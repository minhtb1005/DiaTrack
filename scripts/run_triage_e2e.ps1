$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$frontend = Join-Path $root 'frontend'
$testRoot = Join-Path $root 'test-results\triage-e2e'
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$env:TRIAGE_E2E_DB_DIR = Join-Path $testRoot "run-$stamp"
$env:TRIAGE_E2E_API_PORT = '8108'
$env:TRIAGE_E2E_WEB_PORT = '3108'
$env:TRIAGE_E2E_EXTERNAL_SERVERS = '1'
$env:NEXT_PUBLIC_API_URL = 'http://127.0.0.1:8108'
$env:FRONTEND_URL = 'http://127.0.0.1:3108'

foreach ($port in @(8108, 3108)) {
    if (netstat -ano | Select-String -Pattern "127\.0\.0\.1:$port\s+.*LISTENING") {
        throw "Port $port is already in use; refusing to reuse an unknown server."
    }
}

$apiProcess = $null
$webProcess = $null
try {
    $apiProcess = Start-Process -FilePath (Join-Path $root '.venv\Scripts\python.exe') `
        -ArgumentList 'tests\triage_e2e_server.py' -WorkingDirectory $root -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $testRoot "run-$stamp-api.out.log") `
        -RedirectStandardError (Join-Path $testRoot "run-$stamp-api.err.log") -PassThru
    $webProcess = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','dev','--','-p','3108','-H','127.0.0.1' `
        -WorkingDirectory $frontend -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $testRoot "run-$stamp-web.out.log") `
        -RedirectStandardError (Join-Path $testRoot "run-$stamp-web.err.log") -PassThru
    foreach ($url in @('http://127.0.0.1:8108/openapi.json', 'http://127.0.0.1:3108')) {
        $ready = $false
        for ($i = 0; $i -lt 180; $i++) {
            try {
                $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
                if ($response.StatusCode -eq 200) { $ready = $true; break }
            } catch { Start-Sleep -Milliseconds 1000 }
        }
        if (-not $ready) { throw "Server did not become ready: $url" }
    }
    Push-Location $frontend
    try {
        & npm.cmd run test:e2e -- --config=playwright.triage-integration.config.ts
        $testExit = $LASTEXITCODE
    } finally { Pop-Location }
    if ($testExit -ne 0) { throw "Playwright exit code: $testExit" }
} finally {
    foreach ($port in @(3108, 8108)) {
        $listeners = netstat -ano | Select-String -Pattern "127\.0\.0\.1:$port\s+.*LISTENING"
        foreach ($listener in $listeners) {
            $listenerPid = [int](($listener.ToString().Trim() -split '\s+')[-1])
            Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue
        }
    }
    foreach ($started in @($webProcess, $apiProcess)) {
        if ($null -ne $started) {
            Stop-Process -Id $started.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
