#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# douyin-scraper 自动化部署脚本
# ═══════════════════════════════════════════════════════════════
# 用法：
#   chmod +x deploy.sh
#   ./deploy.sh            # 交互式部署
#   ./deploy.sh --unattended  # 非交互式（CI/CD）
#
# 我实际执行时踩过的坑：
#   - 虚拟环境不隔离 → 系统包被覆盖
#   - ffmpeg 缺失 → 音视频处理运行时才发现
#   - 权限不对 → systemd 启动失败
#   - 端口冲突 → 服务无法绑定
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# 配置（可通过环境变量覆盖）
INSTALL_DIR="${INSTALL_DIR:-/opt/douyin-scraper}"
SERVICE_USER="${SERVICE_USER:-douyin}"
API_PORT="${API_PORT:-18080}"
CHROME_PORT="${CHROME_PORT:-19222}"
WORKSPACE_DIR="${WORKSPACE_DIR:-/opt/douyin-scraper/workspaces}"
UNATTENDED="${1:-}"

echo "══════════════════════════════════════════════════"
echo "  抖音采集工具 API — 自动化部署"
echo "══════════════════════════════════════════════════"
echo ""

# ─── 1. 系统依赖检查 ─────────────────────────────────
echo ">>> [1/8] 检查系统依赖..."

check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        echo "❌ 缺少依赖: $1"
        echo "   安装: $2"
        return 1
    fi
    echo "✅ $1 已安装"
    return 0
}

MISSING=0
check_cmd python3 "apt install python3 python3-venv" || MISSING=1
check_cmd git "apt install git" || MISSING=1
check_cmd ffmpeg "apt install ffmpeg" || MISSING=1

if [ "$MISSING" -eq 1 ]; then
    echo ""
    echo "⚠️  缺少系统依赖，是否自动安装？(y/n)"
    if [ "$UNATTENDED" = "--unattended" ]; then
        echo "非交互模式：自动安装..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq python3 python3-venv python3-pip git ffmpeg
    else
        read -r answer
        if [ "$answer" = "y" ]; then
            sudo apt-get update -qq
            sudo apt-get install -y -qq python3 python3-venv python3-pip git ffmpeg
        else
            echo "请手动安装后重新运行"
            exit 1
        fi
    fi
fi

# ─── 2. 创建用户和目录 ─────────────────────────────
echo ">>> [2/8] 创建用户和目录..."

if ! id "$SERVICE_USER" &>/dev/null; then
    sudo useradd -r -s /bin/bash -d "$INSTALL_DIR" "$SERVICE_USER"
    echo "✅ 用户 $SERVICE_USER 已创建"
else
    echo "✅ 用户 $SERVICE_USER 已存在"
fi

sudo mkdir -p "$INSTALL_DIR"
sudo mkdir -p "$WORKSPACE_DIR"
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$WORKSPACE_DIR"

# ─── 3. 复制代码 ────────────────────────────────────
echo ">>> [3/8] 复制代码..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 复制 douyin_scraper 模块
sudo -u "$SERVICE_USER" cp -r "$PROJECT_ROOT/douyin_scraper" "$INSTALL_DIR/"
# 复制 API 代码
sudo -u "$SERVICE_USER" cp -r "$PROJECT_ROOT/api" "$INSTALL_DIR/"
# 复制 pyproject.toml
sudo -u "$SERVICE_USER" cp "$PROJECT_ROOT/pyproject.toml" "$INSTALL_DIR/" 2>/dev/null || true

echo "✅ 代码已复制到 $INSTALL_DIR"

# ─── 4. 创建虚拟环境 ───────────────────────────────
echo ">>> [4/8] 创建虚拟环境..."

if [ ! -d "$INSTALL_DIR/.venv" ]; then
    sudo -u "$SERVICE_USER" python3 -m venv "$INSTALL_DIR/.venv"
    echo "✅ 虚拟环境已创建"
else
    echo "✅ 虚拟环境已存在"
