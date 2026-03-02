# AI News Bot

AI 资讯自动抓取、智能过滤与推送系统，专注于 **AI 辅助开发 / Vibe Coding / AI 编程工具** 领域。

## 工作流程

```
定时抓取(crontab 每3小时) → 日期过滤 → URL去重 → 千问AI语义过滤 → 话题去重 → 钉钉推送 → 入库存储
```

## 数据来源

### RSS 订阅（25 个源）

通过 `feedparser` 解析 RSS/Atom feed，每源最多取 20 条。

#### 技术社区

| 来源 | 地址 | 说明 |
|------|------|------|
| Hacker News | `hnrss.org/newest?q=AI+coding` | AI Coding 关键词过滤 |
| Reddit | `reddit.com/r/programming/.rss` | r/programming 全量 |
| Lobsters | `lobste.rs/rss` | 高质量技术社区 |
| Dev.to | `dev.to/feed/tag/ai` | 开发者社区 AI 标签 |

#### 海外科技媒体

| 来源 | 地址 | 说明 |
|------|------|------|
| TechCrunch | `techcrunch.com/.../artificial-intelligence/feed/` | AI 分类 |
| The Verge | `theverge.com/rss/ai-artificial-intelligence/index.xml` | AI 行业新闻 |
| Ars Technica | `feeds.arstechnica.com/arstechnica/technology-lab` | 深度技术报道 |
| VentureBeat | `feeds.feedburner.com/venturebeat/SZYF` | AI 商业/融资 |
| MIT Tech Review | `technologyreview.com/feed` | 前沿技术解读 |

#### 官方博客（一手信息）

| 来源 | 地址 | 说明 |
|------|------|------|
| OpenAI | `openai.com/blog/rss.xml` | GPT / ChatGPT 动态 |
| Google AI | `blog.google/innovation-and-ai/technology/ai/rss/` | Gemini 等 |
| Hugging Face | `huggingface.co/blog/feed.xml` | 开源模型/工具 |
| GitHub Blog | `github.blog/feed/` | Copilot / Actions |
| arXiv AI | `rss.arxiv.org/rss/cs.AI` | AI 领域最新论文 |

#### 国内媒体

| 来源 | 地址 | 说明 |
|------|------|------|
| InfoQ 中文 | `infoq.cn/feed` | 技术深度内容 |
| 36氪 | `36kr.com/feed` | 科技商业资讯 |
| 机器之心 | `jiqizhixin.com/rss` | 国内最专业 AI 媒体 |
| 量子位 | `qbitai.com/feed` | AI 通俗解读 |
| 少数派 | `sspai.com/feed` | 效率工具/AI 工具评测 |

#### GitHub Releases（AI 工具版本追踪）

| 项目 | Atom 地址 | 说明 |
|------|----------|------|
| Cursor | `github.com/cursor/cursor/releases.atom` | AI 编辑器 |
| Continue | `github.com/continuedev/continue/releases.atom` | IDE AI 插件 |
| Ollama | `github.com/ollama/ollama/releases.atom` | 本地模型运行 |
| LangChain | `github.com/langchain-ai/langchain/releases.atom` | AI 应用框架 |
| Open WebUI | `github.com/open-webui/open-webui/releases.atom` | 模型交互 UI |

### 网页采集（1 个源）

通过 `requests` + `BeautifulSoup` 解析 HTML，无反爬限制。

| 来源 | 地址 | 说明 |
|------|------|------|
| GitHub Trending | `github.com/trending` | 每日热门开源项目，最多 25 个 |

## 技术栈

| 模块 | 技术 |
|------|------|
| 数据抓取 | feedparser / requests + BeautifulSoup |
| AI 过滤 | 阿里千问 (Qwen) 大模型 API |
| 数据存储 | SQLite |
| 消息推送 | 钉钉机器人 Webhook |
| 交互助手 | Chainlit + Claude Code SDK |
| 定时调度 | Linux crontab |

## 项目结构

```
├── main.py                  # 主入口：抓取→过滤→推送→入库
├── config.yaml              # 配置文件（从 .example 复制，填入密钥）
├── requirements.txt         # Python 依赖
├── sources/
│   ├── rss_fetcher.py       # RSS/Atom 订阅抓取（25 个源）
│   └── web_scraper.py       # 网页采集（GitHub Trending）
├── filter/
│   └── ai_filter.py         # 千问 AI 语义过滤 + 话题去重
├── storage/
│   └── db.py                # SQLite 存储 + Webhook 订阅管理
├── push/
│   └── dingtalk.py          # 钉钉推送（支持多订阅者）
├── web/
│   ├── app.py               # Flask Web 应用（端口 5001）
│   └── templates/           # 页面模板（首页/统计/资讯/推送管理）
├── agent/
│   ├── app.py               # Chainlit AI 助手（端口 8000）
│   ├── .env                 # Agent API 配置（从 .example 复制）
│   └── CLAUDE.md            # Agent 系统指令
├── docker/                  # Docker 一键部署配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── supervisord.conf     # 进程守护（Flask + Chainlit + cron）
│   ├── crontab              # 容器内定时任务
│   ├── .env                 # 端口映射配置
│   ├── config.yaml.example  # 主配置模板
│   └── agent/.env.example   # Agent 配置模板
└── data/
    ├── news.db              # SQLite 数据库（运行时生成）
    └── cron.log             # 定时任务日志
```

