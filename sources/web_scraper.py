"""网页采集模块 — GitHub Trending"""

import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}


def fetch_trending() -> list[dict]:
    """抓取 GitHub Trending"""
    return _fetch_github_trending()


def _fetch_github_trending() -> list[dict]:
    """抓取 GitHub Trending 项目"""
    articles = []
    try:
        logger.info("抓取 GitHub Trending")
        resp = requests.get(
            "https://github.com/trending",
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        repo_list = soup.select("article.Box-row")

        for repo in repo_list[:25]:
            h2 = repo.select_one("h2 a")
            if not h2:
                continue
            repo_path = h2.get("href", "").strip("/")
            if not repo_path:
                continue
            repo_name = repo_path.replace("/", " / ")
            repo_url = f"https://github.com/{repo_path}"

            desc_tag = repo.select_one("p")
            description = desc_tag.get_text(strip=True) if desc_tag else ""

            stars_tag = repo.select_one("span.d-inline-block.float-sm-right")
            stars = stars_tag.get_text(strip=True) if stars_tag else ""

            lang_tag = repo.select_one("span[itemprop='programmingLanguage']")
            language = lang_tag.get_text(strip=True) if lang_tag else ""

            summary_parts = []
            if description:
                summary_parts.append(description)
            if language:
                summary_parts.append(f"语言: {language}")
            if stars:
                summary_parts.append(f"今日星标: {stars}")

            articles.append({
                "title": f"[GitHub Trending] {repo_name}",
                "url": repo_url,
                "summary": " | ".join(summary_parts),
                "source": "GitHub Trending",
                "published_time": datetime.now().isoformat(),
            })

        logger.info(f"  GitHub Trending: 获取 {len(articles)} 个项目")
    except Exception as e:
        logger.error(f"抓取 GitHub Trending 失败: {e}")

    return articles
