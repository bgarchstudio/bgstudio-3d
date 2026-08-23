@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo BG Studio 3D Urun Yoneticisi - Kontrol
echo ======================================
echo Repo: %CD%
echo Beklenen panel surumu: 2.8.5
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
echo --- Kalici veri kasasi ---
where py >nul 2>nul && py -3 "%~dp0tools\product_manager\storage_cli.py" status && goto :done
where python >nul 2>nul && python "%~dp0tools\product_manager\storage_cli.py" status && goto :done
where python3 >nul 2>nul && python3 "%~dp0tools\product_manager\storage_cli.py" status && goto :done
:done
echo.
echo Panel sekmesi aciksa kapat. Yeni paneli URUN-YONETICI.cmd ile ac.
echo.
pause
endlocal
