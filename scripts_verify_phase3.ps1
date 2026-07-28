$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $repoRoot

function Assert-NativeSuccess([string]$step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$step failed with exit code $LASTEXITCODE."
    }
}

try {
    Write-Host "[1/7] backend tests"
    Push-Location "apps/backend"
    python -m pytest
    Assert-NativeSuccess "Backend tests"
    Pop-Location

    Write-Host "[2/7] database metadata"
    $env:PYTHONPATH = "apps/backend"
    python -c "from app.db.base import get_metadata; expected={'audit_logs','nutritionist_service_assignments','roles','users','user_roles','services','rooms','care_units','care_unit_layout_positions'}; actual=set(get_metadata().tables); assert expected == actual, (expected-actual, actual-expected); print('tables', sorted(actual))"
    Assert-NativeSuccess "Database metadata validation"

    Write-Host "[3/7] migration chain"
    Push-Location "apps/backend"
    $heads = alembic heads
    Assert-NativeSuccess "Alembic heads"
    if ($heads -notmatch "20260728_0004") {
        throw "Unexpected Alembic head: $heads"
    }
    alembic upgrade head --sql | Out-Null
    Assert-NativeSuccess "Alembic migration chain"
    Pop-Location

    Write-Host "[4/7] OpenAPI contract"
    python -c "from app.main import app; paths=app.openapi()['paths']; expected={'/api/v1/hospital/structure','/api/v1/hospital/services','/api/v1/hospital/services/{service_id}','/api/v1/hospital/rooms','/api/v1/hospital/rooms/{room_id}','/api/v1/hospital/care-units','/api/v1/hospital/care-units/{care_unit_id}','/api/v1/hospital/care-units/{care_unit_id}/layout'}; assert expected <= set(paths), expected-set(paths); print('hospital endpoints', len(expected))"
    Assert-NativeSuccess "OpenAPI contract"

    Write-Host "[5/7] frontend tests and build"
    Push-Location "apps/frontend"
    npm.cmd test
    Assert-NativeSuccess "Frontend tests"
    npm.cmd run build
    Assert-NativeSuccess "Frontend build"
    Pop-Location

    Write-Host "[6/7] conflict markers"
    $markers = git grep -n -E "^(<<<<<<<|=======|>>>>>>>)" -- . ":(exclude)apps/frontend/package-lock.json"
    if ($LASTEXITCODE -eq 0) {
        throw "Merge conflict markers found:`n$markers"
    }

    Write-Host "[7/7] docker compose config"
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker compose -f infra/docker-compose.yml --env-file infra/.env.example config | Out-Null
        Assert-NativeSuccess "Docker Compose validation"
    } else {
        Write-Host "Docker CLI not available; compose validation skipped."
    }

    Write-Host "Phase 3 verification completed."
} finally {
    Pop-Location
}
