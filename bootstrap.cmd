@echo off
cd /d "%~dp0"
py -3 -m pipeline.etl.bootstrap
if errorlevel 1 (
  echo.
  echo Build failed. Check Python installation and project setup.
  pause
)
