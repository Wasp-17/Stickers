$ErrorActionPreference = 'Stop'
$siteRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$siteUrl = 'http://127.0.0.1:8766/index.html'

try {
    Invoke-WebRequest -UseBasicParsing -Uri $siteUrl -TimeoutSec 1 | Out-Null
} catch {
    $pythonPath = (Get-Command python -ErrorAction Stop).Source
    Start-Process -FilePath $pythonPath `
        -ArgumentList @('-m', 'http.server', '8766', '--bind', '127.0.0.1', '--directory', $siteRoot) `
        -WorkingDirectory $siteRoot `
        -WindowStyle Hidden

    $ready = $false
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 250
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $siteUrl -TimeoutSec 1 | Out-Null
            $ready = $true
            break
        } catch { }
    }
    if (-not $ready) { throw 'Local site server did not start.' }
}

Start-Process $siteUrl
