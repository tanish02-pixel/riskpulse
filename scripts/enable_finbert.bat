@echo off
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (
  echo Run start.bat once to create the environment, then stop the server.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install transformers==5.19.0
if errorlevel 1 goto fail
.venv\Scripts\python.exe scripts\setup_model.py
if errorlevel 1 goto fail
echo FinBERT ready. Restart start.bat.
pause
exit /b 0
:fail
echo Model setup failed. See README troubleshooting.
pause
exit /b 1

