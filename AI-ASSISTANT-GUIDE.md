# Chainlit + Claude Code CLI：AI 助手搭建指南

> 通用技术方案，可复用于任何项目。通过 Chainlit 提供 Web 聊天界面，后端调用 Claude Code CLI 作为 AI 引擎，支持接入千问、DeepSeek、Anthropic 等大模型。

## 架构原理

```
浏览器 ──WebSocket──▶ Chainlit (Python Web 框架)
                           │
                           │ asyncio.create_subprocess_exec
                           ▼
                     Claude Code CLI (Node.js)
                           │
                           │ HTTPS (Anthropic Messages API 格式)
                           ▼
                   大模型 API 端点
                   ├── 阿里千问 dashscope
                   ├── DeepSeek
                   └── Anthropic (原生)
```

**核心思路**：Claude Code CLI 本身支持通过环境变量自定义 API 端点和模型。只要目标 API 兼容 **Anthropic Messages 格式**（`/v1/messages`），就可以直接替换后端模型，无需修改任何代码。

**为什么用 Claude Code CLI 而不是直接调用 API？**

- 内置多轮对话和上下文管理
- 自带工具调用能力（Bash、Read、Glob、Grep 等），AI 可以执行命令、读文件、搜索代码
- `--output-format stream-json` 提供结构化事件流，便于前端解析和展示
- 一行命令替换模型，零代码改动

## 前置要求

| 依赖 | 版本 | 安装命令 |
|------|------|---------|
| Python | 3.10+ | 系统自带或 `apt install python3` |
| pip | - | `apt install python3-pip` |
| Node.js | 18+ | 见下方安装命令 |
| Claude Code CLI | latest | `npm install -g @anthropic-ai/claude-code` |
| chainlit | 2.0+ | `pip install chainlit` |

**安装 Node.js（如未安装）：**

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
```

**安装 Claude Code CLI：**

```bash
npm install -g @anthropic-ai/claude-code

# 验证
claude --version
```

## 目录结构

将以下文件放到项目的 `agent/` 目录下（目录名可自定义）：

```
your-project/
├── agent/
│   ├── app.py              # Chainlit 主程序
│   ├── .env                # API 配置（不提交 git）
│   ├── .env.example        # 配置模板（提交 git）
│   └── CLAUDE.md           # 系统指令（定义 AI 的角色和能力）
├── .gitignore              # 需排除 agent/.env
└── ...
```

## 第 1 步：配置 API 密钥

### 1.1 创建配置文件

```bash
cp agent/.env.example agent/.env
```

### 1.2 编辑 `agent/.env`

文件中有且仅有 3 个变量需要配置：

```bash
ANTHROPIC_BASE_URL=<API 端点地址>
ANTHROPIC_AUTH_TOKEN=<你的 API Key>
ANTHROPIC_MODEL=<模型名称>
```

**变量说明：**

| 变量 | 含义 | 必填 |
|------|------|------|
| `ANTHROPIC_BASE_URL` | 大模型 API 的基础 URL。Claude Code CLI 会向 `{BASE_URL}/v1/messages` 发请求 | 是 |
| `ANTHROPIC_AUTH_TOKEN` | API 认证密钥，通过 HTTP Header `x-api-key` 传递 | 是 |
| `ANTHROPIC_MODEL` | 模型名称，传递给 API 的 `model` 字段 | 是 |

### 1.3 各 API 提供商配置参考

#### 阿里千问 Qwen（国内推荐）

```bash
ANTHROPIC_BASE_URL=https://dashscope.aliyuncs.com/apps/anthropic
ANTHROPIC_AUTH_TOKEN=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_MODEL=qwen3-coder-plus
```

- **获取 API Key**：注册 [阿里云百炼平台](https://bailian.console.aliyun.com/) → 左侧菜单「API-KEY 管理」→ 创建
- **可用模型**：`qwen3-coder-plus`（推荐，编程能力强）、`qwen-max`、`qwen-plus`、`qwen-turbo`
- **端点说明**：`/apps/anthropic` 是千问的 Anthropic 兼容端点（不是 `/compatible-mode/v1`，那个是 OpenAI 格式）
- **网络要求**：国内服务器可直接访问；部分海外 IP 可能被阿里云拒绝 TLS 握手

#### DeepSeek

```bash
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_AUTH_TOKEN=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_MODEL=deepseek-chat
```

- **获取 API Key**：注册 [DeepSeek 开放平台](https://platform.deepseek.com/) → API Keys
- **可用模型**：`deepseek-chat`、`deepseek-reasoner`
- **网络要求**：国内外均可访问

#### Anthropic 原生

```bash
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_AUTH_TOKEN=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

