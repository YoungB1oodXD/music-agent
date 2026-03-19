# start_all.ps1
# Music Agent 完整启动脚本 (Windows PowerShell)
# 用法: powershell -ExecutionPolicy Bypass -File start_all.ps1

param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [int]$BackendWaitSeconds = 10
)

$ErrorActionPreference = "Continue"
$ProjectRoot = "E:\Workspace\music_agent"

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Magenta
Write-Host "   Music Agent - Complete Startup Script" -ForegroundColor Magenta
Write-Host "=" * 60 -ForegroundColor Magenta
Write-Host ""

# ============================================================================
# PHASE 1: Environment Check
# ============================================================================
Write-Host "[PHASE 1] Environment Check" -ForegroundColor Cyan
Write-Host "-" * 40 -ForegroundColor DarkGray

Set-Location $ProjectRoot

# Check API Key
$bailianKey = [Environment]::GetEnvironmentVariable("DASHSCOPE_API_KEY_BAILIAN")
$codingKey = [Environment]::GetEnvironmentVariable("DASHSCOPE_API_KEY")

if ($bailianKey) {
    Write-Host "  API Key: DASHSCOPE_API_KEY_BAILIAN (OK)" -ForegroundColor Green
} elseif ($codingKey) {
    Write-Host "  API Key: DASHSCOPE_API_KEY (OK)" -ForegroundColor Green
} else {
    Write-Host "  ERROR: No API Key found!" -ForegroundColor Red
    Write-Host "  Please set DASHSCOPE_API_KEY_BAILIAN environment variable." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Python
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Python: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Python not found!" -ForegroundColor Red
    exit 1
}

# Check Node.js
$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Node.js: $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Node.js not found!" -ForegroundColor Red
    exit 1
}

# ============================================================================
# PHASE 2: Clean Up Old Processes
# ============================================================================
Write-Host ""
Write-Host "[PHASE 2] Cleaning Up Old Processes" -ForegroundColor Cyan
Write-Host "-" * 40 -ForegroundColor DarkGray

foreach ($port in @($BackendPort, $FrontendPort)) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connections) {
        foreach ($conn in $connections) {
            if ($conn.OwningProcess -and $conn.OwningProcess -gt 0) {
                $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
                if ($proc) {
                    Write-Host "  Stopping: $($proc.ProcessName) (PID: $($proc.Id)) on port $port" -ForegroundColor Yellow
                    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                }
            }
        }
    }
}
Start-Sleep -Seconds 2
Write-Host "  Ports cleared." -ForegroundColor Green

# ============================================================================
# PHASE 3: Start Backend
# ============================================================================
Write-Host ""
Write-Host "[PHASE 3] Starting Backend" -ForegroundColor Cyan
Write-Host "-" * 40 -ForegroundColor DarkGray

# Set environment variables
$env:MUSIC_AGENT_LLM_MODE = "qwen"
$env:TF_CPP_MIN_LOG_LEVEL = "3"
$env:TRANSFORMERS_NO_TF = "1"
$env:TF_ENABLE_ONEDNN_OPTS = "0"

Write-Host "  Environment variables set:" -ForegroundColor Gray
Write-Host "    MUSIC_AGENT_LLM_MODE = qwen" -ForegroundColor DarkGray
Write-Host "    TF_CPP_MIN_LOG_LEVEL = 3" -ForegroundColor DarkGray
Write-Host "    TRANSFORMERS_NO_TF = 1" -ForegroundColor DarkGray

# Start backend process
$backendProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
$backendProcessInfo.FileName = "python"
$backendProcessInfo.Arguments = "scripts\run_api.py"
$backendProcessInfo.WorkingDirectory = $ProjectRoot
$backendProcessInfo.UseShellExecute = $false
$backendProcessInfo.CreateNoWindow = $false

