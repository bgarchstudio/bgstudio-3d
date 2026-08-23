@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title BG Studio 3D - Kalici Veri Kontrol
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
where py >nul 2>nul && py -3 "%~dp0tools\product_manager\storage_cli.py" status && goto :done
where python >nul 2>nul && python "%~dp0tools\product_manager\storage_cli.py" status && goto :done
where python3 >nul 2>nul && python3 "%~dp0tools\product_manager\storage_cli.py" status && goto :done
echo [HATA] Python 3 bulunamadi.
:done
echo.
pause
endlocal
