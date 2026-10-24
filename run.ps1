# Script khởi động toàn bộ Local AI Agent Workspace
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  🚀 KHỞI ĐỘNG LOCAL AI AGENT WORKSPACE (ANTIGRAVITY)" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $rootDir

# 1. Check & start Ollama
Write-Host "[1/3] Kiểm tra dịch vụ Ollama (Port 11434)..." -ForegroundColor Yellow
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "      Ollama đang hoạt động sẵn sàng!" -ForegroundColor Green
} catch {
    Write-Host "      Khởi động Ollama daemon..." -ForegroundColor Yellow
    Start-Process -FilePath "C:\Users\AMIN\AppData\Local\Programs\Ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Minimized
    Start-Sleep -Seconds 3
}

# 2. Start Backend FastAPI
Write-Host "[2/3] Khởi động Backend FastAPI (Port 8765)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$rootDir'; & '.\.venv\Scripts\python.exe' -m uvicorn backend.main:app --host 127.0.0.1 --port 8765"

Start-Sleep -Seconds 2

# 3. Start Frontend Vite
Write-Host "[3/3] Khởi động Frontend Vite (Port 5173)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$rootDir\frontend'; npm run dev"

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  ✅ HOÀN TẤT! Đang mở trình duyệt tại: http://localhost:5173/" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Cyan
Start-Process "http://localhost:5173/"
