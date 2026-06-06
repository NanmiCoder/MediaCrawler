# Sync upstream MediaCrawler into a local feature branch.
# Usage: .\scripts\sync-upstream.ps1 [-Branch <branch>]

param(
    [string]$Branch = "feature/xhs-insight-pipeline",
    [string]$UpstreamRemote = "upstream",
    [string]$UpstreamBranch = "main"
)

$ErrorActionPreference = "Stop"

# Verify the upstream remote is configured.
$remotes = git remote
if ($remotes -notcontains $UpstreamRemote) {
    Write-Host "ERROR: remote '$UpstreamRemote' not configured." -ForegroundColor Red
    Write-Host "Run: git remote add $UpstreamRemote https://github.com/NanmiCoder/MediaCrawler.git" -ForegroundColor Yellow
    exit 1
}

# Refuse to proceed with a dirty working tree (rebase would lose work).
$status = git status --porcelain
if ($status) {
    Write-Host "ERROR: working tree has uncommitted changes:" -ForegroundColor Red
    git status --short
    exit 1
}

Write-Host "==> Fetching $UpstreamRemote ..." -ForegroundColor Cyan
git fetch $UpstreamRemote

Write-Host "==> Updating main from $UpstreamRemote/$UpstreamBranch ..." -ForegroundColor Cyan
git checkout main
git merge "$UpstreamRemote/$UpstreamBranch"

Write-Host "==> Rebasing $Branch onto main ..." -ForegroundColor Cyan
git checkout $Branch
git rebase main

Write-Host "==> Sync complete." -ForegroundColor Green
