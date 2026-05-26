@echo off
title UniGuide Local Server
color 0B
E:
cd "E:\Stem trường"

echo ===================================================
echo   🎓 UNIGUIDE - AI CAREER COUNSELING SYSTEM 🎓
echo ===================================================
echo.
echo [*] Dang kich hoat moi truong ao Python (venv)...
call venv\Scripts\activate.bat

echo [*] Dang mo trinh duyet nghiem thu giao dien...
start http://localhost:5000

echo [*] Dang khoi dong may chu Flask Backend (Local Port 5000)...
echo.
python app.py

pause