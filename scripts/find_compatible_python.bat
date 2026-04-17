@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "PYTHON_CMD="
set "PYTHON_VERSION="

for %%V in (3.13 3.12 3.11 3.10) do (
    py -%%V -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py -%%V"
        for /f "usebackq delims=" %%I in (`py -%%V -c "import sys; print('.'.join(str(v) for v in sys.version_info[:3]))"`) do set "PYTHON_VERSION=%%I"
        goto :done
    )
)

for %%P in (python python3) do (
    %%P -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=%%P"
        for /f "usebackq delims=" %%I in (`%%P -c "import sys; print('.'.join(str(v) for v in sys.version_info[:3]))"`) do set "PYTHON_VERSION=%%I"
        goto :done
    )
)

:done
endlocal & set "PYTHON_CMD=%PYTHON_CMD%" & set "PYTHON_VERSION=%PYTHON_VERSION%"
if not defined PYTHON_CMD exit /b 1
exit /b 0
