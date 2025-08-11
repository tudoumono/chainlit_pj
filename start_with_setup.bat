@echo off
echo ========================================
echo AI Workspace - Setup and Launch
echo ========================================
echo.

REM Check if chainlit-sqlalchemy is installed
python -c "import chainlit.data.sql_alchemy" 2>nul
if %errorlevel% neq 0 (
    echo Installing required packages...
    pip install chainlit-sqlalchemy[sqlite]
    echo.
)

echo Starting application...
echo.
echo Login credentials:
echo   Username: admin
echo   Password: admin123
echo.
echo ========================================
echo.
chainlit run app.py
pause
