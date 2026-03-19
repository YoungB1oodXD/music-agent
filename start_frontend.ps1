# start_frontend.ps1
# Music Agent 前端启动脚本 (Windows PowerShell)
# 用法: powershell -ExecutionPolicy Bypass -File start_frontend.ps1

param(
    [int]$Port = 3000,
    [string]$BackendUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Continue"
$ProjectRoot = "E:\Workspace\music_agent"
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Music Agent Frontend Startup Script" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# 1. 检查前端目录
Write-Host "`n[1/5] Checking frontend directory..." -ForegroundColor Yellow
if (-not (Test-Path $FrontendDir)) {
    Write-Host "ERROR: Frontend directory not found: $FrontendDir" -ForegroundColor Red
    exit 1
}
Set-Location $FrontendDir
Write-Host "  Frontend directory: $FrontendDir" -ForegroundColor Green

# 2. 检查后端是否运行
Write-Host "`n[2/5] Checking backend connection..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-WebRequest -Uri "$BackendUrl/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  Backend is running: $BackendUrl" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: Backend not responding at $BackendUrl" -ForegroundColor Yellow
    Write-Host "  Frontend may not work correctly without the backend." -ForegroundColor Yellow
    Write-Host "  Please run start_backend.ps1 first." -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue starting frontend anyway? (y/n)"
    if ($continue -ne "y") {
        Write-Host "Aborted." -ForegroundColor Red
        exit 0
    }
}

# 3. 检查 node_modules
Write-Host "`n[3/5] Checking dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "node_modules")) {
    Write-Host "  node_modules not found. Running npm install..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: npm install failed!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  Dependencies installed." -ForegroundColor Green
}

# 4. 清理占用端口的旧进程
Write-Host "`n[4/5] Cleaning up port $Port..." -ForegroundColor Yellow
$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($connections) {
    foreach ($conn in $connections) {
        if ($conn.OwningProcess -and $conn.OwningProcess -gt 0) {
            $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "  Killing process: $($proc.ProcessName) (PID: $($proc.Id))" -ForegroundColor Yellow
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
    Start-Sleep -Seconds 2
    Write-Host "  Port $Port cleared." -ForegroundColor Green
} else {
    Write-Host "  Port $Port is available." -ForegroundColor Green
}

# 5. 启动前端
Write-Host "`n[5/5] Starting frontend development server..." -ForegroundColor Yellow

$processInfo = New-Object System.Diagnostics.ProcessStartInfo
$processInfo.FileName = "cmd.exe"
$processInfo.Arguments = "/c npm run dev"
$processInfo.WorkingDirectory = $FrontendDir
$processInfo.UseShellExecute = $false
$processInfo.CreateNoWindow = $false

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $processInfo
$null = $process.Start()

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Green
Write-Host "FRONTEND STARTED" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend URL:    http://localhost:$Port" -ForegroundColor White
Write-Host "  Backend URL:     $BackendUrl" -ForegroundColor White
Write-Host "  Process ID:      $($process.Id)" -ForegroundColor White
Write-Host ""
Write-Host "  Open in browser: http://localhost:$Port" -ForegroundColor Cyan
Write-Host ""

return $process