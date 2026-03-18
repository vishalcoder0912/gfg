$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $root "ai-nl-analytics-dashboard\frontend"
$backendDir = Join-Path $root "ai-nl-analytics-dashboard\backend"
$pythonExe = Join-Path $root ".venv\Scripts\python.exe"

function Stop-PortProcess {
    param([int]$Port)

    $connections = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        Write-Host "Port $Port is already free."
        return
    }

    $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $pids) {
        try {
            $proc = Get-Process -Id $pid -ErrorAction Stop
            Write-Host "Stopping $($proc.ProcessName) (PID $pid) on port $Port..."
            Stop-Process -Id $pid -Force
        } catch {
            Write-Host ("Could not stop PID {0} on port {1}: {2}" -f $pid, $Port, $_.Exception.Message)
        }
    }

    Start-Sleep -Seconds 1
}

if (-not (Test-Path $pythonExe)) {
    throw "Python not found at $pythonExe"
}

Stop-PortProcess -Port 8000
Stop-PortProcess -Port 3000

Write-Host "Starting backend on http://127.0.0.1:8000 ..."
Start-Process -FilePath $pythonExe `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $backendDir

Write-Host "Starting frontend on http://127.0.0.1:3000 ..."
Start-Process -FilePath "npm.cmd" `
    -ArgumentList "run", "dev" `
    -WorkingDirectory $frontendDir

Write-Host ""
Write-Host "Frontend: http://127.0.0.1:3000"
Write-Host "Backend:  http://127.0.0.1:8000"
