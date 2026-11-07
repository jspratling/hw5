@echo off
title Campus Customs front desk (port 5173)
cd /d "%~dp0frontend"
if not exist node_modules (
  echo Installing the dashboard packages the first time...
  call npm install
)
echo Starting the front desk at http://localhost:5173 ...
call npm run dev
pause
