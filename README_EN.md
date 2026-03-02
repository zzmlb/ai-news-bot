# AI News Bot

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/zzmlb/ai-news-bot?style=social)](https://github.com/zzmlb/ai-news-bot)

**Automated AI news aggregation system** — Fetches news from 25+ sources, uses LLM-powered intelligent filtering and classification, and delivers only the most relevant content.

Focused on **AI-assisted development / Vibe Coding / AI programming tools**.

[中文文档](README.md)

---

## Key Features

- **Multi-source Aggregation** — 25 RSS feeds + GitHub Trending, covering major AI media worldwide
- **AI-powered Filtering** — Qwen LLM two-stage semantic analysis: relevance scoring + 6-category classification
- **Topic Deduplication** — LLM identifies duplicate reports of the same event and merges them
- **DingTalk Push** — Markdown-formatted messages with multi-group subscription support
- **Web Dashboard** — News browsing, category stats, trend charts, and word cloud analysis
- **AI Assistant** — Chainlit-based interactive assistant for querying data and troubleshooting
- **One-click Deploy** — One API key + one command, fully automated setup

## Pipeline

```
25+ sources → Date filter → URL dedup → AI semantic filter (Qwen) → Topic dedup → DingTalk push → SQLite
                                              ↓                                         ↓
                                        6-category tags                          Web dashboard
                                        Chinese summaries                        AI assistant
```

## Quick Start

### One-click Install (Recommended)

```bash
git clone https://github.com/zzmlb/ai-news-bot.git
cd ai-news-bot
bash install.sh            # Interactive API key input
# Or pass directly: bash install.sh sk-yourKey
```

> Get a free Qwen API Key from [Alibaba Cloud Bailian](https://bailian.console.aliyun.com/), format: `sk-xxx`.

After installation, run your first fetch:

```bash
python3 main.py --test --force
```

Access: **News page** `http://IP:5001` | **AI Assistant** `http://IP:8000`

### Docker Deployment

```bash
cd docker/
cp config.yaml.example config.yaml    # Edit and fill in API Key
cp agent/.env.example agent/.env      # Edit and fill in the same Key
docker compose up -d --build
```

Access: **News page** `http://IP:15001` | **AI Assistant** `http://IP:18000`

<details>
<summary>Configuration file reference</summary>

**docker/config.yaml**

```yaml
qwen:
    api_key: "sk-yourKey"
    model: "qwen-turbo"
webhook:
    dingtalk:
        enabled: false
        url: ""
        keyword: "AInew"
```

**docker/agent/.env**

```bash
ANTHROPIC_BASE_URL=https://dashscope.aliyuncs.com/apps/anthropic
ANTHROPIC_AUTH_TOKEN=sk-yourKey
ANTHROPIC_MODEL=qwen3-coder-plus
```

</details>

### Manual Deployment

If you prefer not to use the install script:

```bash
git clone https://github.com/zzmlb/ai-news-bot.git
cd ai-news-bot

# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Configure (two files, same Qwen API Key)
cp config.yaml.example config.yaml       # Edit: fill in api_key
cp agent/.env.example agent/.env         # Edit: fill in ANTHROPIC_AUTH_TOKEN

# 3. Install Claude CLI (required for AI assistant, optional)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
npm install -g @anthropic-ai/claude-code

# 4. Create data directory
mkdir -p data

# 5. Start news web page
nohup python3 web/app.py > data/flask.log 2>&1 &

# 6. Start AI assistant (must run from project root)
nohup chainlit run agent/app.py --host 0.0.0.0 --port 8000 > data/chainlit.log 2>&1 &

# 7. First fetch
python3 main.py --test --force

# 8. Setup cron job
(crontab -l 2>/dev/null; echo "0 */3 * * * cd $(pwd) && python3 main.py >> data/cron.log 2>&1") | crontab -
```

## Usage

### Fetch News

```bash
python3 main.py                 # Production (fetch + filter + push + save)
python3 main.py --test          # Test mode (no push, save only)
python3 main.py --test --force  # Skip dedup (recommended for first run)
```

### Cron Job

The install script configures this automatically. Manual setup:

```bash
crontab -e
# Run every 3 hours (replace with your path):
0 */3 * * * cd /root/ai-news-bot && python3 main.py >> data/cron.log 2>&1
```

### Service Management

```bash
ss -tlnp | grep -E '5001|8000'                    # Check status
kill $(lsof -ti:5001); nohup python3 web/app.py > data/flask.log 2>&1 &   # Restart web
kill $(lsof -ti:8000); nohup chainlit run agent/app.py --host 0.0.0.0 --port 8000 > data/chainlit.log 2>&1 &  # Restart assistant
```

## Data Sources

| Category | Sources | Count |
|----------|---------|-------|
| Tech Communities | Hacker News, Reddit, Lobsters, Dev.to | 4 |
| International Media | TechCrunch, The Verge, Ars Technica, VentureBeat, MIT Tech Review | 5 |
| Official Blogs | OpenAI, Google AI, Hugging Face, GitHub Blog, arXiv | 5 |
| Chinese Media | InfoQ, 36Kr, Synced (Jiqizhixin), QbitAI, SSPAI | 5 |
| Release Tracking | Cursor, Continue, Ollama, LangChain, Open WebUI | 5 |
| Web Scraping | GitHub Trending | 1 |

## AI Classification

| Tag | Description | Examples |
|-----|-------------|----------|
| `tool` | AI coding tools | Cursor release, Copilot updates |
| `model` | AI models | GPT-5 launch, Claude benchmarks |
| `security` | Security risks | AI-generated code vulnerabilities |
| `insight` | Industry insights | Developer surveys, market trends |
| `opensource` | Open source | Trending AI frameworks on GitHub |
| `practice` | Dev practices | Vibe Coding methodology, prompt engineering |

## AI Assistant API Configuration

Multiple API providers supported (`agent/.env`):

| Provider | ANTHROPIC_BASE_URL | Model | Notes |
|----------|-------------------|-------|-------|
| Alibaba Qwen | `https://dashscope.aliyuncs.com/apps/anthropic` | `qwen3-coder-plus` | Recommended for China |
| DeepSeek | `https://api.deepseek.com/anthropic` | `deepseek-chat` | Available in China |
| Anthropic | `https://api.anthropic.com` | `claude-sonnet-4-20250514` | Requires overseas network |

## Tech Stack

| Module | Technology |
|--------|-----------|
| Data Fetching | feedparser, requests, BeautifulSoup |
| AI Filtering | Alibaba Qwen (Qwen) API |
| Storage | SQLite |
| Push Notifications | DingTalk Webhook |
| Web UI | Flask + Tailwind CSS |
| AI Assistant | Chainlit + Claude Code CLI |
| Scheduling | crontab / Docker supervisord |

## License

MIT
