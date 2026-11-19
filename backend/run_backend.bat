@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python -m uvicorn app_full:app --reload
pause
