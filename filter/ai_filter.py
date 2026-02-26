"""千问 AI 语义过滤模块 - 筛选 AI 辅助开发/Vibe Coding 相关资讯"""

import json
import logging
import time
import requests

logger = logging.getLogger(__name__)

DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

FILTER_PROMPT = """你是一个 AI 开发领域的资深编辑。请筛选以下文章，找出与"AI 辅助开发 / Vibe Coding / AI 编程工具"相关的内容。

相关主题包括但不限于：
- AI 编程助手（Copilot、Cursor、Claude Code 等）
- 大语言模型在软件开发中的应用
- AI 代码生成、代码审查、自动化测试
- Vibe Coding（用自然语言驱动编程）
- AI Agent 开发框架
- 开发者工具中的 AI 集成
- AI 开源项目（与开发相关的）

文章列表（JSON 格式）：
{articles_json}

请对每篇文章返回 JSON 数组，每个元素包含：
- "index": 文章序号（从0开始）
- "relevant": true/false（是否相关）
- "importance": "major" 或 "normal"（重大=行业重要事件/突破性进展/知名产品重大更新；一般=普通工具发布/日常讨论）
- "category": 分类标签，从以下6个中选1个：
  - "tool" = 工具发布（编程工具新版本/新功能，如 Cursor、Claude Code、Windsurf）
  - "model" = AI 模型（模型发布、性能评测、模型对比）
  - "security" = 安全风险（安全事件、故障、AI 滥用风险）
  - "insight" = 行业洞察（调研报告、趋势分析、观点讨论）
  - "opensource" = 开源项目（GitHub 热门项目、开源框架）
  - "practice" = 开发实践（AI 辅助开发方法论、工作流、经验分享）
- "summary_zh": 中文摘要（要求见下方）

【摘要写作要求 - 非常重要】
1. 直接说核心事实，禁止用"文章介绍了"、"文章讨论了"、"文章提到"等套话开头
2. 要回答：发生了什么？为什么值得关注？
3. 英文内容翻译为中文
4. 长度 40-100 字
5. 相同事件的不同报道，摘要要体现差异角度

好的摘要示例：
- "Cursor 发布 1.0 正式版，新增 Agent 模式可自主完成多文件重构，免费用户每天可用 50 次"
- "亚马逊内部 AI 编码工具引发 AWS 长达 13 小时宕机，暴露自动化代码部署的安全隐患"
- "调查显示 AI 编程助手实际生产力提升仅约 10%，远低于厂商宣传预期"

差的摘要示例（禁止）：
- "文章讨论了AI编码代理的事件驱动任务协调机制"
- "文章介绍了一个AI编码平台"

只返回 JSON 数组，不要其他内容。"""


def _call_qwen(api_key: str, model: str, prompt: str) -> str:
    """调用千问 API"""
    resp = requests.post(
        DASHSCOPE_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _parse_response(text: str) -> list[dict]:
    """从 AI 响应中解析 JSON 数组"""
    text = text.strip()
    # 处理 markdown 代码块包裹的情况
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # 去掉 ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def filter_articles(articles: list[dict], api_key: str, model: str = "qwen-turbo") -> list[dict]:
    """
    对文章列表进行 AI 语义过滤。
    返回相关文章列表，每篇附带 summary_zh 和 importance 字段。
    """
    if not articles:
        return []

    # 分批处理，每批最多15篇，避免单次请求过大
    batch_size = 15
    filtered = []

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        batch_input = [
            {"index": j, "title": a["title"], "summary": a.get("summary", ""), "source": a.get("source", "")}
            for j, a in enumerate(batch)
        ]

        prompt = FILTER_PROMPT.format(articles_json=json.dumps(batch_input, ensure_ascii=False))

        try:
            logger.info(f"AI 过滤第 {i // batch_size + 1} 批（{len(batch)} 篇）")
            result_text = _call_qwen(api_key, model, prompt)
            results = _parse_response(result_text)

            for item in results:
                idx = item.get("index", -1)
                if 0 <= idx < len(batch) and item.get("relevant"):
                    article = batch[idx].copy()
                    article["summary_zh"] = item.get("summary_zh", "")
                    article["importance"] = item.get("importance", "normal")
                    article["category"] = item.get("category", "insight")
                    filtered.append(article)

        except Exception as e:
            logger.error(f"AI 过滤第 {i // batch_size + 1} 批失败: {e}")
            # 过滤失败时跳过这批，不影响其他批次

        # 批次间间隔，避免 API 限流
        if i + batch_size < len(articles):
            time.sleep(1)

    logger.info(f"AI 过滤完成: {len(articles)} 篇 → {len(filtered)} 篇相关")

    # 第二阶段：合并同一事件的重复报道
    if len(filtered) > 1:
        filtered = _dedup_by_topic(filtered, api_key, model)

    return filtered


DEDUP_PROMPT = """你是一个资讯编辑。以下是一批已筛选的 AI 开发相关文章，其中可能存在多篇报道同一事件的情况。

请合并重复报道：同一事件只保留最有信息量的 1 篇，其余标记为丢弃。

文章列表（JSON 格式）：
{articles_json}

返回 JSON 数组，每个元素包含：
- "index": 文章序号（从0开始）
- "keep": true/false（true=保留，false=与其他文章重复应丢弃）
- "reason": 丢弃原因（仅 keep=false 时填写，说明与哪篇重复，如"与第0篇报道同一事件"）

只返回 JSON 数组，不要其他内容。"""


def _dedup_by_topic(articles: list[dict], api_key: str, model: str) -> list[dict]:
    """用 AI 合并同一事件的重复报道"""
    dedup_input = [
        {"index": i, "title": a["title"], "summary_zh": a.get("summary_zh", ""), "source": a.get("source", "")}
        for i, a in enumerate(articles)
    ]

    prompt = DEDUP_PROMPT.format(articles_json=json.dumps(dedup_input, ensure_ascii=False))

    try:
        logger.info(f"话题去重: 分析 {len(articles)} 篇文章")
        result_text = _call_qwen(api_key, model, prompt)
        results = _parse_response(result_text)

        kept = []
        removed = 0
        for item in results:
            idx = item.get("index", -1)
            if 0 <= idx < len(articles) and item.get("keep"):
                kept.append(articles[idx])
            elif not item.get("keep"):
                removed += 1

        logger.info(f"话题去重完成: {len(articles)} 篇 → {len(kept)} 篇（合并 {removed} 篇重复报道）")
        return kept
    except Exception as e:
        logger.error(f"话题去重失败，保留原始结果: {e}")
        return articles
