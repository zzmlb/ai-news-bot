"""SQLite 去重存储模块"""

import sqlite3
import os
import re
from collections import Counter
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "news.db")

# 需要迁移添加的新列
_NEW_COLUMNS = [
    ("summary_zh", "TEXT"),
    ("category", "TEXT"),
    ("importance", "TEXT"),
    ("published_time", "TEXT"),
]


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            source TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            pushed_at TEXT
        )
    """)
    # 幂等迁移：检测并添加新列
    existing = {row[1] for row in conn.execute("PRAGMA table_info(articles)")}
    for col_name, col_type in _NEW_COLUMNS:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
    # webhook 订阅表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS webhook_subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            webhook_url TEXT UNIQUE NOT NULL,
            keyword TEXT NOT NULL DEFAULT 'AInew',
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def is_duplicate(url: str) -> bool:
    """检查文章是否已存在"""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT 1 FROM articles WHERE url = ?", (url,)).fetchone()
        return row is not None
    finally:
        conn.close()


def save_article(article: dict):
    """保存文章记录，标记为已推送（含 AI 过滤产出的字段）"""
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO articles
               (url, title, source, pushed_at, summary_zh, category, importance, published_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                article["url"],
                article["title"],
                article.get("source", ""),
                datetime.now().isoformat(),
                article.get("summary_zh", ""),
                article.get("category", ""),
                article.get("importance", ""),
                article.get("published_time", ""),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_articles(page=1, per_page=20, category=None, search=None,
                 date_from=None, date_to=None):
    """分页 + 筛选查询文章列表，返回 (articles_list, total_count)"""
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    try:
        where_clauses = []
        params = []

        if category:
            where_clauses.append("category = ?")
            params.append(category)
        if search:
            where_clauses.append("(title LIKE ? OR summary_zh LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if date_from:
            where_clauses.append("published_time >= ?")
            params.append(date_from)
        if date_to:
            where_clauses.append("published_time <= ?")
            params.append(date_to + "T23:59:59")

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # 总数
        total = conn.execute(
            f"SELECT COUNT(*) FROM articles{where_sql}", params
        ).fetchone()[0]

        # 分页查询
        offset = (page - 1) * per_page
        rows = conn.execute(
            f"""SELECT id, url, title, source, summary_zh, category, importance,
                       published_time, created_at
                FROM articles{where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()

        articles = [dict(row) for row in rows]
        return articles, total
    finally:
        conn.close()


def get_today_stats():
    """今日概览：分类统计 + 重大新闻列表"""
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        # 今日总数
        total = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE published_time LIKE ?",
            (f"{today_str}%",),
        ).fetchone()[0]

        # 分类统计
        cat_rows = conn.execute(
            """SELECT category, COUNT(*) as cnt FROM articles
               WHERE published_time LIKE ? AND category != ''
               GROUP BY category ORDER BY cnt DESC""",
            (f"{today_str}%",),
        ).fetchall()
        categories = {row["category"]: row["cnt"] for row in cat_rows}

        # 重大新闻
        major_rows = conn.execute(
            """SELECT id, url, title, source, summary_zh, category, importance,
                      published_time, created_at
               FROM articles
               WHERE published_time LIKE ? AND importance = 'major'
               ORDER BY created_at DESC""",
            (f"{today_str}%",),
        ).fetchall()
        major = [dict(row) for row in major_rows]

        # 最新 10 条
        latest_rows = conn.execute(
            """SELECT id, url, title, source, summary_zh, category, importance,
                      published_time, created_at
               FROM articles
               WHERE published_time LIKE ?
               ORDER BY created_at DESC LIMIT 10""",
            (f"{today_str}%",),
        ).fetchall()
        latest = [dict(row) for row in latest_rows]

        return {
            "total": total,
            "categories": categories,
            "major": major,
            "latest": latest,
        }
    finally:
        conn.close()