fi

# ─── 5. 安装 Python 依赖 ──────────────────────────
echo ">>> [5/8] 安装 Python 依赖..."

VENV_PIP="$INSTALL_DIR/.venv/bin/pip"

sudo -u "$SERVICE_USER" "$VENV_PIP" install --upgrade pip --quiet
sudo -u "$SERVICE_USER" "$VENV_PIP" install -r "$INSTALL_DIR/api/requirements.txt" --quiet
sudo -u "$SERVICE_USER" "$VENV_PIP" install -e "$INSTALL_DIR" --quiet 2>/dev/null || \
    sudo -u "$SERVICE_USER" "$VENV_PIP" install httpx --quiet

echo "✅ Python 依赖已安装"

# ─── 6. 创建 .env 文件 ────────────────────────────
echo ">>> [6/8] 创建配置文件..."

ENV_FILE="$INSTALL_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    sudo -u "$SERVICE_USER" tee "$ENV_FILE" > /dev/null << EOF
# 抖音采集工具 API 配置
DY_API_HOST=0.0.0.0
DY_API_PORT=$API_PORT
DY_API_PUBLIC_PORT=$API_PORT
DY_API_BASE_URL=http://localhost:$API_PORT
DY_WORKSPACE_DIR=$WORKSPACE_DIR
DY_CHROME_PORT=$CHROME_PORT
DY_CHROME_CDP_URL=http://localhost:$CHROME_PORT
WEB_DEV_PORT=15173
VITE_API_BASE_URL=http://localhost:$API_PORT
VITE_WS_BASE_URL=ws://localhost:$API_PORT
DY_LOG_LEVEL=INFO
DY_CORS_ORIGINS=*
DY_RELOAD=0
EOF
    echo "✅ .env 文件已创建"
else
    echo "✅ .env 文件已存在"
fi

# ─── 7. 安装 systemd 服务 ─────────────────────────
echo ">>> [7/8] 安装 systemd 服务..."

# 更新 service 文件中的路径
sudo cp "$INSTALL_DIR/api/douyin-scraper.service" /etc/systemd/system/ 2>/dev/null || true
sudo sed -i "s|/opt/douyin-scraper|$INSTALL_DIR|g" /etc/systemd/system/douyin-scraper.service
sudo sed -i "s|User=douyin|User=$SERVICE_USER|g" /etc/systemd/system/douyin-scraper.service
sudo sed -i "s|Group=douyin|Group=$SERVICE_USER|g" /etc/systemd/system/douyin-scraper.service
sudo systemctl daemon-reload
sudo systemctl enable douyin-scraper

echo "✅ systemd 服务已安装并启用"

# ─── 8. 启动服务 ──────────────────────────────────
echo ">>> [8/8] 启动服务..."

sudo systemctl restart douyin-scraper

# 等待服务启动
sleep 3

if sudo systemctl is-active --quiet douyin-scraper; then
    echo ""
    echo "══════════════════════════════════════════════════"
    echo "  ✅ 部署成功！"
    echo "══════════════════════════════════════════════════"
    echo ""
    echo "  API 地址:    http://localhost:$API_PORT"
    echo "  API 文档:    http://localhost:$API_PORT/docs"
    echo "  健康检查:    http://localhost:$API_PORT/health"
    echo "  工作目录:    $WORKSPACE_DIR"
    echo ""
    echo "  常用命令:"
    echo "    sudo systemctl status douyin-scraper"
    echo "    sudo systemctl restart douyin-scraper"
    echo "    sudo journalctl -u douyin-scraper -f"
    echo ""
else
    echo ""
    echo "══════════════════════════════════════════════════"
    echo "  ❌ 服务启动失败！"
    echo "══════════════════════════════════════════════════"
    echo ""
    echo "  排查："
    echo "    sudo journalctl -u douyin-scraper -n 50 --no-pager"
    echo "    sudo systemctl status douyin-scraper"
    exit 1
fi
