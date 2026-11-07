@echo off
title Campus Customs backend (port 8000)
cd /d "%~dp0backend"
echo Starting the Campus Customs backend at http://localhost:8000 ...
python -m uvicorn main:app --reload --port 8000
pause
