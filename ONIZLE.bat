@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  start "BG Studio 3D Local Server" cmd /k "cd /d "%~dp0" && py -3 -m http.server 8000"
  timeout /t 2 /nobreak >nul
  start "" http://localhost:8000/index.html
  exit /b
)
where python >nul 2>&1
if %errorlevel%==0 (
  start "BG Studio 3D Local Server" cmd /k "cd /d "%~dp0" && python -m http.server 8000"
  timeout /t 2 /nobreak >nul
  start "" http://localhost:8000/index.html
  exit /b
)
echo Python bulunamadi. Site index.html ile aciliyor.
start "" index.html
