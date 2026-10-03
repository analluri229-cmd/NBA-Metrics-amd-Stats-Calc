@echo off
cd /d "%~dp0"
py -3 -m scripts.etl.bootstrap
if errorlevel 1 (
  echo.
  echo Build failed. Check Python installation and project setup.
  pause
)
