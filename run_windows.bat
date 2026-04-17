@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo The virtual environment does not exist yet.
    echo Please run install_windows.bat first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" launch.py
set "APP_EXIT=%ERRORLEVEL%"
if not "%APP_EXIT%"=="0" (
    echo.
    echo The application exited with code %APP_EXIT%.
    if exist "startup_error.log" (
        echo A startup log was written to startup_error.log
    )
    pause
)
endlocal & exit /b %APP_EXIT%
