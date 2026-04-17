@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

call scripts\find_compatible_python.bat
if errorlevel 1 (
    echo No compatible Python runtime was found.
    echo Supported and tested range for this project: Python 3.10 to 3.13 x64.
    echo.
    echo Install any normal Python version in that range and retry.
    echo Tip: "py -0p" shows Python installations detected by the Windows launcher.
    pause
    exit /b 1
)

echo Using Python runtime: %PYTHON_CMD%  [%PYTHON_VERSION%]

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    call %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo Failed to create the virtual environment.
        pause
        exit /b 1
    )
)

if not exist ".venv\Scripts\activate.bat" (
    echo The virtual environment exists but is incomplete.
    echo Delete .venv and run this installer again.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip wheel
if errorlevel 1 (
    echo Failed to update pip/wheel.
    pause
    exit /b 1
)
python -m pip install -c constraints.txt "setuptools<82"
if errorlevel 1 (
    echo Failed to install a setuptools version compatible with PyTorch.
    pause
    exit /b 1
)

echo.
echo Choose PyTorch backend:
echo   [1] CUDA 12.6
echo   [2] CPU only
choice /C 12 /N /T 20 /D 1 /M "Selection (default after 20s: 1): "
set TORCHMODE=%ERRORLEVEL%

if "%TORCHMODE%"=="1" (
    python -m pip install -c constraints.txt torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
) else (
    python -m pip install -c constraints.txt torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
)
if errorlevel 1 (
    echo PyTorch installation failed.
    pause
    exit /b 1
)

python -c "import torch; print('PyTorch import OK:', torch.__version__)"
if errorlevel 1 (
    echo Warning: PyTorch was installed but could not be initialized.
    echo On Windows this is often caused by a missing Microsoft Visual C++ Redistributable or a backend/runtime mismatch.
    echo The app will still be installed, but captioning and training may not work until that is fixed.
    echo.
)

python -m pip install -c constraints.txt -r requirements.txt
if errorlevel 1 (
    echo Base dependency installation failed.
    pause
    exit /b 1
)

echo.
echo Installing optional Hugging Face Xet download accelerator...
python -m pip install -c constraints.txt hf_xet
if errorlevel 1 (
    echo Warning: hf_xet could not be installed. Setup will continue with regular HTTP downloads.
) else (
    echo hf_xet installed successfully. Faster Xet-backed downloads should now be available.
)

echo Re-checking setuptools compatibility...
python -m pip install -c constraints.txt "setuptools<82"

echo.
set "HF_TOKEN="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\prompt_hf_token.ps1" -TimeoutSeconds 20`) do set "HF_TOKEN=%%I"

set "BASE_MODEL=stabilityai/stable-diffusion-xl-base-1.0"
set "BLIP_MODEL=Salesforce/blip-image-captioning-base"
set "BASE_MODEL_VARIANT=fp16"

echo Downloading only the files required for the local PyTorch training workflow...
set "HF_XET_HIGH_PERFORMANCE=1"
python scripts\bootstrap_offline_assets.py --base-dir "%cd%" --base-model "%BASE_MODEL%" --blip-model "%BLIP_MODEL%" --base-model-variant "%BASE_MODEL_VARIANT%" --hf-token "%HF_TOKEN%"
if errorlevel 1 (
    echo Bootstrap failed.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\create_shortcuts.ps1" -ProjectDir "%cd%" -ShortcutName "SDXL Easy Trainer Offline"

echo.
echo Setup finished successfully.
echo Shortcuts were created when Windows allowed it.
echo The app can now be used offline with local files only.
echo.
echo The GUI can start automatically now. Press N within 15 seconds to cancel.
choice /C YN /N /T 15 /D Y /M "Start GUI now? "
if errorlevel 2 goto :done
start "" wscript.exe "%cd%\run_gui.vbs"

:done
endlocal
