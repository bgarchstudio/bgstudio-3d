@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title BG Studio 3D - Kalici Veri Gecisi
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
echo.
echo [BG Studio 3D] Mevcut panel verileri Windows AppData kalici kasasina aktariliyor...
echo Repo: %CD%
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0tools\product_manager\storage_cli.py" migrate
  goto :done
)
where python >nul 2>nul
if %errorlevel%==0 (
  python "%~dp0tools\product_manager\storage_cli.py" migrate
  goto :done
)
where python3 >nul 2>nul
if %errorlevel%==0 (
  python3 "%~dp0tools\product_manager\storage_cli.py" migrate
  goto :done
)
echo [HATA] Python 3 bulunamadi.
:done
echo.
echo Bu islem bir kez tamamlandiktan sonra urun, renk, logo ve referans verileri CMD/repo dosyalarindan bagimsiz kalir.
echo.
pause
endlocal
