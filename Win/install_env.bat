@echo off
cd /d "%~dp0"

echo === [1/3] Checking virtual environment...
if not exist myenv (
    echo Creating virtual environment 'myenv'...
    python -m venv myenv
) else (
    echo Environment 'myenv' already exists.
)

echo.
echo === [2/3] Upgrading pip...
myenv\Scripts\python.exe -m pip install --upgrade pip

echo.
echo === [3/3] Installing dependencies (EasyOCR, Gemini, Pynput, Win11Toast)...
echo This may take 1-3 minutes:
myenv\Scripts\pip.exe install easyocr google-genai pynput pillow win11toast

echo.
echo === [OK] Windows setup completed successfully!
pause

