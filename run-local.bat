@echo off
setlocal
title Document Q^&A API - local demo
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed. Get Python 3.12 from https://www.python.org/downloads/
  echo During setup, tick "Add python.exe to PATH". Then double-click this file again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating a virtual environment...
  python -m venv .venv || goto fail
)

echo [2/3] Installing dependencies (first run takes a minute)...
rem The PostgreSQL driver is only needed in production; locally the API uses SQLite.
findstr /v /i "psycopg2" requirements.txt > "%TEMP%\docqa-requirements-local.txt"
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r "%TEMP%\docqa-requirements-local.txt" || goto fail

echo [3/3] Starting the API in a new window...
start "Document Q&A API server" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"

echo Waiting for the server, then running the guided demo...
".venv\Scripts\python.exe" scripts\demo.py http://127.0.0.1:8000 || goto fail

start "" http://127.0.0.1:8000/
echo.
echo The web app is open in your browser (API docs: http://127.0.0.1:8000/docs).
echo Close the "Document Q&A API server" window to stop the API.
pause
exit /b 0

:fail
echo.
echo Something failed. Send a screenshot of this window to Claude.
pause
exit /b 1
