# PowerShell Script to Initialize and Push to GitHub

Write-Host "=== Robotic Arm Health Monitoring System - Git Setup ===" -ForegroundColor Cyan

# 1. Check Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Git is not found in your PATH." -ForegroundColor Yellow
    Write-Host "You can install it by running: winget install --id Git.Git -e --source winget" -ForegroundColor Yellow
    Write-Host "Or download it from: https://git-scm.com/download/win" -ForegroundColor Yellow
    Exit
}

# 2. Check Git identity
$userName = git config --global user.name
$userEmail = git config --global user.email

if (-not $userName -or -not $userEmail) {
    Write-Host "[*] Git user identity is not configured." -ForegroundColor Yellow
    $inputName = Read-Host "Enter your GitHub / Git Name"
    $inputEmail = Read-Host "Enter your GitHub / Git Email"
    git config --global user.name "$inputName"
    git config --global user.email "$inputEmail"
}

# 3. Initialize Git if needed
if (-not (Test-Path ".git")) {
    Write-Host "[*] Initializing local git repository..." -ForegroundColor Green
    git init
    git branch -M main
}

# 4. Stage and commit
Write-Host "[*] Staging files..." -ForegroundColor Green
git add .

Write-Host "[*] Creating commit..." -ForegroundColor Green
git commit -m "Complete implementation: Robotic Arm Joint Health Monitoring System"

# 5. Remote and push
$currentRemote = git remote get-url origin 2>$null
if (-not $currentRemote) {
    Write-Host "`n[*] No remote repository configured yet." -ForegroundColor Cyan
    Write-Host "1. Create a new repository on https://github.com/new"
    Write-Host "2. Copy the repository URL (e.g., https://github.com/username/robotic-arm-health-monitor.git)"
    $repoUrl = Read-Host "`nEnter your GitHub repository URL"
    if ($repoUrl) {
        git remote add origin $repoUrl
        Write-Host "[*] Remote added: $repoUrl" -ForegroundColor Green
    }
}

Write-Host "`n[*] Pushing to GitHub (main branch)..." -ForegroundColor Green
git push -u origin main

Write-Host "`n=== Completed successfully! ===" -ForegroundColor Cyan
