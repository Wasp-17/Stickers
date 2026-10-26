$ErrorActionPreference = 'Stop'
$Python = if ($env:PRINTNIK_PYTHON) { $env:PRINTNIK_PYTHON }
          elseif (Test-Path "$PSScriptRoot\.venv\Scripts\python.exe") { "$PSScriptRoot\.venv\Scripts\python.exe" }
          else { 'python' }
Set-Location $PSScriptRoot

& $Python -m PyInstaller --noconfirm --clean --windowed --onefile `
  --name Printnik `
  --add-data "config;config" `
  printnik_launcher.py
if ($LASTEXITCODE -ne 0) { throw "Не удалось собрать Printnik.exe (код $LASTEXITCODE)" }

New-Item -ItemType Directory -Force -Path "$PSScriptRoot\installer-payload\payload" | Out-Null
Copy-Item "$PSScriptRoot\dist\Printnik.exe" "$PSScriptRoot\installer-payload\payload\Printnik.exe" -Force

& $Python -m PyInstaller --noconfirm --clean --windowed --onefile `
  --name Printnik-Setup `
  --add-binary "$PSScriptRoot\installer-payload\payload\Printnik.exe;payload" `
  installer.py
if ($LASTEXITCODE -ne 0) { throw "Не удалось собрать Printnik-Setup.exe (код $LASTEXITCODE)" }

$VersionedSetup = "$PSScriptRoot\dist\Printnik-Setup-$(Get-Date -Format 'yyyyMMdd-HHmmss').exe"
Copy-Item "$PSScriptRoot\dist\Printnik-Setup.exe" $VersionedSetup -Force

Write-Host "READY: $PSScriptRoot\dist\Printnik.exe"
Write-Host "READY: $PSScriptRoot\dist\Printnik-Setup.exe"
Write-Host "READY FOR DOWNLOAD: $VersionedSetup"
