@echo off
setlocal

set "EXE_SRC=%~dp0KortexNexus\KortexNexus.exe"

if not exist "%EXE_SRC%" (
    echo [ERROR] No se encontro "%EXE_SRC%".
    echo Extrae todo el archivo ZIP antes de ejecutar este instalador.
    pause
    exit /b 1
)

if /I "%~1"=="--cli" goto :CLI_MODE

start "" "%EXE_SRC%" --install
exit /b 0

:CLI_MODE
echo ============================================================
echo   KORTEX NEXUS v2.0 - Instalador CLI para Windows
echo ============================================================
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\KortexNexus"
set "EXE_PATH=%INSTALL_DIR%\KortexNexus.exe"
taskkill /F /IM KortexNexus.exe >nul 2>&1
if exist "%INSTALL_DIR%" rmdir /S /Q "%INSTALL_DIR%"
mkdir "%INSTALL_DIR%" >nul 2>&1
xcopy "%~dp0KortexNexus\*" "%INSTALL_DIR%\" /E /I /H /Y /Q >nul
copy /Y "%~dp0uninstall_windows.bat" "%INSTALL_DIR%\uninstall_windows.bat" >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "KortexNexus" /t REG_SZ /d "\"%EXE_PATH%\" --daemon" /f >nul
echo Instalado en %INSTALL_DIR%
exit /b 0
