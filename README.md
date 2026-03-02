# AI News Bot

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/zzmlb/ai-news-bot?style=social)](https://github.com/zzmlb/ai-news-bot)

**自动化 AI 资讯聚合系统** — 从 25+ 个数据源抓取资讯，通过大模型智能过滤和分类，只推送真正相关的内容。

专注于 **AI 辅助开发 / Vibe Coding / AI 编程工具** 领域。

[English](README_EN.md)

---

## 核心特性

- **多源聚合** — 25 个 RSS 源 + GitHub Trending，覆盖海内外主流 AI 媒体
- **AI 智能过滤** — 千问大模型两阶段语义分析：相关性判断 + 6 类标签分类
- **话题去重** — LLM 识别同一事件的不同报道，自动合并去重
- **钉钉推送** — Markdown 格式化消息，支持多群组订阅
- **Web 仪表盘** — 资讯浏览、分类统计、趋势图表、词云分析
- **AI 助手** — 基于 Chainlit 的交互式助手，可查询数据、分析日志、排查问题
- **一键部署** — 一个 API Key + 一条命令，全自动完成安装和启动

## 工作流程

```
25+ 数据源抓取 → 日期过滤 → URL 去重 → AI 语义过滤(千问) → 话题去重 → 钉钉推送 → SQLite 入库
                                          ↓                                    ↓
                                     6 类标签分类                        Web 仪表盘展示
                                     中文摘要生成                        AI 助手交互查询
```

## 快速开始

### 一键安装（推荐）

```bash
git clone https://github.com/zzmlb/ai-news-bot.git
cd ai-news-bot
bash install.sh            # 交互输入 API Key
# 或直接传参：bash install.sh sk-你的Key
```

> 千问 API Key 从 [阿里云百炼](https://bailian.console.aliyun.com/) 免费获取，格式 `sk-xxx`。

安装完成后首次抓取：

```bash
python3 main.py --test --force
```

访问：**资讯页面** `http://IP:5001` | **AI 助手** `http://IP:8000`

### Docker 部署

```bash
cd docker/
cp config.yaml.example config.yaml    # 编辑填入 API Key
cp agent/.env.example agent/.env      # 编辑填入同一个 Key
docker compose up -d --build
```

访问：**资讯页面** `http://IP:15001` | **AI 助手** `http://IP:18000`

<details>
<summary>配置文件格式参考</summary>

**docker/config.yaml**

```yaml
qwen:
    api_key: "sk-你的Key"
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
ANTHROPIC_AUTH_TOKEN=sk-你的Key
ANTHROPIC_MODEL=qwen3-coder-plus
```

</details>

### 手动部署

不想用一键脚本的话，按以下步骤操作：

```bash
git clone https://github.com/zzmlb/ai-news-bot.git
cd ai-news-bot

# 1. 装 Python 依赖
pip install -r requirements.txt

# 2. 配置（两个文件，填同一个千问 API Key）
cp config.yaml.example config.yaml       # 编辑填入 api_key
cp agent/.env.example agent/.env         # 编辑填入 ANTHROPIC_AUTH_TOKEN

# 3. 装 Claude CLI（AI 助手需要，可选）
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
npm install -g @anthropic-ai/claude-code

# 4. 创建数据目录
mkdir -p data

# 5. 启动资讯页面
nohup python3 web/app.py > data/flask.log 2>&1 &

# 6. 启动 AI 助手（必须在项目根目录执行）
nohup chainlit run agent/app.py --host 0.0.0.0 --port 8000 > data/chainlit.log 2>&1 &

# 7. 首次抓取
python3 main.py --test --force

# 8. 设置定时任务
(crontab -l 2>/dev/null; echo "0 */3 * * * cd $(pwd) && python3 main.py >> data/cron.log 2>&1") | crontab -
```

## 使用

### 抓取资讯

```bash
python3 main.py                 # 正式运行（抓取 + AI过滤 + 推送 + 入库）
python3 main.py --test          # 测试模式（不推送，仅入库）
python3 main.py --test --force  # 忽略去重（首次推荐）
```

### 定时任务

安装脚本会自动配置。手动配置方式：

```bash
crontab -e
# 每 3 小时自动抓取（替换为你的路径）：
0 */3 * * * cd /root/ai-news-bot && python3 main.py >> data/cron.log 2>&1
```

### 服务管理

```bash
ss -tlnp | grep -E '5001|8000'                    # 查看状态
kill $(lsof -ti:5001); nohup python3 web/app.py > data/flask.log 2>&1 &   # 重启 Web
kill $(lsof -ti:8000); nohup chainlit run agent/app.py --host 0.0.0.0 --port 8000 > data/chainlit.log 2>&1 &  # 重启助手
```

## 数据来源

| 分类 | 来源 | 数量 |
|------|------|------|
| 技术社区 | Hacker News、Reddit、Lobsters、Dev.to | 4 |
| 海外媒体 | TechCrunch、The Verge、Ars Technica、VentureBeat、MIT Tech Review | 5 |
| 官方博客 | OpenAI、Google AI、Hugging Face、GitHub Blog、arXiv | 5 |
| 国内媒体 | InfoQ、36氪、机器之心、量子位、少数派 | 5 |
| 版本追踪 | Cursor、Continue、Ollama、LangChain、Open WebUI | 5 |
| 网页采集 | GitHub Trending | 1 |

## AI 过滤分类

| 标签 | 说明 | 示例 |
|------|------|------|
| `tool` | AI 编程工具 | Cursor 新版本、Copilot 功能更新 |
| `model` | AI 模型 | GPT-5 发布、Claude 评测对比 |
| `security` | 安全风险 | AI 生成代码漏洞、模型攻击 |
| `insight` | 行业洞察 | 开发者调研报告、市场趋势 |
| `opensource` | 开源项目 | GitHub 热门 AI 框架 |
| `practice` | 开发实践 | Vibe Coding 方法论、提示词工程 |

## AI 助手 API 配置

支持多种 API 提供商（`agent/.env`）：

| 提供商 | ANTHROPIC_BASE_URL | 模型 | 说明 |
|--------|-------------------|------|------|
| 阿里千问 | `https://dashscope.aliyuncs.com/apps/anthropic` | `qwen3-coder-plus` | 国内推荐 |
| DeepSeek | `https://api.deepseek.com/anthropic` | `deepseek-chat` | 国内可用 |
| Anthropic | `https://api.anthropic.com` | `claude-sonnet-4-20250514` | 需海外网络 |

## 钉钉推送（可选）

编辑 `config.yaml`，开启推送：

```yaml
webhook:
    dingtalk:
        enabled: true
        url: "https://oapi.dingtalk.com/robot/send?access_token=你的token"
        keyword: "AInew"
```

> 钉钉群 → 群设置 → 机器人 → 自定义机器人 → 复制 Webhook 地址。

## 技术栈

| 模块 | 技术 |
|------|------|
| 数据抓取 | feedparser、requests、BeautifulSoup |
| AI 过滤 | 阿里千问 (Qwen) API |
| 数据存储 | SQLite |
| 消息推送 | 钉钉 Webhook |
| Web 页面 | Flask + Tailwind CSS |
| AI 助手 | Chainlit + Claude Code CLI |
| 定时调度 | crontab / Docker supervisord |

## 项目结构

```
├── main.py              # 主入口
├── install.sh           # 一键安装
├── sources/             # 数据抓取（RSS + 网页）
├── filter/              # AI 语义过滤 + 话题去重
├── storage/             # SQLite 存储
├── push/                # 钉钉推送
├── web/                 # Flask Web 仪表盘（:5001）
├── agent/               # Chainlit AI 助手（:8000）
├── docker/              # Docker 部署配置
└── data/                # 运行时数据
```

## License

MIT
