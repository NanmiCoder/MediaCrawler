# view_data.ps1 — 启动小红书数据查看器（Streamlit UI）
#
# 用法：在项目根目录执行
#   .\view_data.ps1
#
# 关键点：必须把项目根目录加进 PYTHONPATH，否则 streamlit 启动时
# 找不到 `insight` 包（conda env 里只装了 streamlit，没装项目源码）。
# 这个问题在 README 的启动命令里漏了，所以单独写成脚本。

$ErrorActionPreference = "Stop"

# 以脚本所在目录作为项目根 —— 这样从任何位置调用都能 import 到 insight
$env:PYTHONPATH = $PSScriptRoot

Write-Host "PYTHONPATH = $env:PYTHONPATH" -ForegroundColor Cyan
Write-Host "启动 Streamlit ... Ctrl+C 停止" -ForegroundColor Cyan
Write-Host ""

streamlit run insight/viewer/app.py
