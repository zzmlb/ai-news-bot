FROM python:3.11-slim

# 系统依赖：supervisor（进程守护）、cron（定时任务）、Node.js（Claude CLI）
RUN apt-get update && apt-get install -y --no-install-recommends \
        supervisor cron curl ca-certificates gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
       | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
       > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app

# Python 依赖（先装依赖，利用 Docker 缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码（build context 为仓库根目录）
COPY . .

# 删除敏感文件和数据（运行时通过 volume 挂载）
RUN rm -f config.yaml agent/.env \
    && rm -rf data/ __pycache__ */__pycache__ \
    && mkdir -p data

# supervisor 和 cron 配置
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/crontab /etc/cron.d/ai-news-bot
RUN chmod 0644 /etc/cron.d/ai-news-bot && crontab /etc/cron.d/ai-news-bot

EXPOSE 5001 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
