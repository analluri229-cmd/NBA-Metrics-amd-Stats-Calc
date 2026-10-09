@echo off
rem Opens the NBA data menu. Uses the project venv Python (it has the download libraries), else py -3.
cd /d "%~dp0"
set "PY="
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if not defined PY if exist "%USERPROFILE%\.venv\Scripts\python.exe" set "PY=%USERPROFILE%\.venv\Scripts\python.exe"
if defined PY ("%PY%" -m pipeline) else (py -3 -m pipeline)
if errorlevel 1 pause
