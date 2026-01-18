#!/bin/bash

echo "════════════════════════════════════════════════════════════════"
echo "              MediaCrawler API Server 启动脚本                  "
echo "════════════════════════════════════════════════════════════════"
echo ""

# 进入项目目录
cd "$(dirname "$0")"

# 激活虚拟环境
echo ">>> 激活虚拟环境..."
source venv/bin/activate

# 显示配置
echo ""
echo ">>> API 配置:"
echo "  端口: 8080"
echo "  文档: http://localhost:8080/docs"
echo "  支持平台: 抖音(dy) | 小红书(xhs) | 知乎(zhihu)"
echo ""

# 检查依赖
echo ">>> 检查依赖..."
python -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  正在安装 API 依赖..."
    pip install fastapi uvicorn pydantic -q
    echo "  依赖安装完成"
fi

echo ""
echo ">>> 启动 API 服务器..."
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  🚀 API 文档: http://localhost:8080/docs                      ║"
echo "║  📊 API 端点: http://localhost:8080/api/search               ║"
echo "║  🔗 支持平台: 抖音 | 小红书 | 知乎                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "  按 Ctrl+C 停止服务"
echo ""

# 启动 API 服务
python api_server.py
