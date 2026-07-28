$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $repoRoot

function Assert-NativeSuccess([string]$step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$step failed with exit code $LASTEXITCODE."
    }
}

try {
    Write-Host "[1/6] backend tests"
    Push-Location "apps/backend"
    python -m pytest
    Assert-NativeSuccess "Backend tests"
    Pop-Location

    Write-Host "[2/6] backend import"
    $env:PYTHONPATH = "apps/backend"
    python -c "import app.main; print('import ok')"
    Assert-NativeSuccess "Backend import"

    Write-Host "[3/6] health endpoint"
    python -c "from fastapi.testclient import TestClient; from app.main import app; r=TestClient(app).get('/api/v1/health'); assert r.status_code == 200; print(r.json())"
    Assert-NativeSuccess "Health endpoint"

    Write-Host "[4/6] frontend tests and build"
    Push-Location "apps/frontend"
    npm.cmd test
    Assert-NativeSuccess "Frontend tests"
    npm.cmd run build
    Assert-NativeSuccess "Frontend build"
    Pop-Location

    Write-Host "[5/6] metadata and conflict markers"
    python -c "from app.db.base import get_metadata; print('tables', list(get_metadata().tables.keys()))"
    Assert-NativeSuccess "Database metadata"
    $markers = git grep -n -E "^(<<<<<<<|=======|>>>>>>>)" -- . ":(exclude)apps/frontend/package-lock.json"
    if ($LASTEXITCODE -eq 0) {
        throw "Merge conflict markers found:`n$markers"
    }

    Write-Host "[6/6] docker compose config"
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker compose -f infra/docker-compose.yml --env-file infra/.env.example config | Out-Null
        Assert-NativeSuccess "Docker Compose validation"
    } else {
        Write-Host "Docker CLI not available; compose validation skipped."
    }

    Write-Host "Phase 2 verification completed."
} finally {
    Pop-Location
}
