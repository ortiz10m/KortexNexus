@echo off
setlocal

echo ============================================================
echo   KORTEX NEXUS v2.0 - Desinstalador para Windows
echo ============================================================
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\Programs\KortexNexus"

echo [1/4] Deteniendo Kortex Nexus...
taskkill /F /IM KortexNexus.exe >nul 2>&1

echo [2/4] Eliminando entrada de auto-inicio...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "KortexNexus" /f >nul 2>&1

echo [3/4] Eliminando accesos directos...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$desk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Kortex Nexus.lnk'; if (Test-Path $desk) { Remove-Item -Force $desk }; $start = Join-Path ([Environment]::GetFolderPath('Programs')) 'Kortex Nexus'; if (Test-Path $start) { Remove-Item -Recurse -Force $start }"

echo [4/4] Eliminando archivos del programa...
set /p "DELDATA=Eliminar tambien tus notas y configuracion en %USERPROFILE%\.kortex_nexus? (S/N) [N]: "
if /I "%DELDATA%"=="S" (
    rmdir /S /Q "%USERPROFILE%\.kortex_nexus" >nul 2>&1
    echo       Datos del usuario eliminados.
)

echo.
echo Desinstalacion finalizada.
if exist "%INSTALL_DIR%" (
    start "" /B cmd /C "ping 127.0.0.1 -n 2 >nul & rmdir /S /Q \"%INSTALL_DIR%\""
)
pause
exit /b 0
