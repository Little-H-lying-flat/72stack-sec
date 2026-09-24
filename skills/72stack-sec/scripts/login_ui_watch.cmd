@echo off
REM 期2：通知 + Playwright 自动抓 cookie（你只需在弹出窗口登录）
set ROOT=%~1
if "%ROOT%"=="" set ROOT=D:\SRC挖洞\字节跳动_V3_SRC挖洞
cd /d "%~dp0"
echo === login_ui --watch --auto-cookie ===
echo 请在弹出的 Chromium 里登录；成功后自动写 session.cookie 并 confirm-ready
python login_ui.py --task-root "%ROOT%" --watch --force-notify --auto-cookie
echo exit=%ERRORLEVEL%
pause