## 前置要求

- Python 3.10+
- pip（Debian/Ubuntu: `apt install python3-pip`）
- Node.js 18+（仅 AI 助手需要，用于安装 Claude Code CLI）
- Docker 和 Docker Compose（仅 Docker 部署方式需要）

## 密钥获取

| 密钥 | 用途 | 获取方式 |
|------|------|---------|
| 千问 API Key | 资讯 AI 过滤 + AI 助手 | 注册 [阿里云百炼](https://bailian.console.aliyun.com/)，创建 API Key（格式 `sk-xxx`） |
| 钉钉 Webhook | 消息推送 | 钉钉群 → 群设置 → 机器人 → 自定义机器人 → 复制 Webhook 地址，安全设置选"自定义关键词" |

> 千问 API Key 同时用于主流程的 AI 语义过滤（`config.yaml`）和 AI 助手（`agent/.env`）。

## 快速开始

### 方式一：Docker 部署（推荐）

只需填写配置文件，一条命令启动所有服务（Web 页面 + AI 助手 + 定时抓取）。

```bash
cd docker/

# 1. 填写配置
cp config.yaml.example config.yaml      # 填入千问 API Key 和钉钉 Webhook
cp agent/.env.example agent/.env         # 填入千问 API Key

# 2. 构建并启动
docker compose up -d --build

# 3. 访问
# 资讯页面: http://IP:15001（端口可在 docker/.env 中修改）
# AI 助手:  http://IP:18000
```

容器内通过 supervisord 管理三个进程：

| 进程 | 说明 |
|------|------|
| flask | Web 资讯页面（首页、统计、推送管理） |
| chainlit | AI 交互助手 |
| cron | 每 3 小时自动抓取推送 |

常用命令：

```bash
docker compose logs -f            # 查看日志
docker compose restart            # 重启服务
docker compose down               # 停止容器
docker compose up -d --build      # 重新构建
```

### 方式二：手动部署

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 配置

```bash
cp config.yaml.example config.yaml
# 编辑 config.yaml，填入千问 API Key 和钉钉 Webhook URL

cp agent/.env.example agent/.env
# 编辑 agent/.env，填入千问 API Key（AI 助手使用）
```

#### 3. 测试运行

```bash
python3 main.py --test          # 测试模式，不推送
python3 main.py --test --force  # 忽略去重
```

#### 4. 启动 Web 页面

```bash
# 前台运行
python3 web/app.py

# 后台运行（推荐）
nohup python3 web/app.py > data/flask.log 2>&1 &

# 访问 http://IP:5001
```

#### 5. 启动 AI 助手（可选）

AI 助手通过 Claude Code CLI 接入大模型，支持多种 API 提供商。

**安装 Claude Code CLI：**

```bash
# 安装 Node.js 18+（如未安装）
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# 安装 Claude Code CLI
npm install -g @anthropic-ai/claude-code
```

**配置 AI 助手的模型 API：**

```bash
cp agent/.env.example agent/.env
# 编辑 agent/.env，选择以下任一方式：
```

| API 提供商 | ANTHROPIC_BASE_URL | 模型示例 | 说明 |
|-----------|-------------------|---------|------|
| 阿里千问 | `https://dashscope.aliyuncs.com/apps/anthropic` | `qwen3-coder-plus` | 国内推荐，无需翻墙 |
| DeepSeek | `https://api.deepseek.com/anthropic` | `deepseek-chat` | 国内可用 |
| Anthropic | `https://api.anthropic.com` | `claude-sonnet-4-20250514` | 需海外网络 |

> 原理：Claude Code CLI 支持 `ANTHROPIC_BASE_URL` 自定义端点，只要目标 API 兼容 Anthropic Messages 格式即可。详见 `agent/.env.example` 中的完整配置说明。

**启动：**

```bash
nohup chainlit run agent/app.py --host 0.0.0.0 --port 8000 > data/chainlit.log 2>&1 &

# 访问 http://IP:8000
```

#### 6. 定时任务

```bash
crontab -e
# 添加以下行（注意替换为项目的绝对路径）：
# 0 */3 * * * cd /root/ai-news-bot && python3 main.py >> data/cron.log 2>&1
```

验证 cron 是否生效：

```bash
crontab -l                       # 确认已添加
tail -f data/cron.log            # 等待下次执行后查看日志
```

## AI 过滤分类

系统将资讯分为 6 个类别：

| 分类 | 标签 | 说明 |
|------|------|------|
| 工具发布 | `tool` | AI 编程工具新版本/新功能 |
| AI 模型 | `model` | 模型发布、评测、对比 |
| 安全风险 | `security` | 安全事件、AI 滥用风险 |
| 行业洞察 | `insight` | 调研报告、趋势分析 |
| 开源项目 | `opensource` | GitHub 热门项目/框架 |
| 开发实践 | `practice` | AI 辅助开发方法论 |

## License

MIT
