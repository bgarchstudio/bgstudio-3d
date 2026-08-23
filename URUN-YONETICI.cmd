@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title BG Studio 3D - Urun Yoneticisi v2.6.3
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo.
echo [BG Studio 3D] Urun Yoneticisi v2.6.3 baslatiliyor...
echo Klasor: %CD%
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0tools\product_manager\server.py"
  goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
  python "%~dp0tools\product_manager\server.py"
  goto :end
)

where python3 >nul 2>nul
if %errorlevel%==0 (
  python3 "%~dp0tools\product_manager\server.py"
  goto :end
)

echo [HATA] Python 3 bulunamadi.
echo Ayarlar ^> Uygulamalar ^> Uygulama yurutme diger adlarinda Python kisayollarini kontrol et.
echo Python kuruluysa CMD'yi kapatip yeniden ac ve tekrar dene.
echo.
pause
:end
endlocal
