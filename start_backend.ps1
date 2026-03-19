# start_backend.ps1
# Music Agent 后端启动脚本 (Windows PowerShell)
# 用法: powershell -ExecutionPolicy Bypass -File start_backend.ps1

param(
    [int]$Port = 8000,
    [int]$WaitSeconds = 8
)

$ErrorActionPreference = "Continue"
$ProjectRoot = "E:\Workspace\music_agent"

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Music Agent Backend Startup Script" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# 1. 进入项目目录
Write-Host "`n[1/6] Entering project directory: $ProjectRoot" -ForegroundColor Yellow
Set-Location $ProjectRoot
if (-not (Test-Path "scripts\run_api.py")) {
    Write-Host "ERROR: scripts\run_api.py not found!" -ForegroundColor Red
    Write-Host "Make sure you are in the correct project directory." -ForegroundColor Red
    exit 1
}

# 2. 检查 API Key
Write-Host "`n[2/6] Checking API Key..." -ForegroundColor Yellow
$bailianKey = [Environment]::GetEnvironmentVariable("DASHSCOPE_API_KEY_BAILIAN")
$codingKey = [Environment]::GetEnvironmentVariable("DASHSCOPE_API_KEY")

if ($bailianKey) {
    Write-Host "  DASHSCOPE_API_KEY_BAILIAN: Found (prefix: $($bailianKey.Substring(0, [Math]::Min(9, $bailianKey.Length))))" -ForegroundColor Green
} elseif ($codingKey) {
    Write-Host "  DASHSCOPE_API_KEY: Found (prefix: $($codingKey.Substring(0, [Math]::Min(9, $codingKey.Length))))" -ForegroundColor Green
} else {
    Write-Host "  ERROR: No API Key found!" -ForegroundColor Red
    Write-Host "  Please set DASHSCOPE_API_KEY_BAILIAN or DASHSCOPE_API_KEY environment variable." -ForegroundColor Red
    Write-Host "  Example: `$env:DASHSCOPE_API_KEY_BAILIAN = 'sk-xxxxx'" -ForegroundColor Yellow
    exit 1
}

# 3. 设置环境变量
Write-Host "`n[3/6] Setting environment variables..." -ForegroundColor Yellow
$env:MUSIC_AGENT_LLM_MODE = "qwen"
$env:TF_CPP_MIN_LOG_LEVEL = "3"
$env:TRANSFORMERS_NO_TF = "1"
$env:TF_ENABLE_ONEDNN_OPTS = "0"
Write-Host "  MUSIC_AGENT_LLM_MODE = $env:MUSIC_AGENT_LLM_MODE" -ForegroundColor Green
Write-Host "  TF_CPP_MIN_LOG_LEVEL = $env:TF_CPP_MIN_LOG_LEVEL" -ForegroundColor Green
Write-Host "  TRANSFORMERS_NO_TF = $env:TRANSFORMERS_NO_TF" -ForegroundColor Green

# 4. 清理占用端口的旧进程
Write-Host "`n[4/6] Cleaning up port $Port..." -ForegroundColor Yellow
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

# 5. 启动后端
Write-Host "`n[5/6] Starting backend server..." -ForegroundColor Yellow
Write-Host "  Running: python scripts\run_api.py" -ForegroundColor Gray

$processInfo = New-Object System.Diagnostics.ProcessStartInfo
$processInfo.FileName = "python"
$processInfo.Arguments = "scripts\run_api.py"
$processInfo.WorkingDirectory = $ProjectRoot
$processInfo.UseShellExecute = $false
$processInfo.RedirectStandardOutput = $false
$processInfo.RedirectStandardError = $false
$processInfo.CreateNoWindow = $false

# 复制当前环境变量到新进程
$processInfo.EnvironmentVariables["MUSIC_AGENT_LLM_MODE"] = $env:MUSIC_AGENT_LLM_MODE
$processInfo.EnvironmentVariables["TF_CPP_MIN_LOG_LEVEL"] = $env:TF_CPP_MIN_LOG_LEVEL
$processInfo.EnvironmentVariables["TRANSFORMERS_NO_TF"] = $env:TRANSFORMERS_NO_TF
$processInfo.EnvironmentVariables["TF_ENABLE_ONEDNN_OPTS"] = $env:TF_ENABLE_ONEDNN_OPTS
if ($bailianKey) {
    $processInfo.EnvironmentVariables["DASHSCOPE_API_KEY_BAILIAN"] = $bailianKey
}
if ($codingKey) {
    $processInfo.EnvironmentVariables["DASHSCOPE_API_KEY"] = $codingKey
}

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $processInfo
$null = $process.Start()

Write-Host "  Backend process started (PID: $($process.Id))" -ForegroundColor Green

# 6. 健康检查
Write-Host "`n[6/6] Health check (waiting up to $WaitSeconds seconds)..." -ForegroundColor Yellow
$healthUrl = "http://localhost:$Port/health"
$maxAttempts = $WaitSeconds
$success = $false

for ($i = 1; $i -le $maxAttempts; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $success = $true
            break
        }
    } catch {
        Write-Host "  Attempt $i/$maxAttempts - Waiting..." -ForegroundColor DarkGray
    }
}

Write-Host ""
if ($success) {
    Write-Host "=" * 60 -ForegroundColor Green
    Write-Host "BACKEND STARTED SUCCESSFULLY" -ForegroundColor Green
    Write-Host "=" * 60 -ForegroundColor Green
    Write-Host ""
    Write-Host "  Backend URL:     http://localhost:$Port" -ForegroundColor White
    Write-Host "  Health Check:    $healthUrl" -ForegroundColor White
    Write-Host "  LLM Mode:        qwen" -ForegroundColor White
    Write-Host "  Process ID:      $($process.Id)" -ForegroundColor White
    Write-Host ""
    Write-Host "  To stop: Get-Process -Id $($process.Id) | Stop-Process" -ForegroundColor DarkGray
    Write-Host ""
} else {
    Write-Host "=" * 60 -ForegroundColor Red
    Write-Host "BACKEND STARTUP FAILED" -ForegroundColor Red
    Write-Host "=" * 60 -ForegroundColor Red
    Write-Host ""
    Write-Host "  Troubleshooting steps:" -ForegroundColor Yellow
    Write-Host "  1. Check if port $Port is still occupied:" -ForegroundColor White
    Write-Host "     Get-NetTCPConnection -LocalPort $Port" -ForegroundColor Gray
    Write-Host "  2. Check for Python errors in the console window" -ForegroundColor White
    Write-Host "  3. Try running manually:" -ForegroundColor White
    Write-Host "     python scripts\run_api.py" -ForegroundColor Gray
    Write-Host "  4. Verify API Key is set correctly" -ForegroundColor White
    Write-Host ""
}

# 返回进程对象供后续使用
return $process