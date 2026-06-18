@echo off
chcp 65001 >nul
title 调试 Chrome 启动器（政采云 CDP）

echo.
echo ========================================
echo   即将关闭所有 Chrome 并启动调试版
echo   (调试端口 9222 / 独立 profile)
echo ========================================
echo.

echo 关闭现有 Chrome...
taskkill /F /IM chrome.exe >nul 2>&1

echo 等待 2 秒...
timeout /t 2 /nobreak >nul

echo 启动调试 Chrome 并打开政采云...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=C:/chrome-debug --no-first-run --no-default-browser-check "https://b.zhengcaiyun.cn/luban/search?k=&type=1"

echo 等待 Chrome 起来 (5秒)...
timeout /t 5 /nobreak >nul

echo.
echo 检查端口 9222...
netstat -ano | findstr ":9222" | findstr "LISTENING"
if %errorlevel%==0 (
    echo.
    echo [OK] 调试 Chrome 已就绪，政采云页面已自动打开
    echo.
    echo 下一步：
    echo   1. 如有滑块验证码，手动通过
    echo   2. 回到系统点"抓取招标信息"
) else (
    echo.
    echo [失败] 端口 9222 未监听，请截图反馈
)

echo.
pause
