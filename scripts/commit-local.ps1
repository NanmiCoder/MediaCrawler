# 提交并推送本地 feature 分支的定制代码
# 用法: .\scripts\commit-local.ps1 -Message "feat: xxx" [-Branch <分支名>]

param(
    [Parameter(Mandatory = $true)]
    [string]$Message,
    [string]$Branch = "feature/xhs-insight-pipeline"
)

$ErrorActionPreference = "Stop"

# 检查是否在目标 feature 分支
$current = git rev-parse --abbrev-ref HEAD
if ($current -ne $Branch) {
    Write-Host "Error: 当前分支 '$current'，期望 '$Branch'" -ForegroundColor Red
    Write-Host "请先执行: git checkout $Branch" -ForegroundColor Yellow
    exit 1
}

# 检查是否有改动
$status = git status --porcelain
if (-not $status) {
    Write-Host "没有可提交的改动" -ForegroundColor Yellow
    exit 0
}

Write-Host "==> 待提交改动:" -ForegroundColor Cyan
git status --short

Write-Host "==> git add ." -ForegroundColor Cyan
git add .

Write-Host "==> git commit ..." -ForegroundColor Cyan
git commit -m $Message

Write-Host "==> git push origin $Branch ..." -ForegroundColor Cyan
git push origin $Branch

Write-Host "==> 提交并推送完成" -ForegroundColor Green
