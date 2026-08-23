@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul 2>nul
title BG Studio 3D - Kalici Launcher Kurulumu
cd /d "%~dp0"
echo.
echo BG Studio 3D kalici launcher kurulumu baslatiliyor...
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL-LAUNCHER.ps1"
set "EC=%ERRORLEVEL%"
echo.
if not "%EC%"=="0" echo [HATA] Kurulum tamamlanamadi. Yukaridaki mesaji ekran goruntusu olarak gonderebilirsin.
if "%EC%"=="0" echo [OK] Kurulum tamamlandi.
echo.
echo Bu pencereyi kapatmak icin bir tusa bas.
pause >nul
exit /b %EC%
