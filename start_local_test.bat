@echo off
setlocal EnableExtensions

if /I not "%~1"=="_shell" (
    start "Anchor Schedule Web Local Test" cmd /k call "%~f0" _shell
    exit /b
)

cd /d "%~dp0"
title Anchor Schedule Web Local Test

set "ROOT_PY=%~dp0..\venv\Scripts\python.exe"
set "LOCAL_PY=%~dp0venv\Scripts\python.exe"

if exist "%ROOT_PY%" (
    set "PYTHON_EXE=%ROOT_PY%"
) else if exist "%LOCAL_PY%" (
    set "PYTHON_EXE=%LOCAL_PY%"
) else (
    echo [ERROR] No Python virtual environment was found.
    echo [ERROR] Create ..\venv or .\venv first.
    pause
    exit /b 1
)

echo [INFO] Python: %PYTHON_EXE%
echo [INFO] Installing/checking dependencies...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

if not exist "storage" mkdir "storage"

if "%SECRET_KEY%"=="" set "SECRET_KEY=local-dev-secret-key"
if "%PORT%"=="" set "PORT=5000"

set "EXISTING_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /r /c:":%PORT% .*LISTENING"') do (
    set "EXISTING_PID=%%P"
    goto :port_found
)

:port_found
if defined EXISTING_PID (
    echo [WARN] Port %PORT% is already in use by PID %EXISTING_PID%.
    echo [WARN] Trying to stop the old process...
    taskkill /PID %EXISTING_PID% /F >nul 2>nul
    timeout /t 1 >nul
)

echo.
echo [INFO] Starting local test server...
echo [INFO] Open: http://127.0.0.1:%PORT%
echo [INFO] Press Ctrl+C to stop the server.
echo.

"%PYTHON_EXE%" app.py
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo [INFO] Server exited normally.
) else (
    echo [ERROR] Server exited with code %EXIT_CODE%.
)
pause

endlocal
