"""AI 资讯助手 - Chainlit + Claude Code CLI（stream-json 模式）"""

import os
import json
import asyncio
import logging

import chainlit as cl

logger = logging.getLogger("ai-assistant")

# Claude Code CLI 路径
CLAUDE_CMD = "claude"

# 工作目录：资讯系统根目录
WORK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 从 .env 读取配置
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")

# CLAUDE.md 系统指令路径
CLAUDE_MD_PATH = os.path.join(os.path.dirname(__file__), "CLAUDE.md")


def _load_env() -> dict:
    """从 .env 文件加载环境变量"""
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
    dot_env = _load_env()
    env.update(dot_env)
    env["DISABLE_CLAUDE_TELEMETRY"] = "1"
    env.pop("CLAUDECODE", None)
    return env


def _load_system_prompt() -> str:
    """读取 CLAUDE.md 作为系统指令"""
    if os.path.exists(CLAUDE_MD_PATH):
        with open(CLAUDE_MD_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


async def call_claude(prompt: str, reply: cl.Message):
    """调用 Claude Code CLI，解析 stream-json 事件流"""
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
                event = json.loads(line_str)
                await _handle_event(event, reply)
            except json.JSONDecodeError:
                pass

    await process.wait()

    if process.returncode != 0:
        stderr_data = await process.stderr.read()
        stderr_text = stderr_data.decode("utf-8", errors="replace").strip()
        logger.error(f"CLI 退出码 {process.returncode}: {stderr_text[:200]}")
        if stderr_text and "Trace:" not in stderr_text:
            error_lines = stderr_text.split("\n")[-5:]
            await reply.stream_token(
                f"\n\n---\n**执行异常** (exit {process.returncode}):\n```\n{''.join(error_lines)}\n```"
            )


async def _handle_event(event: dict, reply: cl.Message):
    """处理单个 stream-json 事件"""
    evt_type = event.get("type", "")

    if evt_type == "assistant":
        contents = event.get("message", {}).get("content", [])
        for block in contents:
            if block.get("type") == "text":
                text = block.get("text", "")
                if text:
                    await reply.stream_token(text)


@cl.on_chat_start
async def on_start():
    """对话开始时的欢迎信息"""
    await cl.Message(
        content=(
            "👋 你好！我是 **AI 资讯助手**。\n\n"
            "我可以帮你：\n"
            "- 📊 查询已抓取的资讯数据\n"
            "- 📋 查看定时任务日志\n"
            "- 🔍 分析系统代码和配置\n"
            "- 🛠️ 排查运行问题\n\n"
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
