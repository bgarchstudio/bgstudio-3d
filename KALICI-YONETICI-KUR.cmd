@echo off
setlocal EnableExtensions DisableDelayedExpansion

rem If launched by double click, reopen inside cmd /k so ANY error stays visible.
if /i not "%~1"=="__BG3D_RUN__" (
  start "BG Studio 3D - Launcher Kurulumu" cmd.exe /k ""%~f0" __BG3D_RUN__"
  exit /b 0
)

chcp 65001 >nul 2>nul
title BG Studio 3D - Kalici Yonetici Kurulumu
cd /d "%~dp0"

set "APP_HOME=%LOCALAPPDATA%\BGStudio3D"
set "LAUNCH_HOME=%APP_HOME%\launcher"
set "LAUNCHER_SOURCE=%~dp0launcher\BG-STUDIO-3D-YONETICI.cmd"
set "LAUNCHER=%LAUNCH_HOME%\BG-STUDIO-3D-YONETICI.cmd"
set "REPO_FILE=%LAUNCH_HOME%\repo-path.txt"
set "ICON_TARGET=%LAUNCH_HOME%\bgstudio3d.ico"
set "SHORTCUT_NAME=BG Studio 3D Yonetici.lnk"
set "REPO="

echo.
echo =====================================================
echo       BG STUDIO 3D - KALICI YONETICI KURULUMU
echo =====================================================
echo.

if not exist "%LAUNCHER_SOURCE%" (
  echo [HATA] Launcher dosyasi bu pakette bulunamadi:
  echo %LAUNCHER_SOURCE%
  goto FATAL
)

rem 1) Installer repo root'a kopyalandiysa.
if exist "%~dp0tools\product_manager\server.py" set "REPO=%~dp0"

rem 2) Hotfix klasoru repo icine cikarildiysa parent klasoru dene.
if not defined REPO if exist "%~dp0..\tools\product_manager\server.py" set "REPO=%~dp0.."

rem 3) Daha once kaydedilmis repo yolunu dene.
if not defined REPO if exist "%REPO_FILE%" set /p "REPO="<"%REPO_FILE%"
if defined REPO set "REPO=%REPO:"=%"

:CHECK_REPO
if defined REPO if exist "%REPO%\tools\product_manager\server.py" goto HAVE_REPO

echo Repo klasoru otomatik bulunamadi.
echo.
echo bgstudio-3d klasorunun TAM yolunu yapistir.
echo Ornek: C:\Users\Berkant\Desktop\bgstudio-3d
echo.
set /p "REPO=Repo yolu: "
if not defined REPO (
  echo.
  echo [HATA] Repo yolu bos birakildi.
  goto FATAL
)
set "REPO=%REPO:"=%"
if not exist "%REPO%\tools\product_manager\server.py" (
  echo.
  echo [HATA] Bu klasorde tools\product_manager\server.py bulunamadi:
  echo %REPO%
  echo.
  set "REPO="
  goto CHECK_REPO
)

:HAVE_REPO
for %%I in ("%REPO%") do set "REPO=%%~fI"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"

echo [1/5] Repo bulundu:
echo       %REPO%
echo.

if not exist "%LAUNCH_HOME%" mkdir "%LAUNCH_HOME%" >nul 2>nul
if not exist "%LAUNCH_HOME%" (
  echo [HATA] Kalici launcher klasoru olusturulamadi:
  echo %LAUNCH_HOME%
  goto FATAL
)

echo [2/5] Kalici klasor hazir:
echo       %LAUNCH_HOME%

>"%REPO_FILE%" echo %REPO%
if errorlevel 1 (
  echo [HATA] Repo yolu kaydedilemedi.
  goto FATAL
)

copy /y "%LAUNCHER_SOURCE%" "%LAUNCHER%" >nul
if errorlevel 1 (
  echo [HATA] Kalici launcher kopyalanamadi.
  goto FATAL
)

echo [3/5] Kalici launcher olusturuldu.

rem Icon can be in repo or package. Missing icon is NOT fatal.
if exist "%REPO%\assets\brand\favicon.ico" copy /y /b "%REPO%\assets\brand\favicon.ico" "%ICON_TARGET%" >nul 2>nul