def get_daily_trend(days=30):
    """最近 N 天每日文章数量趋势，返回 {date: count}"""
    conn = _get_conn()
    start = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    try:
        rows = conn.execute(
            """SELECT SUBSTR(published_time, 1, 10) as day, COUNT(*) as cnt
               FROM articles
               WHERE published_time >= ?
               GROUP BY day ORDER BY day""",
            (start,),
        ).fetchall()
        # 补齐没有数据的日期
        result = {}
        for i in range(days):
            d = (datetime.now() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            result[d] = 0
        for day, cnt in rows:
            if day in result:
                result[day] = cnt
        return result
    finally:
        conn.close()


def get_category_stats():
    """全局分类分布统计"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT category, COUNT(*) as cnt FROM articles
               WHERE category != '' GROUP BY category ORDER BY cnt DESC"""
        ).fetchall()
        return {cat: cnt for cat, cnt in rows}
    finally:
        conn.close()


def get_source_stats(limit=15):
    """来源排行 Top N"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT source, COUNT(*) as cnt FROM articles
               WHERE source != '' GROUP BY source ORDER BY cnt DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return {src: cnt for src, cnt in rows}
    finally:
        conn.close()


def get_importance_stats():
    """重要性分布统计"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT importance, COUNT(*) as cnt FROM articles
               WHERE importance != '' GROUP BY importance ORDER BY cnt DESC"""
        ).fetchall()
        return {imp: cnt for imp, cnt in rows}
    finally:
        conn.close()


# jieba 停用词（高频无意义词）
_STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有",
    "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些", "什么",
    "之", "与", "为", "以", "及", "等", "可以", "如何", "通过", "使用",
    "发布", "支持", "功能", "提供", "新", "更", "最", "已", "将", "被", "让",
    "the", "a", "an", "and", "or", "is", "in", "on", "for", "to", "of",
    "with", "by", "at", "from", "as", "its", "it", "this", "that", "are",
    "was", "be", "has", "have", "had", "not", "but", "all", "can", "new",
    "your", "you", "how", "now", "get", "top",
}


def get_word_freq(limit=100):
    """从标题和摘要提取关键词频率（用于词云）"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT title, summary_zh FROM articles"
        ).fetchall()
    finally:
        conn.close()

    import jieba
    counter = Counter()
    for title, summary in rows:
        text = (title or "") + " " + (summary or "")
        words = jieba.cut(text)
        for w in words:
            w = w.strip().lower()
            if len(w) >= 2 and w not in _STOP_WORDS and not re.match(r'^[\d\s\W]+$', w):
                counter[w] += 1
    return counter.most_common(limit)


# ========== Webhook 订阅管理 ==========

def mask_webhook_url(url: str) -> str:
    """对 webhook URL 做脱敏：只显示 access_token 前4位和后4位"""
    if "access_token=" in url:
        prefix, token = url.split("access_token=", 1)
        if len(token) > 8:
            token = token[:4] + "****" + token[-4:]
        return prefix + "access_token=" + token
    # 非标准格式：保留前30字符 + **** + 后6字符
    if len(url) > 40:
        return url[:30] + "****" + url[-6:]
    return url


def add_webhook(name: str, webhook_url: str, keyword: str = "AInew") -> dict:
    """添加一个 webhook 订阅，返回 {'ok': True/False, 'msg': ...}"""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO webhook_subscribers (name, webhook_url, keyword) VALUES (?, ?, ?)",
            (name.strip(), webhook_url.strip(), keyword.strip()),
        )
        conn.commit()
        return {"ok": True, "msg": "添加成功"}
    except sqlite3.IntegrityError:
        return {"ok": False, "msg": "该 Webhook 链接已存在"}
    finally:
        conn.close()


def list_webhooks():
    """列出所有订阅（URL 已脱敏），返回 list[dict]"""
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, name, webhook_url, keyword, enabled, created_at FROM webhook_subscribers ORDER BY created_at DESC"
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["webhook_url_masked"] = mask_webhook_url(d["webhook_url"])
            result.append(d)
        return result
    finally:
        conn.close()


def toggle_webhook(wid: int, enabled: bool):
    """启用/禁用一个订阅"""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE webhook_subscribers SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, wid),
        )
        conn.commit()
    finally:
        conn.close()


def delete_webhook(wid: int):
    """删除一个订阅"""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM webhook_subscribers WHERE id = ?", (wid,))
        conn.commit()
    finally:
        conn.close()


def get_enabled_webhooks():
    """获取所有启用的订阅（含完整 URL，供推送使用）"""
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, name, webhook_url, keyword FROM webhook_subscribers WHERE enabled = 1"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