- **获取 API Key**：注册 [Anthropic Console](https://console.anthropic.com/) → API Keys
- **可用模型**：`claude-opus-4-20250514`、`claude-sonnet-4-20250514`、`claude-haiku-4-5-20251001`
- **网络要求**：需海外网络

### 1.4 `.env.example` 模板

将以下内容保存为 `agent/.env.example`，提交到 git 供其他人参考：

```bash
# ============================================================
# AI 助手配置 — Claude Code CLI 后端
# ============================================================
# 复制本文件为 .env，填入对应的值：
#   cp .env.example .env
#
# 只需配置 3 个变量：BASE_URL + AUTH_TOKEN + MODEL
# 选择以下任一 API 提供商，取消注释并填入 Key 即可。
# ============================================================

# --- 阿里千问 Qwen（国内推荐）---
# 获取 Key: https://bailian.console.aliyun.com/ → API-KEY 管理
ANTHROPIC_BASE_URL=https://dashscope.aliyuncs.com/apps/anthropic
ANTHROPIC_AUTH_TOKEN=your-qwen-api-key
ANTHROPIC_MODEL=qwen3-coder-plus

# --- DeepSeek ---
# 获取 Key: https://platform.deepseek.com/api_keys
# ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
# ANTHROPIC_AUTH_TOKEN=your-deepseek-api-key
# ANTHROPIC_MODEL=deepseek-chat

# --- Anthropic 原生（需海外网络）---
# 获取 Key: https://console.anthropic.com/
# ANTHROPIC_BASE_URL=https://api.anthropic.com
# ANTHROPIC_AUTH_TOKEN=your-anthropic-api-key
# ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

### 1.5 安全：确保 .env 不被提交

在项目根目录的 `.gitignore` 中添加：

```gitignore
agent/.env
```

## 第 2 步：编写系统指令（CLAUDE.md）

`agent/CLAUDE.md` 定义了 AI 的角色、能力范围和行为约束。Claude Code CLI 通过 `--system-prompt` 参数加载此文件。

**编写要点：**

1. 明确角色定位（你是 XX 项目的助手）
2. 列出项目目录结构和核心模块
3. 说明 AI 可以操作的范围（哪些工具可用、哪些文件可读）
4. 添加行为约束（如只读操作、不修改配置等）

**模板示例：**

```markdown
# [项目名称] AI 助手

你是 [项目名称] 的智能助手。请始终使用中文回复。

## 项目概述

[一句话描述项目功能]

## 目录结构

[列出关键文件和目录]

## 你的能力

1. 查询和分析数据
2. 阅读代码并解释逻辑
3. 执行诊断命令排查问题
4. 提供优化建议

## 常用命令

[列出 AI 可能需要执行的 bash 命令]

## 注意事项

- 工作目录为 /path/to/project/
- 不要修改生产配置
- 数据库查询使用只读操作
```

> 系统指令的质量直接决定 AI 的回答质量。写得越具体，AI 越能给出精准的回答。

## 第 3 步：编写 Chainlit 主程序（app.py）

以下是完整的 `agent/app.py`，可直接复制使用：

```python
"""AI 助手 - Chainlit + Claude Code CLI（stream-json 模式）"""

import os
import json
import asyncio
import logging

import chainlit as cl

logger = logging.getLogger("ai-assistant")

# Claude Code CLI 命令
CLAUDE_CMD = "claude"

# 工作目录：项目根目录（根据实际情况调整相对路径）
WORK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 配置文件路径
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")
CLAUDE_MD_PATH = os.path.join(os.path.dirname(__file__), "CLAUDE.md")


def _load_env() -> dict:
    """从 .env 文件加载配置"""
    env = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()
    return env


def _build_env() -> dict:
    """构建子进程环境变量"""
    env = os.environ.copy()
    env.update(_load_env())
    env["DISABLE_CLAUDE_TELEMETRY"] = "1"
    # 防止嵌套 Claude 会话冲突
    env.pop("CLAUDECODE", None)
    return env


def _load_system_prompt() -> str:
    """读取 CLAUDE.md 作为系统指令"""
    if os.path.exists(CLAUDE_MD_PATH):
        with open(CLAUDE_MD_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


async def call_claude(prompt: str, reply: cl.Message):
    """
    调用 Claude Code CLI，解析 stream-json 事件流。

    CLI 参数说明：
      --print           非交互模式，直接输出结果
      --verbose          启用详细输出（stream-json 需要此参数）
      --output-format    输出格式，stream-json 为逐行 JSON 事件流
      --max-turns        最大对话轮次（含工具调用）
      --allowedTools     允许 AI 使用的工具列表
      --model            模型名称（从 .env 读取）
      --system-prompt    系统指令（从 CLAUDE.md 读取）
    """
    system_prompt = _load_system_prompt()
    dot_env = _load_env()
    model = dot_env.get("ANTHROPIC_MODEL", "")

    cmd = [
        CLAUDE_CMD,
        "--print",
        "--verbose",
        "--output-format", "stream-json",
        "--max-turns", "10",
        "--allowedTools", "Bash", "Read", "Glob", "Grep",
    ]
    if model:
        cmd.extend(["--model", model])
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])
    cmd.append(prompt)

    env = _build_env()
    logger.info(f"调用模型: {model or 'default'}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=WORK_DIR,
        env=env,
    )

    # 逐块读取 stdout，按行解析 JSON 事件
    line_buffer = b""
    while True:
        chunk = await process.stdout.read(4096)
        if not chunk:
            break
        line_buffer += chunk

        while b"\n" in line_buffer:
            line, line_buffer = line_buffer.split(b"\n", 1)
            line_str = line.decode("utf-8", errors="replace").strip()
            if not line_str:
                continue
            try:
                event = json.loads(line_str)
            except json.JSONDecodeError:
                continue
            await _handle_event(event, reply)

    # 处理缓冲区剩余数据
    if line_buffer:
        line_str = line_buffer.decode("utf-8", errors="replace").strip()
        if line_str:
            try:
                await _handle_event(json.loads(line_str), reply)
            except json.JSONDecodeError:
                pass

    await process.wait()

    # 错误处理
    if process.returncode != 0:
        stderr_data = await process.stderr.read()
        stderr_text = stderr_data.decode("utf-8", errors="replace").strip()
        logger.error(f"CLI 退出码 {process.returncode}: {stderr_text[:200]}")
        if stderr_text and "Trace:" not in stderr_text:
            error_lines = stderr_text.split("\n")[-5:]
            await reply.stream_token(
                f"\n\n---\n**执行异常** (exit {process.returncode}):\n"
                f"```\n{''.join(error_lines)}\n```"
            )


