@echo off
setlocal
cd /d "%~dp0"
title BG Studio 3D - Urun Yoneticisi
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\product_manager\server.py
  goto :eof
)
where python >nul 2>nul
if %errorlevel%==0 (
  python tools\product_manager\server.py
  goto :eof
)
echo.
echo [BG Studio 3D] Python bulunamadi.
echo Urun Yoneticisi icin Python 3 gerekiyor.
echo https://www.python.org/downloads/ adresinden kurup tekrar deneyin.
echo Kurulumda "Add Python to PATH" secenegini isaretleyin.
echo.
pause
