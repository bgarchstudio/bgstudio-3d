@echo off
setlocal
chcp 65001 >nul 2>nul
title BG Studio 3D - Kalici Launcher Kontrol
set "HOME=%LOCALAPPDATA%\BGStudio3D\launcher"
echo.
echo ===============================================
echo      BG STUDIO 3D - LAUNCHER KONTROL
echo ===============================================
echo.
echo Klasor: %HOME%
echo.
if exist "%HOME%\BG-STUDIO-3D-YONETICI.cmd" (echo [OK] Kalici launcher var.) else (echo [YOK] Kalici launcher yok.)
if exist "%HOME%\repo-path.txt" (
  echo [OK] Repo yolu kaydi var:
  type "%HOME%\repo-path.txt"
) else (
  echo [YOK] repo-path.txt yok.
)
echo.
echo Klasor aciliyor...
start "" explorer.exe "%HOME%"
echo.
pause
