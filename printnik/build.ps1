$ErrorActionPreference = 'Stop'
$Python = 'C:\Users\PC\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:PYTHONPATH = "$PSScriptRoot\.build-deps"
Set-Location $PSScriptRoot
Copy-Item "$PSScriptRoot\..\catalog-data\cut_size_rules.json" "$PSScriptRoot\config\cut_size_rules.json" -Force

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

Write-Host "READY: $PSScriptRoot\dist\Printnik.exe"
Write-Host "READY: $PSScriptRoot\dist\Printnik-Setup.exe"
