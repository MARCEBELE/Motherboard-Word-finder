@echo off
title Board Word Finder - Setup
cd /d "%~dp0"
echo ============================================
echo   Board Word Finder - Setup
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [X] Python was not found.
  echo     Install Python 3.10 or newer from https://www.python.org/downloads/
  echo     IMPORTANT: tick "Add Python to PATH" during install, then run this again.
  echo.
  pause
  exit /b 1
)

echo Creating a private environment in .venv ...
python -m venv .venv
if errorlevel 1 (
  echo [X] Could not create the environment.
  pause
  exit /b 1
)

echo.
echo Installing dependencies. This downloads ~100-200 MB and can take a few minutes...
echo.
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [X] Install failed. Check your internet connection and try again.
  pause
  exit /b 1
)

echo.
echo ============================================
echo   Setup complete!
echo   Now double-click  "Start Word Finder.bat"
echo ============================================
echo.
echo (The first board you process will download the OCR models, ~15 MB.)
pause
