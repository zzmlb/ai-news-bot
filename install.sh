#!/bin/bash
# ============================================
# AI News Bot 一键安装脚本
# 用法: curl -sL <url> | bash
# 或者: bash install.sh
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔════════════════════════════════════════╗"
echo "║      AI News Bot 一键安装              ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# ---------- 0. 检测项目目录 ----------
# 如果在已有项目中运行，使用当前目录；否则 clone
if [ -f "main.py" ] && [ -f "config.yaml.example" ]; then
    PROJECT_DIR="$(pwd)"
    echo -e "${GREEN}检测到项目目录: $PROJECT_DIR${NC}"
else
    INSTALL_DIR="${INSTALL_DIR:-/root/ai-news-bot}"
    if [ -d "$INSTALL_DIR" ] && [ -f "$INSTALL_DIR/main.py" ]; then
        PROJECT_DIR="$INSTALL_DIR"
        echo -e "${GREEN}使用已有目录: $PROJECT_DIR${NC}"
    else
        echo -e "${YELLOW}[1/6] 拉取代码...${NC}"
        apt-get update -qq && apt-get install -y -qq git python3 python3-pip > /dev/null 2>&1
        git clone https://github.com/zzmlb/ai-news-bot.git "$INSTALL_DIR" 2>/dev/null || {
            echo -e "${RED}git clone 失败，请手动下载代码后在项目目录运行 bash install.sh${NC}"
            exit 1
        }
        PROJECT_DIR="$INSTALL_DIR"
    fi
fi

cd "$PROJECT_DIR"

# ---------- 1. 系统依赖 ----------
echo -e "${YELLOW}[1/6] 安装系统依赖...${NC}"
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq python3 python3-pip > /dev/null 2>&1
echo -e "${GREEN}  Python3 已就绪${NC}"

# ---------- 2. Python 依赖 ----------
echo -e "${YELLOW}[2/6] 安装 Python 依赖...${NC}"
pip install -q -r requirements.txt 2>/dev/null
echo -e "${GREEN}  Python 依赖安装完成${NC}"

# ---------- 3. 收集 API Key ----------
echo ""
echo -e "${CYAN}━━━━━━━━━━ 配置 API Key ━━━━━━━━━━${NC}"
echo ""

# 千问 API Key
if [ -f config.yaml ] && grep -q "sk-" config.yaml 2>/dev/null && ! grep -q "sk-xxx" config.yaml 2>/dev/null; then
    echo -e "${GREEN}  config.yaml 已配置，跳过${NC}"
    QWEN_KEY=""
else
    echo -e "请输入 ${CYAN}千问 API Key${NC}（用于 AI 过滤，从 https://bailian.console.aliyun.com 获取）"
    echo -en "  API Key (sk-xxx): "
    read -r QWEN_KEY
    if [ -z "$QWEN_KEY" ]; then
        echo -e "${RED}  未输入 API Key，跳过配置（后续需手动编辑 config.yaml）${NC}"
    fi
fi

# 钉钉 Webhook（可选）
echo ""
echo -e "请输入 ${CYAN}钉钉 Webhook URL${NC}（可选，回车跳过）"
echo -en "  Webhook URL: "
read -r DINGTALK_URL

# ---------- 4. 生成配置文件 ----------
echo ""
echo -e "${YELLOW}[3/6] 生成配置文件...${NC}"

# config.yaml
if [ -n "$QWEN_KEY" ]; then
    cat > config.yaml << YAML
qwen:
    api_key: "${QWEN_KEY}"
    model: "qwen-turbo"

webhook:
    dingtalk:
        enabled: $([ -n "$DINGTALK_URL" ] && echo "true" || echo "false")
        url: "${DINGTALK_URL:-https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN}"
        keyword: "AInew"
YAML
    echo -e "${GREEN}  config.yaml 已生成${NC}"
fi

# agent/.env（使用同一个千问 Key）
if [ -n "$QWEN_KEY" ]; then
    cat > agent/.env << ENV
