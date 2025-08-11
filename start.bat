@echo off
echo =========================================
echo AI Workspace - Starting with InMemory Data Layer
echo =========================================
echo.
echo Data Layer: InMemory (SimpleDataLayer)
echo History: Will be displayed in UI
echo Note: History will be lost on restart
echo.
echo Login Credentials:
echo   Username: admin
echo   Password: admin123
echo.
echo =========================================
echo.
echo Starting application...
echo.

chainlit run app.py

pause
