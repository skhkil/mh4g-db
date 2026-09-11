@echo off
setlocal
cd /d "%~dp0.."

echo ==============================================
echo   MH4G Database Collector / Converter
echo ==============================================

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found.
  pause
  exit /b 1
)

echo [1/5] Installing Python packages...
python -m pip install -r tools\requirements.txt
if errorlevel 1 goto :fail

echo.
echo [2/5] Crawling flashkiller MH4G pages...
python tools\crawl_source.py
if errorlevel 1 goto :fail

echo.
echo [3/5] Extracting HTML tables...
python tools\extract_tables.py
if errorlevel 1 goto :fail

echo.
echo [4/5] Normalizing, validating and publishing JSON...
python tools\build_database.py --publish
if errorlevel 1 goto :fail

echo.
echo [5/5] Creating analysis ZIP...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$files=@('tools\raw_tables.json','tools\crawl_manifest.json','tools\generated\report.json'); if(Test-Path 'MH4G_DB_analysis.zip'){Remove-Item 'MH4G_DB_analysis.zip' -Force}; Compress-Archive -Path $files -DestinationPath 'MH4G_DB_analysis.zip' -Force"
if errorlevel 1 goto :fail

echo.
echo DONE: MH4G_DB_analysis.zip
echo The site data/ folder has also been updated.
pause
exit /b 0

:fail
echo.
echo [FAILED] Check the error message above.
pause
exit /b 1
