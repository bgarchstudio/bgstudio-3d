@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo BG Studio 3D Urun Yoneticisi - Kontrol
echo ======================================
echo Repo: %CD%
echo.
echo Beklenen panel surumu: 2.6.3
echo.
where py 2>nul
where python 2>nul
where python3 2>nul
echo.
if exist "tools\product_manager\server.py" (
  findstr /C:"PANEL_VERSION" "tools\product_manager\server.py"
) else (
  echo [HATA] server.py bulunamadi.
)
if exist "tools\product_manager\static\manager.js" (
  findstr /C:"PANEL_VERSION" "tools\product_manager\static\manager.js"
) else (
  echo [HATA] manager.js bulunamadi.
)
echo.
echo Bir onceki panel sekmesi aciksa kapat. Yeni paneli URUN-YONETICI.cmd ile ac.
echo.
pause
endlocal
