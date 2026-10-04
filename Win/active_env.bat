@echo off
cd /d "%~dp0"

if not exist myenv (
    echo Error: 'myenv' not found. Run install_env.bat first.
    pause
    exit /b 1
)

if not exist myenv\Scripts\python.exe (
    echo Error: python.exe not found in myenv. Run install_env.bat again.
    pause
    exit /b 1
)

myenv\Scripts\python.exe assistant.py
pause
