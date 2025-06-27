@echo off
title 夏空音樂機器人
color 0b
echo ======================================
echo          夏空音樂機器人啟動器
echo ======================================
echo.

REM 檢查 Python 是否安裝
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python！請先安裝 Python
    echo.
    pause
    exit /b 1
)

REM 檢查主程式是否存在
if not exist "ciaccona_bot.py" (
    echo [錯誤] 找不到 ciaccona_bot.py 檔案！
    echo 請確認檔案在正確位置
    echo.
    pause
    exit /b 1
)

REM 檢查是否需要安裝套件
echo [檢查] 正在檢查必要套件...
python -c "import discord" >nul 2>&1
if %errorlevel% neq 0 (
    echo [安裝] 正在安裝 discord.py...
    pip install discord.py
    echo.
)

python -c "import nacl" >nul 2>&1
if %errorlevel% neq 0 (
    echo [安裝] 正在安裝 PyNaCl (語音功能需要)...
    pip install PyNaCl
    echo.
)

python -c "import dotenv" >nul 2>&1
if %errorlevel% neq 0 (
    echo [安裝] 正在安裝 python-dotenv...
    pip install python-dotenv
    echo.
)


REM 啟動機器人
echo [啟動] 正在啟動夏空機器人...
echo.
python ciaccona_bot.py

REM 如果程式結束，顯示訊息並等待
echo.
echo ======================================
echo        夏空機器人已停止運行
echo ======================================
echo.
echo 按任意鍵關閉視窗...
pause >nul