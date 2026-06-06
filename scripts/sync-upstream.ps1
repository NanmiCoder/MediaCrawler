# 同步上游 MediaCrawler 更新到本地 feature 分支
# 用法: .\scripts\sync-upstream.ps1 [-Branch <分支名>]

param(
    [string]$Branch = "feature/xhs-insight-pipeline",
    [string]$UpstreamRemote = "upstream",
    [string]$UpstreamBranch = "main"
)

$ErrorActionPreference = "Stop"

# 检查 upstream 远程是否配置
$remotes = git remote
if ($remotes -notcontains $UpstreamRemote) {
    Write-Host "Error: remote '$UpstreamRemote' 未配置" -ForegroundColor Red
    Write-Host "请先执行: git remote add $UpstreamRemote https://github.com/NanmiCoder/MediaCrawler.git" -ForegroundColor Yellow
    exit 1
}

# 检查工作区是否干净
$status = git status --porcelain
if ($status) {
    Write-Host "Error: 工作区有未提交的改动:" -ForegroundColor Red
    git status --short
    exit 1
}

Write-Host "==> 拉取 $UpstreamRemote 最新代码..." -ForegroundColor Cyan
git fetch $UpstreamRemote

Write-Host "==> 更新 main <- $UpstreamRemote/$UpstreamBranch ..." -ForegroundColor Cyan
git checkout main
git merge "$UpstreamRemote/$UpstreamBranch"

Write-Host "==> Rebase $Branch 到 main ..." -ForegroundColor Cyan
git checkout $Branch
git rebase main

Write-Host "==> 同步完成" -ForegroundColor Green
