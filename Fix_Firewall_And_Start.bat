@echo off
setlocal enabledelayedexpansion
title JARVIS Companion Connection & Firewall Fix

:: Check for Administrator privileges, auto-elevate if not admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Administrator privileges required. Prompting UAC elevation...
    powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ========================================================
echo   JARVIS PHONE COMPANION — ONE-CLICK WI-FI FIX
echo ========================================================
echo.

echo [1/3] Configuring Windows Firewall for Port 8765...
netsh advfirewall firewall delete rule name="JARVIS Companion Port 8765" >nul 2>&1
netsh advfirewall firewall add rule name="JARVIS Companion Port 8765" dir=in action=allow protocol=TCP localport=8765 profile=any >nul 2>&1
echo   [OK] Inbound TCP Port 8765 allowed on ALL firewall profiles!

echo.
echo [2/3] Setting Network Profiles to Private...
powershell -NoProfile -Command "Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private -ErrorAction SilentlyContinue"
echo   [OK] Active network profiles set to Private (LAN communication allowed)!

echo.
echo [3/3] Detecting Laptop Wi-Fi IP Address...
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { ($_.InterfaceAlias -like '*Wi-Fi*' -or $_.InterfaceAlias -like '*Wireless*' -or $_.IPAddress -like '192.168.*' -or $_.IPAddress -like '10.*') -and $_.IPAddress -notlike '127.*' } | Select-Object -First 1).IPAddress"') do set LAPTOP_IP=%%i

if "%LAPTOP_IP%"=="" (
    for /f "tokens=*" %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | Select-Object -First 1).IPAddress"') do set LAPTOP_IP=%%i
)

echo.
echo ========================================================
echo   CURRENT LAPTOP CONNECTION DETAILS FOR PHONE APP
echo ========================================================
echo.
echo   >> LAPTOP IP : %LAPTOP_IP%
echo   >> PORT      : 8765
echo   >> PIN       : 742918
echo.
echo ========================================================
echo   HOW TO CONNECT FROM YOUR PHONE:
echo ========================================================
echo   1. Make sure JARVIS is running on your laptop.
echo   2. Open JARVIS Companion app on your phone.
echo   3. In 'Laptop IP' field, enter: %LAPTOP_IP%
echo   4. In 'Port' field, enter: 8765
echo   5. In 'PIN' field, enter: 742918
echo   6. Tap 'CONNECT TO JARVIS'!
echo.
echo ========================================================
echo.
set /p START_JARVIS="Kya aap JARVIS assistant abhi start karna chahte hain? (Y/N): "
if /i "%START_JARVIS%"=="Y" (
    echo Starting JARVIS...
    cd /d "%~dp0"
    start "" "run_jarvis.bat"
)
echo Done!
pause