# Copy environment variables
$backendProcessInfo.EnvironmentVariables["MUSIC_AGENT_LLM_MODE"] = $env:MUSIC_AGENT_LLM_MODE
$backendProcessInfo.EnvironmentVariables["TF_CPP_MIN_LOG_LEVEL"] = $env:TF_CPP_MIN_LOG_LEVEL
$backendProcessInfo.EnvironmentVariables["TRANSFORMERS_NO_TF"] = $env:TRANSFORMERS_NO_TF
$backendProcessInfo.EnvironmentVariables["TF_ENABLE_ONEDNN_OPTS"] = $env:TF_ENABLE_ONEDNN_OPTS
if ($bailianKey) { $backendProcessInfo.EnvironmentVariables["DASHSCOPE_API_KEY_BAILIAN"] = $bailianKey }
if ($codingKey) { $backendProcessInfo.EnvironmentVariables["DASHSCOPE_API_KEY"] = $codingKey }

$backendProcess = New-Object System.Diagnostics.Process
$backendProcess.StartInfo = $backendProcessInfo
$null = $backendProcess.Start()

Write-Host "  Backend process started (PID: $($backendProcess.Id))" -ForegroundColor Gray

# Health check
Write-Host "  Waiting for backend to be ready..." -ForegroundColor Gray
$healthUrl = "http://localhost:$BackendPort/health"
$backendReady = $false

for ($i = 1; $i -le $BackendWaitSeconds; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
            break
        }
    } catch {
        Write-Host "." -NoNewline -ForegroundColor DarkGray
    }
}
Write-Host ""

if (-not $backendReady) {
    Write-Host "  ERROR: Backend failed to start!" -ForegroundColor Red
    Write-Host "  Check the Python console for errors." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "  Backend is ready!" -ForegroundColor Green

# ============================================================================
# PHASE 4: Start Frontend
# ============================================================================
Write-Host ""
Write-Host "[PHASE 4] Starting Frontend" -ForegroundColor Cyan
Write-Host "-" * 40 -ForegroundColor DarkGray

$frontendDir = Join-Path $ProjectRoot "frontend"
Set-Location $frontendDir

$frontendProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
$frontendProcessInfo.FileName = "cmd.exe"
$frontendProcessInfo.Arguments = "/c npm run dev"
$frontendProcessInfo.WorkingDirectory = $frontendDir
$frontendProcessInfo.UseShellExecute = $false
$frontendProcessInfo.CreateNoWindow = $false

$frontendProcess = New-Object System.Diagnostics.Process
$frontendProcess.StartInfo = $frontendProcessInfo
$null = $frontendProcess.Start()

Write-Host "  Frontend process started (PID: $($frontendProcess.Id))" -ForegroundColor Gray
Start-Sleep -Seconds 3

# ============================================================================
# PHASE 5: Final Status
# ============================================================================
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Green
Write-Host "   ALL SERVICES STARTED SUCCESSFULLY" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green
Write-Host ""
Write-Host "  Backend:" -ForegroundColor White
Write-Host "    URL:      http://localhost:$BackendPort" -ForegroundColor Cyan
Write-Host "    Health:   http://localhost:$BackendPort/health" -ForegroundColor Cyan
Write-Host "    LLM Mode: qwen" -ForegroundColor White
Write-Host ""
Write-Host "  Frontend:" -ForegroundColor White
Write-Host "    URL:      http://localhost:$FrontendPort" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Process IDs:" -ForegroundColor White
Write-Host "    Backend:  $($backendProcess.Id)" -ForegroundColor Gray
Write-Host "    Frontend: $($frontendProcess.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "-" * 60 -ForegroundColor DarkGray
Write-Host "  Manual Verification Steps:" -ForegroundColor Yellow
Write-Host "  1. Open http://localhost:$FrontendPort in your browser" -ForegroundColor White
Write-Host "  2. Type '推荐适合学习的歌' and press Enter" -ForegroundColor White
Write-Host "  3. Check if recommendations appear in the right panel" -ForegroundColor White
Write-Host "  4. Test like/dislike/refresh buttons" -ForegroundColor White
Write-Host ""
Write-Host "  To stop all services:" -ForegroundColor Yellow
Write-Host "    Get-Process -Id $($backendProcess.Id) | Stop-Process" -ForegroundColor Gray
Write-Host "    Get-Process -Id $($frontendProcess.Id) | Stop-Process" -ForegroundColor Gray
Write-Host ""

# Return process objects
return @{
    Backend = $backendProcess
    Frontend = $frontendProcess
}