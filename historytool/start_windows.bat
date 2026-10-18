@echo off
chcp 65001 >NUL
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  set "PY=python"
)
if not exist ".venv\Scripts\python.exe" (
  echo [historytool] Creez mediul local Python...
  %PY% -m venv .venv
  if errorlevel 1 goto error
  echo [historytool] Instalez dependintele, o singura data...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto error
)
echo [historytool] Pornesc aplicatia. In browser: http://127.0.0.1:8765
".venv\Scripts\python.exe" app.py
pause
exit /b 0
:error
echo [historytool] Eroare la instalare sau pornire. Este necesar Python 3.11+ si internet la prima instalare.
pause
exit /b 1
