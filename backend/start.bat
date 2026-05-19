@echo off
chcp 65001 >nul
echo [zhitu] 智途校园服务启动中...
cd /d "%~dp0"
start /b venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
timeout /t 3 /nobreak >nul
echo [zhitu] Backend running at http://localhost:8000/api
echo [zhitu] Swagger docs: http://localhost:8000/docs
echo [zhitu] Press Ctrl+C to stop
pause