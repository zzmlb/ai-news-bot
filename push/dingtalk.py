"""钉钉 Webhook 推送模块"""

import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

# 分类标签：key -> (颜色, 中文名)
CATEGORY_STYLE = {
    "tool":       ("#1E90FF", "工具发布"),
    "model":      ("#9932CC", "AI模型"),
    "security":   ("#FF4500", "安全风险"),
    "insight":    ("#FF8C00", "行业洞察"),
    "opensource":  ("#2E8B57", "开源项目"),
    "practice":   ("#6495ED", "开发实践"),
}


def _format_time(time_str: str) -> str:
    """格式化时间为 MM-DD HH:MM"""
    if not time_str:
        return ""
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return dt.strftime("%m-%d %H:%M")
    except Exception:
        return ""


def _category_tag(category: str) -> str:
    """生成彩色分类标签"""
    color, name = CATEGORY_STYLE.get(category, ("#999999", "其他"))
    return f'<font color="{color}">[{name}]</font>'


def _build_markdown(articles: list[dict], keyword: str) -> dict:
    """组装带编号、彩色标签的 Markdown 钉钉消息"""
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"【{keyword}】AI 开发资讯 {today}"
    lines = [f"## {title}\n"]

    # 重大排前面，一般排后面
    articles_sorted = sorted(articles, key=lambda x: 0 if x.get("importance") == "major" else 1)

    for i, a in enumerate(articles_sorted, 1):
        time_str = _format_time(a.get("published_time", ""))
        cat_tag = _category_tag(a.get("category", "insight"))
        fire = "🔥" if a.get("importance") == "major" else ""

        # 编号 + 标题 + 标签 + 时间
        lines.append(f"**{i}. {fire}[{a['title']}]({a['url']})** {cat_tag} `{time_str}`\n")
        if a.get("summary_zh"):
            lines.append(f"> {a['summary_zh']}\n")

    lines.append(f"---\n共 {len(articles)} 条 | {keyword}")

    return {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": "\n".join(lines),
        },
    }


def push(articles: list[dict], webhook_url: str, keyword: str = "AInew") -> bool:
    """
    推送资讯到钉钉。
    articles: 已过滤的文章列表
    webhook_url: 钉钉机器人 Webhook URL
    keyword: 安全验证关键词
    返回: 是否推送成功
    """
    if not articles:
        logger.info("没有需要推送的资讯")
        return True

    payload = _build_markdown(articles, keyword)

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errcode") == 0:
            logger.info(f"钉钉推送成功: {len(articles)} 条资讯")
            return True
        else:
            logger.error(f"钉钉推送失败: {data}")
            return False
    except Exception as e:
        logger.error(f"钉钉推送异常: {e}")
        return False


def push_to_all_subscribers(articles: list[dict]):
    """向所有已启用的 DB 订阅者推送，返回 (成功数, 失败数)"""
    from storage.db import get_enabled_webhooks
    subscribers = get_enabled_webhooks()
    if not subscribers:
        logger.info("没有已启用的订阅者")
        return 0, 0
    success, fail = 0, 0
    for sub in subscribers:
        ok = push(articles, sub["webhook_url"], sub.get("keyword", "AInew"))
        if ok:
            logger.info(f"推送成功: {sub['name']}")
            success += 1
        else:
            logger.error(f"推送失败: {sub['name']}")
            fail += 1
    return success, fail
