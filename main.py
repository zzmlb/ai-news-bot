"""AI 资讯推送系统 - 主入口"""

import argparse
import logging
import os
import sys
from datetime import datetime

import yaml

# 将 dev 目录加入 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

from sources.rss_fetcher import fetch_all as fetch_rss
from sources.web_scraper import fetch_trending
from filter.ai_filter import filter_articles
from push.dingtalk import push, push_to_all_subscribers
from storage.db import is_duplicate, save_article

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="AI 资讯推送系统")
    parser.add_argument("--test", action="store_true", help="测试模式，不实际推送")
    parser.add_argument("--force", action="store_true", help="忽略去重，强制处理所有文章")
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("AI 资讯推送系统启动")
    if args.test:
        logger.info(">>> 测试模式：不会实际推送")
    if args.force:
        logger.info(">>> 强制模式：忽略去重")

    # 加载配置
    config = load_config()
    api_key = config["qwen"]["api_key"]
    model = config["qwen"].get("model", "qwen-turbo")
    dingtalk_cfg = config["webhook"]["dingtalk"]

    # === 第1步：抓取资讯 ===
    logger.info("--- 第1步：抓取资讯 ---")
    articles = []
    articles.extend(fetch_rss())
    articles.extend(fetch_trending())
    logger.info(f"共抓取 {len(articles)} 条资讯")

    if not articles:
        logger.info("未抓取到任何资讯，退出")
        return

    # === 第1.5步：只保留今天的新闻 ===
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_articles = []
    for a in articles:
        pt = a.get("published_time", "")
        if pt.startswith(today_str):
            today_articles.append(a)
    logger.info(f"日期过滤: {len(articles)} 条 → {len(today_articles)} 条今日资讯（{today_str}）")
    articles = today_articles

    if not articles:
        logger.info("今天没有新资讯，退出")
        return

    # === 第2步：去重 ===
    logger.info("--- 第2步：去重过滤 ---")
    if args.force:
        new_articles = articles
    else:
        new_articles = [a for a in articles if not is_duplicate(a["url"])]
    logger.info(f"去重后剩余 {len(new_articles)} 条（过滤 {len(articles) - len(new_articles)} 条重复）")

    if not new_articles:
        logger.info("没有新资讯，退出")
        return

    # === 第3步：AI 语义过滤 ===
    logger.info("--- 第3步：AI 语义过滤 ---")
    filtered = filter_articles(new_articles, api_key, model)

    if not filtered:
        logger.info("AI 过滤后没有相关资讯，退出")
        return

    major_count = sum(1 for a in filtered if a.get("importance") == "major")
    logger.info(f"AI 过滤结果: {len(filtered)} 条相关（{major_count} 条重大）")

    # 打印过滤结果摘要
    for a in filtered:
        tag = "🔥" if a.get("importance") == "major" else "📰"
        logger.info(f"  {tag} [{a['source']}] {a['title']}")
        if a.get("summary_zh"):
            logger.info(f"     摘要: {a['summary_zh']}")

    # === 第4步：推送 + 入库 ===
    if args.test:
        logger.info("--- 测试模式，跳过推送，仅入库 ---")
    else:
        logger.info("--- 第4步：钉钉推送 ---")
        if dingtalk_cfg.get("enabled"):
            success = push(filtered, dingtalk_cfg["url"], dingtalk_cfg.get("keyword", "AInew"))
            if success:
                logger.info("推送完成")
            else:
                logger.error("推送失败")
        else:
            logger.info("钉钉推送未启用")

        # 向所有 DB 订阅者推送
        s, f = push_to_all_subscribers(filtered)
        if s or f:
            logger.info(f"订阅者推送: {s} 成功, {f} 失败")

    # 入库（test 模式也入库，方便验证页面数据）
    for a in filtered:
        save_article(a)
    logger.info(f"已保存 {len(filtered)} 条记录到数据库")

    logger.info("AI 资讯推送系统运行结束")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
