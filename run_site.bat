@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found.
  pause
  exit /b 1
)
echo Starting MH4G Simulator v0.7.5...
python run_site.py
