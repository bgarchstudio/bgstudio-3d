@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul 2>nul
title BG Studio 3D - Kalici Yonetici
set "APP_HOME=%LOCALAPPDATA%\BGStudio3D"
set "LAUNCH_HOME=%APP_HOME%\launcher"
set "REPO_FILE=%LAUNCH_HOME%\repo-path.txt"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if not exist "%LAUNCH_HOME%" mkdir "%LAUNCH_HOME%" >nul 2>nul
set "REPO="
if exist "%REPO_FILE%" set /p "REPO="<"%REPO_FILE%"
if defined REPO set "REPO=%REPO:"=%"

:CHECK_REPO
if not defined REPO goto CONFIGURE
if not exist "%REPO%\tools\product_manager\server.py" goto BAD_REPO
if not exist "%REPO%\tools\product_manager\storage_cli.py" goto BAD_REPO
goto RUN_PANEL

:BAD_REPO
cls
echo.
echo [BG Studio 3D] Kayitli repo yolu artik gecerli degil:
echo %REPO%
echo.
echo Repo klasorunu tasidiysan yeni yolu bir kez tanimlaman yeterli.
echo.
set "REPO="
goto CONFIGURE

:CONFIGURE
cls
echo.
echo ===============================================
echo        BG STUDIO 3D - KALICI YONETICI
echo ===============================================
echo.
echo bgstudio-3d repo klasorunun TAM yolunu yapistir.
echo Ornek: C:\Users\Berkant\Desktop\bgstudio-3d
echo.
set /p "REPO=Repo yolu: "
if not defined REPO exit /b 1
set "REPO=%REPO:"=%"
if not exist "%REPO%\tools\product_manager\server.py" (
  echo.
  echo [HATA] Bu klasorde tools\product_manager\server.py bulunamadi.
  echo.
  pause
  set "REPO="
  goto CONFIGURE
)
>"%REPO_FILE%" echo %REPO%
echo.
echo [OK] Repo yolu kalici olarak kaydedildi.
timeout /t 1 /nobreak >nul

:RUN_PANEL
cd /d "%REPO%" || goto BAD_REPO
cls
echo.
echo ===============================================
echo        BG STUDIO 3D - KALICI YONETICI
echo ===============================================
echo.
echo Repo : %CD%
echo Veri : %LOCALAPPDATA%\BGStudio3D
echo.
echo Kalici veriler hazirlaniyor...

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%REPO%\tools\product_manager\storage_cli.py" prepare
  if errorlevel 1 goto DATA_ERROR
  py -3 "%REPO%\tools\product_manager\server.py"
  goto END
)
where python >nul 2>nul
if %errorlevel%==0 (
  python "%REPO%\tools\product_manager\storage_cli.py" prepare
  if errorlevel 1 goto DATA_ERROR
  python "%REPO%\tools\product_manager\server.py"
  goto END
)
where python3 >nul 2>nul
if %errorlevel%==0 (
  python3 "%REPO%\tools\product_manager\storage_cli.py" prepare
  if errorlevel 1 goto DATA_ERROR
  python3 "%REPO%\tools\product_manager\server.py"
  goto END
)

echo.
echo [HATA] Python 3 bulunamadi.
echo Python kurulumunu kontrol et.
echo.
pause
goto END

:DATA_ERROR
echo.
echo [HATA] Kalici veri kasasi hazirlanamadi.
echo Verilerin silinmedi. Kapatip tekrar deneyebilirsin.
echo.
pause

:END
endlocal
