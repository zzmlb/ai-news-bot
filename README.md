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
dev/
├── main.py                # 主入口
├── config.yaml            # 配置文件（需从 .example 复制并填入密钥）
├── requirements.txt       # Python 依赖
├── sources/
│   ├── rss_fetcher.py     # RSS/Atom 订阅抓取（24 个源）
│   └── web_scraper.py     # 网页采集（GitHub Trending + Papers With Code）
├── filter/
│   └── ai_filter.py       # 千问 AI 语义过滤 + 话题去重
├── storage/
│   └── db.py              # SQLite 去重存储
├── push/
│   └── dingtalk.py        # 钉钉推送（Markdown 彩色分类标签）
├── agent/
│   ├── app.py             # Chainlit Web 交互助手
│   ├── .env               # Agent API 配置（需从 .example 复制）
│   └── CLAUDE.md          # Agent 系统指令
└── data/
    ├── news.db            # SQLite 数据库（运行时生成）
    └── cron.log           # 定时任务日志
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

```bash
cp config.yaml.example config.yaml
# 编辑 config.yaml，填入千问 API Key 和钉钉 Webhook
```

### 3. 测试运行

```bash
python3 main.py --test          # 测试模式，不推送
python3 main.py --test --force  # 忽略去重
```

### 4. 定时任务

```bash
crontab -e
# 添加: 0 */3 * * * cd /path/to/dev && python3 main.py >> data/cron.log 2>&1
```

### 5. 启动 Agent 助手（可选）

```bash
pip install chainlit
cp agent/.env.example agent/.env
# 编辑 agent/.env，填入 API Key
chainlit run agent/app.py --host 0.0.0.0 --port 8000
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
