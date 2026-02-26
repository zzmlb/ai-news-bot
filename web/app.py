"""AI 资讯 Web 页面 — Flask 应用"""

import os
import sys
import math

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# 将 dev 目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from storage.db import (get_articles, get_today_stats, get_daily_trend,
                        get_category_stats, get_source_stats,
                        get_importance_stats, get_word_freq,
                        add_webhook, list_webhooks, toggle_webhook,
                        delete_webhook)

app = Flask(__name__)
CORS(app)

# 分类标签映射
CATEGORY_LABELS = {
    "tool": "工具",
    "model": "模型",
    "security": "安全",
    "insight": "洞察",
    "opensource": "开源",
    "practice": "实践",
}


@app.route("/")
def index():
    """首页：今日概览"""
    stats = get_today_stats()
    return render_template("index.html", stats=stats, category_labels=CATEGORY_LABELS)


@app.route("/articles")
def articles():
    """列表页：分页 + 筛选"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    category = request.args.get("category", "").strip() or None
    search = request.args.get("search", "").strip() or None
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None

    items, total = get_articles(page, per_page, category, search, date_from, date_to)
    total_pages = math.ceil(total / per_page) if total else 1

    return render_template(
        "articles.html",
        articles=items,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        category=category or "",
        search=search or "",
        date_from=date_from or "",
        date_to=date_to or "",
        category_labels=CATEGORY_LABELS,
    )


@app.route("/stats")
def stats():
    """统计仪表盘"""
    days = request.args.get("days", 30, type=int)
    trend = get_daily_trend(days)
    categories = get_category_stats()
    sources = get_source_stats(15)
    importance = get_importance_stats()
    word_freq = get_word_freq(120)
    return render_template(
        "stats.html",
        trend=trend,
        categories=categories,
        sources=sources,
        importance=importance,
        word_freq=word_freq,
        days=days,
        category_labels=CATEGORY_LABELS,
    )


@app.route("/webhooks")
def webhooks():
    """推送管理页面"""
    subscribers = list_webhooks()
    msg = request.args.get("msg", "")
    msg_type = request.args.get("msg_type", "")
    return render_template("webhooks.html", subscribers=subscribers, msg=msg, msg_type=msg_type)


@app.route("/webhooks/add", methods=["POST"])
def webhooks_add():
    """添加订阅"""
    name = request.form.get("name", "").strip()
    url = request.form.get("webhook_url", "").strip()
    keyword = request.form.get("keyword", "AInew").strip() or "AInew"
    if not name or not url:
        return _webhook_redirect("名称和 Webhook 链接不能为空", "error")
    if "dingtalk" not in url and "oapi" not in url:
        return _webhook_redirect("请输入有效的钉钉 Webhook 链接", "error")
    result = add_webhook(name, url, keyword)
    return _webhook_redirect(result["msg"], "success" if result["ok"] else "error")


@app.route("/webhooks/toggle/<int:wid>", methods=["POST"])
def webhooks_toggle(wid):
    """启用/禁用"""
    enabled = request.form.get("enabled") == "1"
    toggle_webhook(wid, enabled)
    return _webhook_redirect("已更新", "success")


@app.route("/webhooks/delete/<int:wid>", methods=["POST"])
def webhooks_delete(wid):
    """删除"""
    delete_webhook(wid)
    return _webhook_redirect("已删除", "success")


def _webhook_redirect(msg, msg_type):
    from flask import redirect, url_for
    return redirect(url_for("webhooks", msg=msg, msg_type=msg_type))


@app.route("/api/articles")
def api_articles():
    """JSON API：供前端 AJAX 调用"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    category = request.args.get("category", "").strip() or None
    search = request.args.get("search", "").strip() or None

    items, total = get_articles(page, per_page, category, search)
    return jsonify({"articles": items, "total": total, "page": page})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
