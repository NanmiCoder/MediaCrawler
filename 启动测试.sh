#!/bin/bash

# MediaCrawler 启动脚本

echo "=================================="
echo "  MediaCrawler - 抖音搜索下载工具"
echo "=================================="
echo ""

# 进入项目目录
cd "$(dirname "$0")"

# 激活虚拟环境
echo ">>> 激活虚拟环境..."
source venv/bin/activate

# 显示配置
echo ""
echo ">>> 当前配置:"
echo "  平台: 抖音 (dy)"
echo "  关键词: 美食教程"
echo "  爬取数量: 3个视频"
echo "  下载视频: 开启"
echo "  保存格式: JSON"
echo ""

# 提示
echo ">>> 准备启动程序..."
echo ""
echo "⚠️  提示:"
echo "  1. 程序会自动打开浏览器"
echo "  2. 请用手机抖音扫描二维码登录"
echo "  3. 登录成功后会自动开始搜索"
echo "  4. 结果保存在 data/dy/ 目录"
echo ""

read -p "按 Enter 键开始..."

# 启动程序
echo ""
echo ">>> 启动 MediaCrawler..."
echo ""

python main.py

echo ""
echo "=================================="
echo "  程序已结束"
echo "=================================="
echo ""
echo ">>> 查看结果:"
echo "  JSON数据: data/dy/json/"
echo "  视频文件: data/dy/videos/"
echo ""