rem Remove Internet/Mark-of-the-Web flag from the LOCAL launcher.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%LAUNCHER%' -ErrorAction SilentlyContinue" >nul 2>nul

echo [4/5] Windows dosya engeli temizlendi.

set "PS_SCRIPT=%TEMP%\bg3d-create-shortcut-%RANDOM%.ps1"
>"%PS_SCRIPT%" echo $ErrorActionPreference = 'Stop'
>>"%PS_SCRIPT%" echo $w = New-Object -ComObject WScript.Shell
>>"%PS_SCRIPT%" echo $desktop = $w.SpecialFolders.Item('Desktop')
>>"%PS_SCRIPT%" echo if (-not $desktop) { throw 'Windows masaustu klasoru bulunamadi.' }
>>"%PS_SCRIPT%" echo $link = Join-Path $desktop '%SHORTCUT_NAME%'
>>"%PS_SCRIPT%" echo $s = $w.CreateShortcut($link)
>>"%PS_SCRIPT%" echo $s.TargetPath = '%LAUNCHER%'
>>"%PS_SCRIPT%" echo $s.WorkingDirectory = '%LAUNCH_HOME%'
>>"%PS_SCRIPT%" echo if (Test-Path '%ICON_TARGET%') { $s.IconLocation = '%ICON_TARGET%,0' }
>>"%PS_SCRIPT%" echo $s.Description = 'BG Studio 3D Kalici Yonetici'
>>"%PS_SCRIPT%" echo $s.Save()
>>"%PS_SCRIPT%" echo Unblock-File -LiteralPath $link -ErrorAction SilentlyContinue
>>"%PS_SCRIPT%" echo Write-Output $link

set "SHORTCUT_OUT=%TEMP%\bg3d-shortcut-out-%RANDOM%.txt"
set "SHORTCUT_ERR=%TEMP%\bg3d-shortcut-err-%RANDOM%.txt"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" >"%SHORTCUT_OUT%" 2>"%SHORTCUT_ERR%"
set "PS_CODE=%ERRORLEVEL%"
set "DESKTOP_LINK="
if exist "%SHORTCUT_OUT%" set /p "DESKTOP_LINK="<"%SHORTCUT_OUT%"

del /q "%PS_SCRIPT%" >nul 2>nul

if not "%PS_CODE%"=="0" goto SHORTCUT_FAIL
if not defined DESKTOP_LINK goto SHORTCUT_FAIL
if not exist "%DESKTOP_LINK%" goto SHORTCUT_FAIL

echo [5/5] Masaustu kisayolu olusturuldu.
echo.
echo =====================================================
echo                    KURULUM TAMAM
echo =====================================================
echo.
echo Masaustu : %DESKTOP_LINK%
echo Launcher : %LAUNCHER%
echo Veri      : %APP_HOME%
echo Repo      : %REPO%
echo.
echo Bundan sonra yeni ZIPlerdeki CMD dosyalarini acma.
echo Masaustundeki "BG Studio 3D Yonetici" kisayolunu kullan.
echo.
set /p "OPENNOW=Panel simdi acilsin mi? (E/H): "
if /i "%OPENNOW%"=="E" start "" "%LAUNCHER%"
if /i "%OPENNOW%"=="Y" start "" "%LAUNCHER%"
echo.
echo Bu pencereyi kapatmak icin bir tusa bas.
pause >nul
exit /b 0

:SHORTCUT_FAIL
echo.
echo [UYARI] Kalici launcher olusturuldu fakat masaustu kisayolu olusturulamadi.
echo.
echo Launcher burada:
echo %LAUNCHER%
echo.
if exist "%SHORTCUT_ERR%" (
  echo Windows/PowerShell hata ayrintisi:
  type "%SHORTCUT_ERR%"
  echo.
)
echo Launcher klasoru aciliyor.
start "" explorer.exe "%LAUNCH_HOME%"
echo BG-STUDIO-3D-YONETICI.cmd dosyasini elle acabilirsin.
echo.
pause
exit /b 2

:FATAL
echo.
echo =====================================================
echo                 KURULUM DURDURULDU
echo =====================================================
echo.
echo Yukaridaki hata ekranda kalacak. Ekran goruntusunu bana atabilirsin.
echo.
pause
exit /b 1
