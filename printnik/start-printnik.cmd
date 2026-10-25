@echo off
if not defined PRINTNIK_PYTHON set "PRINTNIK_PYTHON=python"
"%PRINTNIK_PYTHON%" -c "import PIL, numpy" >nul 2>&1
if errorlevel 1 (
  echo Не найден Python с Pillow и NumPy. Установи зависимости из pyproject.toml или запусти Printnik-Setup.exe.
  pause
  exit /b 1
)
cd /d "%~dp0"
start "Печатник" "%PRINTNIK_PYTHON%" -m printnik.app
