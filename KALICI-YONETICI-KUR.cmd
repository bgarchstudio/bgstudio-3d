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
set "SHORTCUT_NAME=BG Studio 3D Yonetici.lnk"

echo.
echo ===============================================
echo      BG STUDIO 3D - KALICI LAUNCHER KUR
echo ===============================================
echo.

if not exist "%~dp0tools\product_manager\server.py" (
  echo [HATA] Bu dosyayi bgstudio-3d repo klasorunun icinden calistir.
  echo tools\product_manager\server.py bulunamadi.
  echo.
  pause
  exit /b 1
)

if not exist "%TEMPLATE%" (
  echo [HATA] Launcher sablonu bulunamadi:
  echo %TEMPLATE%
  echo.
  echo HOTFIX ZIP'inin icindeki tools klasorunu repo uzerine kopyaladigindan emin ol.
  pause
  exit /b 1
)

if not exist "%LAUNCH_HOME%" mkdir "%LAUNCH_HOME%" >nul 2>nul
if not exist "%LAUNCH_HOME%" (
  echo [HATA] Kalici launcher klasoru olusturulamadi:
  echo %LAUNCH_HOME%
  pause
  exit /b 1
)

>"%REPO_FILE%" echo %REPO%
type "%TEMPLATE%" > "%LAUNCHER%"
if not exist "%LAUNCHER%" (
  echo [HATA] Kalici launcher dosyasi olusturulamadi.
  pause
  exit /b 1
)

if exist "%ICON_SOURCE%" copy /y /b "%ICON_SOURCE%" "%ICON_TARGET%" >nul 2>nul

rem Gercek Windows Masaustu klasorunu Shell API ile bulur. OneDrive yonlendirmesinde de calisir.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$w=New-Object -ComObject WScript.Shell;" ^
  "$desktop=$w.SpecialFolders.Item('Desktop');" ^
  "if(-not $desktop){throw 'Desktop klasoru bulunamadi'};" ^
  "$link=Join-Path $desktop '%SHORTCUT_NAME%';" ^
  "$s=$w.CreateShortcut($link);" ^
  "$s.TargetPath='%LAUNCHER%';" ^
  "$s.WorkingDirectory='%LAUNCH_HOME%';" ^
  "if(Test-Path '%ICON_TARGET%'){$s.IconLocation='%ICON_TARGET%,0'};" ^
  "$s.Description='BG Studio 3D Kalici Yonetici';" ^
  "$s.Save();" ^
  "Unblock-File -LiteralPath '%LAUNCHER%' -ErrorAction SilentlyContinue;" ^
  "Unblock-File -LiteralPath $link -ErrorAction SilentlyContinue;" ^
  "Write-Output $link" > "%TEMP%\bg3d-shortcut-path.txt" 2> "%TEMP%\bg3d-shortcut-error.txt"

set "PSERR=%ERRORLEVEL%"
set "DESKTOP_LINK="
if exist "%TEMP%\bg3d-shortcut-path.txt" set /p "DESKTOP_LINK="<"%TEMP%\bg3d-shortcut-path.txt"

if not "%PSERR%"=="0" goto SHORTCUT_FAIL
if not defined DESKTOP_LINK goto SHORTCUT_FAIL
if not exist "%DESKTOP_LINK%" goto SHORTCUT_FAIL

echo [OK] Kalici launcher olusturuldu.
echo [OK] Masaustu kisayolu olusturuldu.
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
exit /b 0

:SHORTCUT_FAIL
echo.
echo [UYARI] Kalici launcher olusturuldu ama Masaustu kisayolu olusturulamadi.
echo Launcher burada:
echo %LAUNCHER%
echo.
if exist "%TEMP%\bg3d-shortcut-error.txt" (
  echo Windows hatasi:
  type "%TEMP%\bg3d-shortcut-error.txt"
  echo.
)
echo Launcher klasoru simdi aciliyor. BG-STUDIO-3D-YONETICI.cmd dosyasina sag tiklayip
echo "Daha fazla secenek goster" ^> "Gonder" ^> "Masaustu (kisayol olustur)" da diyebilirsin.
start "" explorer.exe "%LAUNCH_HOME%"
echo.
pause
exit /b 2