async def _handle_event(event: dict, reply: cl.Message):
    """
    处理 stream-json 事件。

    事件类型：
      system    - 初始化信息（模型、工具列表等），忽略
      assistant - AI 回复内容，提取 text 块发送给前端
      result    - 最终结果摘要，忽略
    """
    if event.get("type") == "assistant":
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "text" and block.get("text"):
                await reply.stream_token(block["text"])


# ──────────────── Chainlit 事件处理 ────────────────


@cl.on_chat_start
async def on_start():
    """对话开始时的欢迎信息（根据项目自定义）"""
    await cl.Message(
        content=(
            "👋 你好！我是 AI 助手。\n\n"
            "请问有什么可以帮你的？"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """处理用户消息"""
    user_input = message.content.strip()
    if not user_input:
        return

    logger.info(f"收到消息: {user_input[:100]}")
    reply = cl.Message(content="")
    await reply.send()

    try:
        await call_claude(user_input, reply)
    except Exception as e:
        logger.exception(f"调用异常: {e}")
        await reply.stream_token(f"\n\n调用失败: {e}")

    await reply.update()
```

**需要根据项目调整的地方：**

| 位置 | 说明 |
|------|------|
| `WORK_DIR` | 改为你项目的根目录路径（CLI 的 Bash/Read 等工具在此目录下执行） |
| `--allowedTools` | 根据需要增减工具，可选：`Bash` `Read` `Write` `Edit` `Glob` `Grep` |
| `--max-turns` | 最大对话轮次，包含工具调用。复杂任务可调大 |
| `on_start()` | 欢迎消息，自定义为项目相关的介绍 |

## 第 4 步：启动和验证

### 4.1 验证 API 连通性

启动前先测试 CLI 能否正常调用模型：

```bash
# 加载配置
source agent/.env
export ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN ANTHROPIC_MODEL
export DISABLE_CLAUDE_TELEMETRY=1

# 测试调用
claude --print --model "$ANTHROPIC_MODEL" "说OK"
```

预期输出：`OK`

如果报错：
- `Connection reset by peer` → 服务器网络无法访问该 API 端点
- `invalid api-key` → API Key 无效
- `model not found` → 模型名称不正确

### 4.2 启动 Chainlit

```bash
# 前台启动（调试用）
chainlit run agent/app.py --host 0.0.0.0 --port 8000

# 后台启动（生产用）
nohup chainlit run agent/app.py --host 0.0.0.0 --port 8000 > data/chainlit.log 2>&1 &
```

访问 `http://IP:8000` 即可打开聊天界面。

### 4.3 防火墙放行

如果外部无法访问，检查防火墙：

```bash
# UFW
ufw allow 8000/tcp && ufw reload

# iptables
iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

## stream-json 事件格式参考

Claude Code CLI `--output-format stream-json` 输出的每行是一个 JSON 对象：

**1. system 事件（初始化）：**

```json
{
  "type": "system",
  "subtype": "init",
  "model": "qwen3-coder-plus",
  "tools": ["Bash", "Read", "Glob", "Grep", ...],
  "session_id": "xxx"
}
```

**2. assistant 事件（AI 回复）：**

```json
{
  "type": "assistant",
  "message": {
    "model": "qwen3-coder-plus",
    "content": [
      {"type": "text", "text": "这是 AI 的回复内容"}
    ]
  }
}
```

**3. result 事件（结束）：**

```json
{
  "type": "result",
  "subtype": "success",
  "result": "最终文本结果",
  "duration_ms": 1876,
  "num_turns": 1
}
```

> 当前 `app.py` 只提取 `assistant` 事件中的 `text` 块。如需展示工具调用过程（如 AI 执行了什么命令），可在 `_handle_event` 中处理 `tool_use` 和 `tool_result` 类型的 content block。

## 常见问题

### Q: 千问端点用 `/compatible-mode/v1` 还是 `/apps/anthropic`？

**必须用 `/apps/anthropic`**。`/compatible-mode/v1` 是 OpenAI 格式端点，Claude Code CLI 需要的是 Anthropic Messages 格式。

### Q: 环境变量用 `ANTHROPIC_API_KEY` 还是 `ANTHROPIC_AUTH_TOKEN`？

**用 `ANTHROPIC_AUTH_TOKEN`**。`ANTHROPIC_API_KEY` 是 Anthropic Python SDK 的变量，Claude Code CLI 使用 `ANTHROPIC_AUTH_TOKEN`。

### Q: 海外服务器无法访问千问 API？

阿里云 dashscope 的部分端点会对海外 IP 做 TLS 拦截。可通过 `curl` 诊断：

```bash
curl -v https://dashscope.aliyuncs.com/apps/anthropic 2>&1 | grep -i "ssl\|reset\|error"
```

如果看到 `Connection reset by peer`，说明被拦截了。解决方案：
- 使用国内服务器部署
- 换用 DeepSeek（境外可用）
- 使用 Anthropic 原生 API

### Q: 如何在 Docker 中部署？

Dockerfile 中需安装 Node.js 和 Claude Code CLI：

```dockerfile
# 安装 Node.js + Claude Code CLI
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
      | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
      > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y nodejs \
    && npm install -g @anthropic-ai/claude-code
```

`agent/.env` 通过 volume 挂载注入：

```yaml
volumes:
  - ./agent/.env:/app/agent/.env:ro
```

### Q: 如何更换模型？

只需修改 `agent/.env` 中的 3 个变量，重启 Chainlit 即可。无需改代码。

### Q: 如何增加 AI 可用的工具？

修改 `app.py` 中 `--allowedTools` 参数。Claude Code CLI 支持的工具：

| 工具 | 能力 | 风险等级 |
|------|------|---------|
| `Bash` | 执行任意 shell 命令 | 高 |
| `Read` | 读取文件内容 | 低 |
| `Write` | 写入/创建文件 | 高 |
| `Edit` | 编辑文件指定内容 | 高 |
| `Glob` | 按模式搜索文件名 | 低 |
| `Grep` | 按正则搜索文件内容 | 低 |

> 生产环境建议只开放 `Read`、`Glob`、`Grep` 等只读工具。`Bash` 和 `Write`/`Edit` 按需开放。
