#!/bin/bash
# ============================================
# AI News Bot 一键安装
# 用法: bash install.sh [你的千问API_Key]
# ============================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}══════ AI News Bot 一键安装 ══════${NC}"

# --- API Key（参数传入 或 交互输入） ---
QWEN_KEY="${1:-}"
if [ -z "$QWEN_KEY" ]; then
    if [ -f config.yaml ] && grep -q "sk-" config.yaml 2>/dev/null && ! grep -q "sk-xxx\|YOUR" config.yaml 2>/dev/null; then
        QWEN_KEY=$(grep "api_key" config.yaml | head -1 | sed 's/.*"\(sk-[^"]*\)".*/\1/')
        echo -e "${GREEN}复用已有 API Key${NC}"
    else
        echo -en "输入千问 API Key (从 https://bailian.console.aliyun.com 获取): "
        read -r QWEN_KEY
    fi
fi

if [ -z "$QWEN_KEY" ]; then
    echo -e "${RED}未提供 API Key，退出${NC}"
    exit 1
fi

# --- 检测/拉取代码 ---
if [ -f "main.py" ]; then
    PROJECT_DIR="$(pwd)"
else
    PROJECT_DIR="/root/ai-news-bot"
    if [ ! -f "$PROJECT_DIR/main.py" ]; then
        echo -e "${YELLOW}拉取代码...${NC}"
        apt-get update -qq > /dev/null 2>&1
        apt-get install -y -qq git python3 python3-pip > /dev/null 2>&1
        git clone https://github.com/zzmlb/ai-news-bot.git "$PROJECT_DIR" 2>&1 | tail -1
    fi
fi
cd "$PROJECT_DIR"

# --- 装依赖 ---
echo -e "${YELLOW}安装依赖...${NC}"
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq python3 python3-pip > /dev/null 2>&1
pip install -q -r requirements.txt 2>/dev/null

# --- 装 Node.js + Claude CLI（AI 助手需要） ---
if ! command -v claude &>/dev/null; then
    echo -e "${YELLOW}安装 Claude CLI...${NC}"
    if ! command -v node &>/dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_20.x 2>/dev/null | bash - > /dev/null 2>&1
        apt-get install -y -qq nodejs > /dev/null 2>&1
    fi
    npm install -g @anthropic-ai/claude-code > /dev/null 2>&1
fi

# --- 生成配置（全自动） ---
mkdir -p data

cat > config.yaml << EOF
qwen:
    api_key: "${QWEN_KEY}"
    model: "qwen-turbo"
webhook:
    dingtalk:
        enabled: false
        url: ""
        keyword: "AInew"
EOF

cat > agent/.env << EOF
ANTHROPIC_BASE_URL=https://dashscope.aliyuncs.com/apps/anthropic
ANTHROPIC_AUTH_TOKEN=${QWEN_KEY}
ANTHROPIC_MODEL=qwen3-coder-plus
EOF

# --- 启动服务 ---
echo -e "${YELLOW}启动服务...${NC}"
kill $(lsof -ti:5001) 2>/dev/null || true
kill $(lsof -ti:8000) 2>/dev/null || true
sleep 1

cd "$PROJECT_DIR"
nohup python3 web/app.py > "$PROJECT_DIR/data/flask.log" 2>&1 &
nohup chainlit run agent/app.py --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/data/chainlit.log" 2>&1 &
sleep 3

# --- 定时任务 ---
if ! crontab -l 2>/dev/null | grep -q "${PROJECT_DIR}.*main.py"; then
    (crontab -l 2>/dev/null; echo "0 */3 * * * cd ${PROJECT_DIR} && python3 main.py >> data/cron.log 2>&1") | crontab -
fi

# --- 防火墙 ---
if command -v ufw &>/dev/null && ufw status | grep -q "active"; then
    ufw allow 5001/tcp > /dev/null 2>&1
    ufw allow 8000/tcp > /dev/null 2>&1
fi

# --- 完成 ---
IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}══════ 安装完成 ══════${NC}"
echo -e "  资讯页面: ${CYAN}http://${IP}:5001${NC}"
echo -e "  AI 助手:  ${CYAN}http://${IP}:8000${NC}"
echo ""
echo -e "  ${YELLOW}首次使用请手动抓取一次资讯:${NC}"
echo -e "  ${CYAN}cd ${PROJECT_DIR} && python3 main.py --test --force${NC}"
echo ""
