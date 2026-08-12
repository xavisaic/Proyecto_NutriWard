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
    python -c "from app.db.base import get_metadata; expected={'audit_logs','nutritionist_service_assignments','roles','users','user_roles','services','rooms','care_units','care_unit_layout_positions'}; actual=set(get_metadata().tables); assert expected <= actual, expected-actual; print('tables', sorted(actual))"
    Assert-NativeSuccess "Database metadata validation"

    Write-Host "[3/7] migration chain"
    Push-Location "apps/backend"
    $heads = @(alembic heads)
    Assert-NativeSuccess "Alembic heads"
    if ($heads.Count -ne 1) { throw "Expected one Alembic head: $heads" }
    if (((alembic history) -join "`n") -notmatch "20260728_0005") { throw "Phase 4 revision is missing." }
    alembic upgrade head --sql | Out-Null
    Assert-NativeSuccess "Alembic migration chain"
    Pop-Location

    Write-Host "[4/7] OpenAPI and health contracts"
    python -c "from fastapi.testclient import TestClient; from app.main import app; paths=app.openapi()['paths']; expected={'/api/v1/users','/api/v1/users/{user_id}','/api/v1/users/{user_id}/roles','/api/v1/users/{user_id}/roles/{role_id}','/api/v1/users/{user_id}/service-assignments','/api/v1/roles','/api/v1/roles/{role_id}/users','/api/v1/nutritionist-service-assignments','/api/v1/nutritionist-service-assignments/{assignment_id}'}; assert expected <= set(paths), expected-set(paths); assert TestClient(app).get('/api/v1/health').status_code == 200; print('phase 4 endpoints', len(expected))"
    Assert-NativeSuccess "OpenAPI and health contracts"

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

    Write-Host "Phase 4 verification completed."
} finally {
    Pop-Location
}
