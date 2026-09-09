@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Primero instala el entorno siguiendo README.md.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "main.py"
