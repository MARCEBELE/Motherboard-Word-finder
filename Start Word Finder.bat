@echo off
title Board Word Finder
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
echo ============================================
echo   Board Word Finder
echo   Keep this window OPEN while using the tool.
echo   Close it to stop.
echo ============================================
echo.
echo Opening in your browser...
start "" cmd /c "timeout /t 2 >nul & start "" http://localhost:8731/viewer.html"
"%PY%" server.py
echo.
echo Server stopped. Press any key to close.
pause >nul
