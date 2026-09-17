@echo off
chcp 65001 >nul
echo [zhitu] 智途校园服务停止中...

set "PORT=8000"
set "FOUND="

rem 仅停止监听 8000 端口的 uvicorn 进程，避免误杀本机其它 python 进程。
rem netstat 输出中：LISTENING 行形如
rem   TCP  0.0.0.0:8000  0.0.0.0:0  LISTENING  12345
rem 第 5 列即为进程 PID；用 ":8000 " 精确匹配端口，避免匹配到 18000 等。
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    set "FOUND=1"
    echo [zhitu] 停止 PID %%p（端口 %PORT%）...
    taskkill /f /pid %%p >nul 2>nul
)

if not defined FOUND (
    echo [zhitu] 未发现运行中的服务（端口 %PORT% 无监听进程）。
) else (
    echo [zhitu] Stopped.
)