ANTHROPIC_BASE_URL=https://dashscope.aliyuncs.com/apps/anthropic
ANTHROPIC_AUTH_TOKEN=${QWEN_KEY}
ANTHROPIC_MODEL=qwen3-coder-plus
ENV
    echo -e "${GREEN}  agent/.env 已生成${NC}"
elif [ ! -f agent/.env ]; then
    cp agent/.env.example agent/.env
    echo -e "${YELLOW}  agent/.env 使用模板（需手动编辑）${NC}"
fi

# 确保 data 目录存在
mkdir -p data

# ---------- 5. 测试运行 ----------
echo ""
echo -e "${YELLOW}[4/6] 测试抓取资讯...${NC}"

if [ -n "$QWEN_KEY" ] || ([ -f config.yaml ] && grep -q "sk-" config.yaml 2>/dev/null); then
    python3 main.py --test --force 2>&1 | tail -5
    echo ""
    ARTICLE_COUNT=$(python3 -c "import sqlite3,os; c=sqlite3.connect('data/news.db'); print(c.execute('SELECT COUNT(*) FROM articles').fetchone()[0])" 2>/dev/null || echo "0")
    echo -e "${GREEN}  数据库已有 ${ARTICLE_COUNT} 条资讯${NC}"
else
    echo -e "${YELLOW}  跳过测试（未配置 API Key）${NC}"
fi

# ---------- 6. 启动服务 ----------
echo ""
echo -e "${YELLOW}[5/6] 启动 Web 服务...${NC}"

# 停止旧进程
pkill -f "python3 web/app.py" 2>/dev/null || true
pkill -f "chainlit run agent/app.py" 2>/dev/null || true
sleep 1

# 启动 Flask
nohup python3 web/app.py > data/flask.log 2>&1 &
sleep 1
if ss -tlnp | grep -q ":5001"; then
    echo -e "${GREEN}  资讯页面已启动: http://$(hostname -I | awk '{print $1}'):5001${NC}"
else
    echo -e "${RED}  Flask 启动失败，请查看 data/flask.log${NC}"
fi

# 启动 Chainlit（需要 Node.js + Claude CLI）
if command -v claude &>/dev/null; then
    nohup chainlit run agent/app.py --host 0.0.0.0 --port 8000 > data/chainlit.log 2>&1 &
    sleep 2
    if ss -tlnp | grep -q ":8000"; then
        echo -e "${GREEN}  AI 助手已启动: http://$(hostname -I | awk '{print $1}'):8000${NC}"
    else
        echo -e "${RED}  Chainlit 启动失败，请查看 data/chainlit.log${NC}"
    fi
else
    echo -e "${YELLOW}  跳过 AI 助手（未安装 Claude CLI）${NC}"
    echo -e "${YELLOW}  如需安装: curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt install -y nodejs && npm install -g @anthropic-ai/claude-code${NC}"
fi

# ---------- 7. 定时任务 ----------
echo ""
echo -e "${YELLOW}[6/6] 设置定时任务...${NC}"
CRON_CMD="0 */3 * * * cd ${PROJECT_DIR} && python3 main.py >> data/cron.log 2>&1"
if crontab -l 2>/dev/null | grep -q "ai-news-bot\|${PROJECT_DIR}.*main.py"; then
    echo -e "${GREEN}  定时任务已存在，跳过${NC}"
else
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo -e "${GREEN}  已添加定时任务（每 3 小时自动抓取）${NC}"
fi

# ---------- 完成 ----------
echo ""
echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           安装完成!                    ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""
IP=$(hostname -I | awk '{print $1}')
echo -e "  资讯页面: ${GREEN}http://${IP}:5001${NC}"
echo -e "  全部资讯: ${GREEN}http://${IP}:5001/articles${NC}"
if command -v claude &>/dev/null; then
    echo -e "  AI 助手:  ${GREEN}http://${IP}:8000${NC}"
fi
echo -e "  项目目录: ${GREEN}${PROJECT_DIR}${NC}"
echo ""
echo -e "  ${YELLOW}提示: 首页显示今日资讯，如果刚部署可能为空，请点\"查看历史资讯\"${NC}"
echo ""
