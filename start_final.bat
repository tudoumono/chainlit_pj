@echo off
echo =========================================
echo AI Workspace - Installing Dependencies
echo =========================================

REM Install required packages
echo Installing SQLAlchemy dependencies...
pip install sqlalchemy aiosqlite asyncpg

echo.
echo =========================================
echo Starting Application
echo =========================================
echo.
echo Login credentials:
echo   Username: admin
echo   Password: admin123
echo.
echo Data Layer: Built-in SQLAlchemy
echo.
echo If history doesn't appear:
echo   1. Run /debug command
echo   2. Clear browser cache (Ctrl+F5)
echo   3. Try incognito mode
echo.
echo =========================================
echo.

chainlit run app.py
pause
