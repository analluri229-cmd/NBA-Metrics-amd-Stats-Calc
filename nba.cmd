@echo off
cd /d "%~dp0"
py -3 -m pipeline
if errorlevel 1 pause
