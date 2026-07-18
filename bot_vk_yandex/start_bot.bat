@echo off
setlocal EnableExtensions
chcp 65001 >nul

cd /d "%~dp0"

echo ========================================
echo   VK + Yandex RAG Bot startup script
echo ========================================
echo.

where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv is not installed or not in PATH.
    echo Install instructions: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/5] Creating virtual environment...
    uv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/5] Virtual environment already exists.
)

echo [2/5] Installing dependencies...
uv pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [3/5] .env file not found. Creating from .env.example...
    if exist ".env.example" (
        copy /Y ".env.example" ".env" >nul
        echo [INFO] .env created. Fill required keys and run script again.
        echo Required: VK_GROUP_ID, VK_ACCESS_TOKEN, YANDEX_API_KEY, YANDEX_FOLDER_ID
    ) else (
        echo [ERROR] .env and .env.example are missing.
    )
    pause
    exit /b 1
) else (
    echo [3/5] .env file found.
)

echo [4/5] Checking Python availability in venv...
".venv\Scripts\python.exe" -V >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python in virtual environment is unavailable.
    pause
    exit /b 1
)

echo [5/5] Starting bot...
echo.
".venv\Scripts\python.exe" "bot.py"

echo.
echo Bot process finished.
pause
