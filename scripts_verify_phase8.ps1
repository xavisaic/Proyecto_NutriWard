$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $repoRoot

function Assert-NativeSuccess([string]$step) {
    if ($LASTEXITCODE -ne 0) { throw "$step failed with exit code $LASTEXITCODE." }
}

try {
    Write-Host "[1/9] backend tests"
    Push-Location "apps/backend"
    python -m pytest
    Assert-NativeSuccess "Backend tests"
    Pop-Location

    Write-Host "[2/9] frontend tests"
    Push-Location "apps/frontend"
    npm.cmd test
    Assert-NativeSuccess "Frontend tests"
    Pop-Location

    Write-Host "[3/9] frontend production build"
    Push-Location "apps/frontend"
    npm.cmd run build
    Assert-NativeSuccess "Frontend build"
    Pop-Location

    $env:PYTHONPATH = "apps/backend"
    Write-Host "[4/9] metadata unchanged"
    python -c "from app.db.base import get_metadata; expected={'audit_logs','nutritionist_service_assignments','roles','users','user_roles','services','rooms','care_units','care_unit_layout_positions','patients','admissions','admission_status_history','patient_location_history','patient_transfer_requests','patient_transfer_request_status_history'}; actual=set(get_metadata().tables); assert expected==actual,(expected-actual,actual-expected); print('tables unchanged', sorted(actual))"
    Assert-NativeSuccess "Metadata"

    Write-Host "[5/9] OpenAPI chart contracts"
    python -c "from app.main import app; s=app.openapi(); p=s['paths']; expected={'/api/v1/patients/{patient_id}/chart-summary','/api/v1/admissions/{admission_id}/operational-timeline'}; assert expected<=set(p),expected-set(p); assert {'page','page_size'}<={x['name'] for x in p['/api/v1/admissions/{admission_id}/operational-timeline']['get']['parameters']}; print('OpenAPI valid')"
    Assert-NativeSuccess "OpenAPI"

    Write-Host "[6/9] single Alembic head"
    Push-Location "apps/backend"
    $heads = @(alembic heads)
    Assert-NativeSuccess "Alembic heads"
    if ($heads.Count -ne 1 -or $heads[0] -notmatch "20260812_0009") { throw "Unexpected Alembic heads: $heads" }
    Pop-Location

    Write-Host "[7/9] idempotent seeds"
    python -c "from sqlalchemy.pool import StaticPool; from sqlmodel import Session,create_engine; from app.db.base import get_metadata; from app.db.seed import seed_database; e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool); get_metadata().create_all(e); s=Session(e); seed_database(s); first={k:s.exec(t.select()).all().__len__() for k,t in get_metadata().tables.items()}; seed_database(s); second={k:s.exec(t.select()).all().__len__() for k,t in get_metadata().tables.items()}; assert first==second,(first,second); print('seeds stable')"
    Assert-NativeSuccess "Seeds"

    Write-Host "[8/9] compilation and conflict markers"
    Push-Location "apps/backend"
    python -m compileall -q app tests
    Assert-NativeSuccess "Python compilation"
    Pop-Location
    $markers = git grep -n -E "^(<<<<<<<|=======|>>>>>>>)" -- . ":(exclude)apps/frontend/package-lock.json"
    if ($LASTEXITCODE -eq 0) { throw "Merge conflict markers found:`n$markers" }

    Write-Host "[9/9] Docker Compose config"
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker compose -f infra/docker-compose.yml --env-file infra/.env.example config | Out-Null
        Assert-NativeSuccess "Docker Compose"
    } else { Write-Host "Docker CLI unavailable; skipped." }
    Write-Host "Phase 8 verification completed."
} finally { Pop-Location }
