@echo off
chcp 65001 >nul
title Khởi Động Local AI Agent Workspace
echo =======================================================
echo   🚀 KHỞI ĐỘNG LOCAL AI AGENT WORKSPACE (ANTIGRAVITY)
echo =======================================================
echo.

cd /d "%~dp0"

echo [1/3] Đang kiểm tra dịch vụ mô hình Ollama...
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       Ollama chưa chạy, đang khởi động Ollama daemon...
    start "Ollama Engine" /min "C:\Users\AMIN\AppData\Local\Programs\Ollama\ollama.exe" serve
    timeout /t 3 /nobreak >nul
) else (
    echo       Ollama đang hoạt động sẵn sàng!
)

echo [2/3] Đang khởi động Backend FastAPI (Port 8765)...
start "Backend - FastAPI" cmd /k "cd /d "%~dp0" && .\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8765"
timeout /t 2 /nobreak >nul

echo [3/3] Đang khởi động Frontend UI (Port 5173)...
start "Frontend - Vite React" cmd /k "cd /d "%~dp0frontend" && npm run dev"
timeout /t 2 /nobreak >nul

echo.
echo =======================================================
echo   ✅ HOÀN TẤT! Đang mở ứng dụng trên trình duyệt...
echo   👉 Địa chỉ: http://localhost:5173/
echo =======================================================
start http://localhost:5173/
