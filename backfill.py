"""回填历史文章的 published_time / category / summary_zh"""

import json
import logging
import sqlite3
import time
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import yaml
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backfill")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "news.db")
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

# 与 ai_filter.py 保持一致的分类 prompt（简化版，只做分类+摘要）
CLASSIFY_PROMPT = """你是一个 AI 开发领域的资深编辑。请对以下文章进行分类和摘要。

文章列表（JSON 格式）：
{articles_json}

请对每篇文章返回 JSON 数组，每个元素包含：
- "index": 文章序号（从0开始）
- "importance": "major" 或 "normal"（重大=行业重要事件/突破性进展/知名产品重大更新；一般=普通工具发布/日常讨论）
- "category": 分类标签，从以下6个中选1个：
  - "tool" = 工具发布/更新
  - "model" = AI 模型
  - "security" = 安全风险
  - "insight" = 行业洞察
  - "opensource" = 开源项目
  - "practice" = 开发实践
- "summary_zh": 中文摘要（40-100字，直接说核心事实，禁止用"文章介绍了"开头）

只返回 JSON 数组，不要其他内容。"""


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def call_qwen(api_key, model, prompt):
    resp = requests.post(
        DASHSCOPE_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
        timeout=120,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        lines = text.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def main():
    config = load_config()
    api_key = config["qwen"]["api_key"]
    model = config["qwen"].get("model", "qwen-turbo")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # === 第1步：用 created_at 回填 published_time ===
    logger.info("=== 第1步：回填 published_time ===")
    no_time = conn.execute(
        "SELECT id, created_at FROM articles WHERE published_time IS NULL OR published_time = ''"
    ).fetchall()
    if no_time:
        for row in no_time:
            # created_at 格式: "2026-02-21 13:23:05" -> "2026-02-21T13:23:05"
            pub_time = row["created_at"].replace(" ", "T") if row["created_at"] else ""
            conn.execute("UPDATE articles SET published_time = ? WHERE id = ?", (pub_time, row["id"]))
        conn.commit()
        logger.info(f"已回填 {len(no_time)} 条 published_time")
    else:
        logger.info("published_time 无需回填")

    # === 第2步：调千问 API 补分类和摘要 ===
    logger.info("=== 第2步：AI 补充 category + summary_zh ===")
    missing = conn.execute(
        "SELECT id, title, source FROM articles WHERE category IS NULL OR category = ''"
    ).fetchall()

    if not missing:
        logger.info("所有文章已有分类，无需处理")
        conn.close()
        return

    logger.info(f"需要分类的文章: {len(missing)} 条")

    batch_size = 15
    updated = 0
    for i in range(0, len(missing), batch_size):
        batch = [dict(row) for row in missing[i:i + batch_size]]
        batch_input = [
            {"index": j, "title": a["title"], "source": a.get("source", "")}
            for j, a in enumerate(batch)
        ]
        prompt = CLASSIFY_PROMPT.format(articles_json=json.dumps(batch_input, ensure_ascii=False))

        try:
            batch_num = i // batch_size + 1
            total_batches = (len(missing) + batch_size - 1) // batch_size
            logger.info(f"处理第 {batch_num}/{total_batches} 批（{len(batch)} 篇）...")

            results = call_qwen(api_key, model, prompt)

            for item in results:
                idx = item.get("index", -1)
                if 0 <= idx < len(batch):
                    conn.execute(
                        "UPDATE articles SET category = ?, importance = ?, summary_zh = ? WHERE id = ?",
                        (
                            item.get("category", "insight"),
                            item.get("importance", "normal"),
                            item.get("summary_zh", ""),
                            batch[idx]["id"],
                        ),
                    )
                    updated += 1
            conn.commit()
            logger.info(f"  第 {batch_num} 批完成")

        except Exception as e:
            logger.error(f"  第 {batch_num} 批失败: {e}")

        if i + batch_size < len(missing):
            time.sleep(1)

    logger.info(f"=== 完成：更新 {updated} 条文章 ===")
    conn.close()


if __name__ == "__main__":
    main()
