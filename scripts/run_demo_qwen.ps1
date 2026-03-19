# Music Agent - Qwen Real Mode Demo Launcher
# Usage: .\scripts\run_demo_qwen.ps1

$ErrorActionPreference = "Stop"

# Set Location to Repo Root
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "--- Music Agent Demo Launcher (Qwen Mode) ---" -ForegroundColor Cyan
Write-Host "Working Directory: $PWD"

# 0. Ensure tmp directory exists
$tmpDir = Join-Path $repoRoot ".sisyphus/tmp"
if (-not (Test-Path $tmpDir)) {
    New-Item -ItemType Directory -Path $tmpDir | Out-Null
    Write-Host "[OK] Created $tmpDir" -ForegroundColor Green
}

# 1. Artifact Check
$artifacts = @(
    "index/chroma_bge_m3/",
    "data/models/implicit_model.pkl",
    "data/models/cf_mappings.pkl",
    "dataset/processed/metadata.json"
)

$missing = @()
foreach ($art in $artifacts) {
    if (-not (Test-Path $art)) {
        $missing += $art
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Error: Missing required artifacts:" -ForegroundColor Red
    foreach ($m in $missing) {
        Write-Host "  - $m" -ForegroundColor Red
    }
    Write-Host "Please ensure models and indices are built before running the demo."
    exit 1
}
Write-Host "[OK] All required artifacts found." -ForegroundColor Green

# 2. Port Check
$ports = @(8000, 5173)
$occupied = $false
foreach ($port in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connection) {
        $pid = $connection[0].OwningProcess
        Write-Host "Error: Port $port is already occupied by PID $pid." -ForegroundColor Red
        $occupied = $true
    }
}
if ($occupied) {
    Write-Host "Please stop the processes above and try again."
    exit 1
}
Write-Host "[OK] Ports 8000 and 5173 are available." -ForegroundColor Green

# 3. API Key Check
$apiKey = $env:DASHSCOPE_API_KEY_BAILIAN
if (-not $apiKey) {
    $apiKey = $env:DASHSCOPE_API_KEY
}

if (-not $apiKey) {
    Write-Host "Error: DASHSCOPE_API_KEY or DASHSCOPE_API_KEY_BAILIAN not found." -ForegroundColor Red
    Write-Host "Please set your API key first:"
    Write-Host '  $env:DASHSCOPE_API_KEY = "your_key_here"'
    exit 1
}
Write-Host "[OK] DashScope API Key found." -ForegroundColor Green

# 4. Start Backend
Write-Host "Starting Backend (Qwen Mode)..." -ForegroundColor Yellow
$env:MUSIC_AGENT_LLM_MODE = "qwen"
$backendOut = ".sisyphus/tmp/demo-api-qwen.out.log"
$backendErr = ".sisyphus/tmp/demo-api-qwen.err.log"

$backendProcess = Start-Process python -ArgumentList "scripts/run_api.py" -NoNewWindow -PassThru -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr

# 5. Start Frontend
Write-Host "Starting Frontend..." -ForegroundColor Yellow
$frontendOut = ".sisyphus/tmp/demo-frontend.out.log"
$frontendErr = ".sisyphus/tmp/demo-frontend.err.log"

# Use cmd /c to run npm as it's often a .cmd on Windows
$frontendProcess = Start-Process cmd -ArgumentList "/c npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173" -NoNewWindow -PassThru -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr

# 6. Wait for Backend & Warmup
Write-Host "Waiting for backend to be ready (this may take 2-5 minutes for cold start)..." -ForegroundColor Yellow
$maxRetries = 150 # 150 * 2s = 300s = 5 minutes
$retryCount = 0
$ready = $false

while ($retryCount -lt $maxRetries) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 2
        if ($health.status -eq "ok" -and $health.llm_mode -eq "qwen") {
            $ready = $true
            break
        }
    } catch {
        # Wait and retry
    }
    $retryCount++
    if ($retryCount % 5 -eq 0) {
        Write-Host "[$($retryCount * 2)s elapsed] Waiting..." -ForegroundColor Gray
    }
    Start-Sleep -Seconds 2
}

if (-not $ready) {
    Write-Host "`nError: Backend failed to start or is not in Qwen mode within 5 minutes." -ForegroundColor Red
    Write-Host "Check logs: $backendErr"
    Stop-Process -Id $backendProcess.Id -Force
    Stop-Process -Id $frontendProcess.Id -Force
    exit 1
}

Write-Host "`n[OK] Backend is ready." -ForegroundColor Green

# Warmup Chat
Write-Host "Performing realistic warmup /chat call (this may take 1-3 minutes)..." -ForegroundColor Yellow
$startTime = Get-Date
try {
    $warmupBody = @{
        message = "我想听适合学习的轻音乐"
    } | ConvertTo-Json
    # Allow 300s timeout for the first real LLM + Embedding call
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/chat" -Method Post -Body $warmupBody -ContentType "application/json" -TimeoutSec 300
    $endTime = Get-Date
    $elapsed = ($endTime - $startTime).TotalSeconds
    Write-Host "[OK] Warmup completed in $($elapsed) seconds." -ForegroundColor Green
} catch {
    Write-Host "Warning: Warmup chat failed or timed out. Qwen might be slow or network is unstable." -ForegroundColor Yellow
    Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Gray
}

# 7. Summary
Write-Host "`n--- Demo Environment Ready ---" -ForegroundColor Cyan
Write-Host "Frontend URL: http://127.0.0.1:5173" -ForegroundColor Green
Write-Host "Backend Health: http://127.0.0.1:8000/health" -ForegroundColor Green
Write-Host "`nLogs:"
Write-Host "  Backend:  $backendOut"
Write-Host "  Frontend: $frontendOut"
Write-Host "`nTo stop the demo, run:"
Write-Host "  Stop-Process -Id $($backendProcess.Id), $($frontendProcess.Id) -Force" -ForegroundColor Yellow
Write-Host "  (Backend PID: $($backendProcess.Id), Frontend PID: $($frontendProcess.Id))"
Write-Host "------------------------------"
