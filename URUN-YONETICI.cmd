@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title BG Studio 3D - Urun Yoneticisi v2.8.3
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo.
echo [BG Studio 3D] Urun Yoneticisi v2.8.3 baslatiliyor...
echo Klasor: %CD%
echo Veri: Windows AppData\Local\BGStudio3D

echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0tools\product_manager\storage_cli.py" prepare
  if errorlevel 1 goto :dataerror
  py -3 "%~dp0tools\product_manager\server.py"
  goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
  python "%~dp0tools\product_manager\storage_cli.py" prepare
  if errorlevel 1 goto :dataerror
  python "%~dp0tools\product_manager\server.py"
  goto :end
)

where python3 >nul 2>nul
if %errorlevel%==0 (
  python3 "%~dp0tools\product_manager\storage_cli.py" prepare
  if errorlevel 1 goto :dataerror
  python3 "%~dp0tools\product_manager\server.py"
  goto :end
)

echo [HATA] Python 3 bulunamadi.
echo Ayarlar ^> Uygulamalar ^> Uygulama yurutme diger adlarinda Python kisayollarini kontrol et.
echo.
pause
goto :end

:dataerror
echo.
echo [HATA] Kalici veri kasasi hazirlanamadi. Mevcut repo verilerine dokunulmadi.
echo KALICI-VERI-KONTROL.cmd dosyasini calistirip sonucu kontrol et.
echo.
pause

:end
endlocal
