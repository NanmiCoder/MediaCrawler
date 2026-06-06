# Stage, commit, and push local customizations on a feature branch.
# Usage: .\scripts\commit-local.ps1 -Message "feat: xxx" [-Branch <branch>]

param(
    [Parameter(Mandatory = $true)]
    [string]$Message,
    [string]$Branch = "feature/xhs-insight-pipeline"
)

$ErrorActionPreference = "Stop"

# Refuse to run on the wrong branch (avoid committing custom code onto main).
$current = git rev-parse --abbrev-ref HEAD
if ($current -ne $Branch) {
    Write-Host "ERROR: current branch is '$current', expected '$Branch'." -ForegroundColor Red
    Write-Host "Run: git checkout $Branch" -ForegroundColor Yellow
    exit 1
}

# Bail out if there is nothing to commit.
$status = git status --porcelain
if (-not $status) {
    Write-Host "No changes to commit." -ForegroundColor Yellow
    exit 0
}

Write-Host "==> Changes to commit:" -ForegroundColor Cyan
git status --short

Write-Host "==> git add ." -ForegroundColor Cyan
git add .

Write-Host "==> git commit ..." -ForegroundColor Cyan
git commit -m $Message

Write-Host "==> git push origin $Branch ..." -ForegroundColor Cyan
git push origin $Branch

Write-Host "==> Commit and push complete." -ForegroundColor Green
