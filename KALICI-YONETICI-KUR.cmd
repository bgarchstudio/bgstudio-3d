@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul 2>nul
title BG Studio 3D - Kalici Yonetici Kurulumu
cd /d "%~dp0"
set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"
set "APP_HOME=%LOCALAPPDATA%\BGStudio3D"
set "LAUNCH_HOME=%APP_HOME%\launcher"
set "TEMPLATE=%~dp0tools\product_manager\launcher\BG-STUDIO-3D-YONETICI.template.txt"
set "LAUNCHER=%LAUNCH_HOME%\BG-STUDIO-3D-YONETICI.cmd"
set "REPO_FILE=%LAUNCH_HOME%\repo-path.txt"
set "ICON_SOURCE=%~dp0assets\brand\favicon.ico"
set "ICON_TARGET=%LAUNCH_HOME%\bgstudio3d.ico"
set "DESKTOP_LINK=%USERPROFILE%\Desktop\BG Studio 3D Yonetici.lnk"

echo.
echo ===============================================
echo      BG STUDIO 3D - KALICI LAUNCHER KUR
echo ===============================================
echo.

if not exist "%~dp0tools\product_manager\server.py" (
  echo [HATA] Bu dosyayi bgstudio-3d repo klasorunun icinden calistir.
  echo server.py bulunamadi.
  echo.
  pause
  exit /b 1
)
if not exist "%TEMPLATE%" (
  echo [HATA] Launcher sablonu bulunamadi.
  echo.
  pause
  exit /b 1
)

if not exist "%LAUNCH_HOME%" mkdir "%LAUNCH_HOME%" >nul 2>nul
>"%REPO_FILE%" echo %REPO%
type "%TEMPLATE%" > "%LAUNCHER%"
if exist "%ICON_SOURCE%" copy /y /b "%ICON_SOURCE%" "%ICON_TARGET%" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "$W=New-Object -ComObject WScript.Shell; $S=$W.CreateShortcut('%DESKTOP_LINK%'); $S.TargetPath='%LAUNCHER%'; $S.WorkingDirectory='%LAUNCH_HOME%'; if(Test-Path '%ICON_TARGET%'){$S.IconLocation='%ICON_TARGET%,0'}; $S.Description='BG Studio 3D Kalici Urun Yoneticisi'; $S.Save()" >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%LAUNCHER%' -ErrorAction SilentlyContinue; if(Test-Path '%DESKTOP_LINK%'){Unblock-File -LiteralPath '%DESKTOP_LINK%' -ErrorAction SilentlyContinue}" >nul 2>nul

echo [OK] Kalici launcher kuruldu.
echo.
echo Launcher : %LAUNCHER%
echo Repo yolu: %REPO_FILE%
echo Masaustu  : %DESKTOP_LINK%
echo.
echo Bundan sonra yeni ZIPlerdeki CMD dosyalarini kullanmana gerek yok.
echo Masaustundeki "BG Studio 3D Yonetici" kisayolunu acman yeterli.
echo.
set /p "OPENNOW=Panel simdi acilsin mi? (E/H): "
if /i "%OPENNOW%"=="E" start "" "%LAUNCHER%"
if /i "%OPENNOW%"=="Y" start "" "%LAUNCHER%"
echo.
pause
endlocal
