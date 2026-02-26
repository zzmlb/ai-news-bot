"""RSS 源抓取模块"""

import logging
import feedparser
from datetime import datetime

logger = logging.getLogger(__name__)

# RSS 源列表
RSS_FEEDS = [
    # === 技术社区 ===
    {
        "name": "Hacker News AI Coding",
        "url": "https://hnrss.org/newest?q=AI+coding",
    },
    {
        "name": "Reddit r/programming",
        "url": "https://www.reddit.com/r/programming/.rss",
    },
    {
        "name": "Lobsters",
        "url": "https://lobste.rs/rss",
    },
    {
        "name": "Dev.to AI",
        "url": "https://dev.to/feed/tag/ai",
    },

    # === 海外科技媒体 ===
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    },
    {
        "name": "VentureBeat AI",
        "url": "https://feeds.feedburner.com/venturebeat/SZYF",
    },
    {
        "name": "MIT Tech Review",
        "url": "https://www.technologyreview.com/feed",
    },

    # === 官方博客（一手信息）===
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog/rss.xml",
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/innovation-and-ai/technology/ai/rss/",
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
    },
    {
        "name": "GitHub Blog",
        "url": "https://github.blog/feed/",
    },
    {
        "name": "arXiv AI",
        "url": "https://rss.arxiv.org/rss/cs.AI",
    },

    # === 国内媒体 ===
    {
        "name": "InfoQ 中文",
        "url": "https://www.infoq.cn/feed",
    },
    {
        "name": "36氪",
        "url": "https://36kr.com/feed",
    },
    {
        "name": "机器之心",
        "url": "https://www.jiqizhixin.com/rss",
    },
    {
        "name": "量子位",
        "url": "https://www.qbitai.com/feed",
    },
    {
        "name": "少数派",
        "url": "https://sspai.com/feed",
    },

    # === GitHub Releases（AI 开发工具动态）===
    {
        "name": "Cursor Releases",
        "url": "https://github.com/cursor/cursor/releases.atom",
    },
    {
        "name": "Continue Releases",
        "url": "https://github.com/continuedev/continue/releases.atom",
    },
    {
        "name": "Ollama Releases",
        "url": "https://github.com/ollama/ollama/releases.atom",
    },
    {
        "name": "LangChain Releases",
        "url": "https://github.com/langchain-ai/langchain/releases.atom",
    },
    {
        "name": "Open WebUI Releases",
        "url": "https://github.com/open-webui/open-webui/releases.atom",
    },
]


def _parse_published(entry) -> str:
    """解析发布时间"""
    for field in ("published_parsed", "updated_parsed"):
        t = getattr(entry, field, None) or entry.get(field)
        if t:
            try:
                return datetime(*t[:6]).isoformat()
            except Exception:
                pass
    return datetime.now().isoformat()


def fetch_all() -> list[dict]:
    """抓取所有 RSS 源，返回统一格式的文章列表"""
    articles = []
    for feed_info in RSS_FEEDS:
        try:
            logger.info(f"抓取 RSS: {feed_info['name']}")
            feed = feedparser.parse(feed_info["url"])
            if feed.bozo and not feed.entries:
                logger.warning(f"RSS 解析失败: {feed_info['name']} - {feed.bozo_exception}")
                continue

            for entry in feed.entries[:20]:  # 每个源最多取20条
                link = entry.get("link", "")
                if not link:
                    continue
                articles.append({
                    "title": entry.get("title", "").strip(),
                    "url": link,
                    "summary": entry.get("summary", "")[:500],
                    "source": feed_info["name"],
                    "published_time": _parse_published(entry),
                })

            logger.info(f"  {feed_info['name']}: 获取 {len(feed.entries)} 条")
        except Exception as e:
            logger.error(f"抓取 {feed_info['name']} 失败: {e}")
            continue

    return articles
