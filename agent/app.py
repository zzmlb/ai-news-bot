"""AI 资讯助手 - Chainlit + Claude Code SDK（stream-json 模式）"""

import os
import json
import asyncio

import chainlit as cl

# Claude Code CLI 路径
CLAUDE_CMD = "claude"

# 工作目录：资讯系统根目录
WORK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 从 .env 读取配置
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")

# CLAUDE.md 系统指令路径
CLAUDE_MD_PATH = os.path.join(os.path.dirname(__file__), "CLAUDE.md")

# 工具名称中文映射
TOOL_NAMES = {
    "Bash": "执行命令",
    "Read": "读取文件",
    "Glob": "搜索文件",
    "Grep": "搜索内容",
}


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


def _truncate(text: str, max_len: int = 500) -> str:
    """截断过长文本"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"\n... (共 {len(text)} 字符)"


async def call_claude(prompt: str, reply: cl.Message):
    """调用 Claude Code CLI，解析 stream-json 事件流，展示思考过程"""
    system_prompt = _load_system_prompt()
    cmd = [
        CLAUDE_CMD,
        "--print",
        "--verbose",
        "--output-format", "stream-json",
        "--max-turns", "10",
        "--allowedTools", "Bash", "Read", "Glob", "Grep",
    ]
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])
    cmd.append(prompt)

    env = _build_env()

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=WORK_DIR,
        env=env,
    )

    # 跟踪活跃的 tool_use Step，key = tool_use_id
    active_steps = {}
    line_buffer = b""

    while True:
        chunk = await process.stdout.read(4096)
        if not chunk:
            break
        line_buffer += chunk

        # 按行解析 JSON
        while b"\n" in line_buffer:
            line, line_buffer = line_buffer.split(b"\n", 1)
            line_str = line.decode("utf-8", errors="replace").strip()
            if not line_str:
                continue
            try:
                event = json.loads(line_str)
            except json.JSONDecodeError:
                continue

            await _handle_event(event, reply, active_steps)

    # 处理缓冲区剩余数据
    if line_buffer:
        line_str = line_buffer.decode("utf-8", errors="replace").strip()
        if line_str:
            try:
                event = json.loads(line_str)
                await _handle_event(event, reply, active_steps)
            except json.JSONDecodeError:
                pass

    await process.wait()

    # 如果执行失败，追加错误信息
    if process.returncode != 0:
        stderr_data = await process.stderr.read()
        stderr_text = stderr_data.decode("utf-8", errors="replace").strip()
        if stderr_text and "Trace:" not in stderr_text:
            error_lines = stderr_text.split("\n")[-10:]
            await reply.stream_token(
                f"\n\n---\n**执行异常** (exit {process.returncode}):\n```\n{''.join(error_lines)}\n```"
            )


async def _handle_event(event: dict, reply: cl.Message, active_steps: dict):
    """处理单个 stream-json 事件"""
    evt_type = event.get("type", "")

    if evt_type == "assistant":
        contents = event.get("message", {}).get("content", [])
        for block in contents:
            block_type = block.get("type", "")

            if block_type == "thinking":
                # 思考过程 → 显示为可折叠的 Step
                thinking_text = block.get("thinking", "")
                if thinking_text:
                    async with cl.Step(name="思考中", type="llm") as step:
                        step.output = thinking_text

            elif block_type == "tool_use":
                # 工具调用 → 创建 Step 并显示输入
                tool_name = block.get("name", "未知工具")
                tool_id = block.get("id", "")
                tool_input = block.get("input", {})

                display_name = TOOL_NAMES.get(tool_name, tool_name)

                # 构建可读的输入描述
                input_desc = _format_tool_input(tool_name, tool_input)

                step = cl.Step(name=f"🔧 {display_name}", type="tool")
                step.input = input_desc
                await step.send()
                active_steps[tool_id] = step

            elif block_type == "text":
                # 最终文本回复 → 流式输出到主消息
                text = block.get("text", "")
                if text:
                    await reply.stream_token(text)

    elif evt_type == "user":
        # 工具执行结果
        contents = event.get("message", {}).get("content", [])
        # 也检查顶层 tool_use_result
        tool_result_str = event.get("tool_use_result", "")

        for block in contents:
            if block.get("type") == "tool_result":
                tool_id = block.get("tool_use_id", "")
                result_content = block.get("content", "")
                is_error = block.get("is_error", False)

                if tool_id in active_steps:
                    step = active_steps.pop(tool_id)
                    if is_error:
                        step.output = f"❌ 错误:\n```\n{_truncate(str(result_content))}\n```"
                    else:
                        step.output = f"```\n{_truncate(str(result_content))}\n```"
                    await step.update()

    elif evt_type == "result":
        # 最终结果（如果前面没输出文本，用这里的 result）
        # 通常 text block 已经处理了，这里做兜底
        pass


def _format_tool_input(tool_name: str, tool_input: dict) -> str:
    """格式化工具输入为可读文本"""
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        desc = tool_input.get("description", "")
        if desc:
            return f"{desc}\n```bash\n{cmd}\n```"
        return f"```bash\n{cmd}\n```"

    elif tool_name == "Read":
        return f"📄 `{tool_input.get('file_path', '')}`"

    elif tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", "")
        return f"🔍 `{pattern}`" + (f" in `{path}`" if path else "")

    elif tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", "")
        return f"🔍 `{pattern}`" + (f" in `{path}`" if path else "")

    return f"```json\n{json.dumps(tool_input, ensure_ascii=False, indent=2)}\n```"


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

    reply = cl.Message(content="")
    await reply.send()

    await call_claude(user_input, reply)

    await reply.update()
