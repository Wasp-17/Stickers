@echo off
set "PRINTNIK_PYTHON=C:\Users\PC\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%PRINTNIK_PYTHON%" (
  echo Не найден встроенный Python Codex. Установочная сборка Printnik-Setup.exe еще не создана.
  pause
  exit /b 1
)
cd /d "%~dp0"
start "Печатник" "%PRINTNIK_PYTHON%" -m printnik.app
