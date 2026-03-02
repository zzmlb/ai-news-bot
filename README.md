# AI News Bot

AI 资讯自动抓取、智能过滤与推送系统，专注于 **AI 辅助开发 / Vibe Coding / AI 编程工具** 领域。

## 工作流程

```
定时抓取(crontab 每3小时) → 日期过滤 → URL去重 → 千问AI语义过滤 → 话题去重 → 钉钉推送 → 入库存储
```

## 快速开始

### 一键安装（推荐）

只需一个千问 API Key，脚本自动完成所有配置和启动。

> 千问 API Key 从 [阿里云百炼](https://bailian.console.aliyun.com/) 获取，格式 `sk-xxx`。

```bash
git clone https://github.com/zzmlb/ai-news-bot.git
cd ai-news-bot
bash install.sh            # 交互输入 API Key
# 或直接传参：bash install.sh sk-你的Key
```

脚本自动完成：装依赖 → 装 Claude CLI → 生成配置 → 启动服务 → 设定时任务 → 开防火墙。

完成后：

```bash
# 手动抓取一次资讯（首次必须执行）
python3 main.py --test --force

# 访问
# 资讯页面: http://IP:5001
# AI 助手:  http://IP:8000
```

### Docker 部署

```bash
cd docker/
cp config.yaml.example config.yaml
cp agent/.env.example agent/.env
```

编辑 `docker/config.yaml`，填入千问 API Key：

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

编辑 `docker/agent/.env`，填入同一个 Key：

```bash
ANTHROPIC_BASE_URL=https://dashscope.aliyuncs.com/apps/anthropic
ANTHROPIC_AUTH_TOKEN=sk-你的Key
ANTHROPIC_MODEL=qwen3-coder-plus
```

启动：

```bash
docker compose up -d --build

# 资讯页面: http://IP:15001（端口可在 docker/.env 中修改）
# AI 助手:  http://IP:18000
```

常用命令：

```bash
docker compose logs -f            # 查看日志
docker compose restart            # 重启服务
docker compose down               # 停止容器
```

## 钉钉推送（可选）

编辑 `config.yaml`（一键安装）或 `docker/config.yaml`（Docker），开启钉钉推送：

```yaml
webhook:
    dingtalk:
        enabled: true
        url: "https://oapi.dingtalk.com/robot/send?access_token=你的token"
        keyword: "AInew"    # 与钉钉机器人安全设置中的关键词一致
```

> 钉钉群 → 群设置 → 机器人 → 自定义机器人 → 复制 Webhook 地址。

## AI 助手 API 配置

`agent/.env` 支持多种 API 提供商，同一个千问 Key 即可：

| API 提供商 | ANTHROPIC_BASE_URL | 模型示例 | 说明 |
|-----------|-------------------|---------|------|
| 阿里千问 | `https://dashscope.aliyuncs.com/apps/anthropic` | `qwen3-coder-plus` | 国内推荐 |
| DeepSeek | `https://api.deepseek.com/anthropic` | `deepseek-chat` | 国内可用 |
| Anthropic | `https://api.anthropic.com` | `claude-sonnet-4-20250514` | 需海外网络 |

> 原理：Claude Code CLI 支持自定义 `ANTHROPIC_BASE_URL`，只要 API 兼容 Anthropic Messages 格式即可。

## 数据来源

### RSS 订阅（25 个源）

| 分类 | 来源 |
|------|------|
| 技术社区 | Hacker News、Reddit、Lobsters、Dev.to |
| 海外媒体 | TechCrunch、The Verge、Ars Technica、VentureBeat、MIT Tech Review |
| 官方博客 | OpenAI、Google AI、Hugging Face、GitHub Blog、arXiv AI |
| 国内媒体 | InfoQ、36氪、机器之心、量子位、少数派 |
| GitHub Releases | Cursor、Continue、Ollama、LangChain、Open WebUI |

### 网页采集

| 来源 | 说明 |
|------|------|
| GitHub Trending | 每日热门开源项目 |

## 项目结构

```
├── main.py                  # 主入口：抓取→过滤→推送→入库
├── install.sh               # 一键安装脚本
├── config.yaml              # 配置文件（从 .example 复制）
├── sources/                 # 数据抓取
├── filter/                  # AI 语义过滤
├── storage/                 # SQLite 存储
├── push/                    # 钉钉推送
├── web/                     # Flask Web 页面（:5001）
├── agent/                   # Chainlit AI 助手（:8000）
├── docker/                  # Docker 部署配置
└── data/                    # 运行时数据（数据库、日志）
```

## 使用

### 抓取资讯

```bash
cd /path/to/ai-news-bot

python3 main.py                 # 正式运行（抓取 + AI过滤 + 推送钉钉 + 入库）
python3 main.py --test          # 测试模式（不推送钉钉，仅入库）
python3 main.py --test --force  # 测试 + 忽略去重（首次使用推荐）
```

### 定时任务

安装脚本会自动配置每 3 小时抓取一次。如需手动配置：

```bash
crontab -e
# 添加以下行（替换为你的项目路径）：
0 */3 * * * cd /root/ai-news-bot && python3 main.py >> data/cron.log 2>&1
```

验证：

```bash
crontab -l               # 查看已配置的定时任务
tail -f data/cron.log    # 查看抓取日志
```

### 服务管理

```bash
# 查看服务状态
ss -tlnp | grep -E '5001|8000'

# 重启资讯页面
kill $(lsof -ti:5001) 2>/dev/null; nohup python3 web/app.py > data/flask.log 2>&1 &

# 重启 AI 助手（必须在项目根目录执行）
kill $(lsof -ti:8000) 2>/dev/null; nohup chainlit run agent/app.py --host 0.0.0.0 --port 8000 > data/chainlit.log 2>&1 &
```

## AI 过滤分类

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
