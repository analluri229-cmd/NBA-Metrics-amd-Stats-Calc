@echo off
cd /d "%~dp0"
py -3 -m pipeline.etl.run_demo_pipeline
if errorlevel 1 (
  echo.
  echo Pipeline failed. Check the workspace setup and Python environment.
  pause
)
