$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $repoRoot

function Assert-NativeSuccess([string]$step) {
    if ($LASTEXITCODE -ne 0) { throw "$step failed with exit code $LASTEXITCODE." }
}

try {
    Write-Host "[1/8] backend tests"
    Push-Location "apps/backend"
    python -m pytest
    Assert-NativeSuccess "Backend tests"
    Pop-Location

    Write-Host "[2/8] database metadata"
    $env:PYTHONPATH = "apps/backend"
    python -c "from app.db.base import get_metadata; expected={'audit_logs','nutritionist_service_assignments','roles','users','user_roles','services','rooms','care_units','care_unit_layout_positions','patients','admissions','admission_status_history','patient_location_history'}; actual=set(get_metadata().tables); assert expected <= actual, expected-actual; print('tables', sorted(actual))"
    Assert-NativeSuccess "Database metadata"

    Write-Host "[3/8] migration chain and reversible SQL"
    Push-Location "apps/backend"
    $heads = @(alembic heads)
    Assert-NativeSuccess "Alembic heads"
    if ($heads.Count -ne 1) { throw "Expected one Alembic head: $heads" }
    $history = alembic history
    if (($history -join "`n") -notmatch "20260731_0006") { throw "Phase 5 revision is missing from Alembic history." }
    alembic upgrade head --sql | Out-Null
    Assert-NativeSuccess "Alembic upgrade SQL"
    alembic downgrade 20260731_0006:20260728_0005 --sql | Out-Null
    Assert-NativeSuccess "Alembic downgrade SQL"
    Pop-Location

    Write-Host "[4/8] idempotent Phase 5 seeds"
    python -c "from sqlalchemy.pool import StaticPool; from sqlmodel import Session,create_engine,func,select; from app.db.base import get_metadata; from app.db.seed import seed_database; from app.models.patient import Patient; from app.models.admission import Admission; e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool); get_metadata().create_all(e); s=Session(e); seed_database(s); seed_database(s); assert s.exec(select(func.count()).select_from(Patient)).one()==4; assert s.exec(select(func.count()).select_from(Admission)).one()==4; print('seed counts stable')"
    Assert-NativeSuccess "Idempotent seeds"

    Write-Host "[5/8] OpenAPI contracts"
    python -c "from app.main import app; paths=app.openapi()['paths']; expected={'/api/v1/patients','/api/v1/patients/unidentified','/api/v1/patients/{patient_id}','/api/v1/patients/{patient_id}/identity','/api/v1/patients/{patient_id}/reconcile','/api/v1/patients/{patient_id}/admissions','/api/v1/admissions','/api/v1/admissions/active','/api/v1/admissions/{admission_id}','/api/v1/admissions/{admission_id}/status','/api/v1/admissions/{admission_id}/location','/api/v1/admissions/{admission_id}/location-history'}; assert expected <= set(paths), expected-set(paths); print('phase 5 endpoints', len(expected))"
    Assert-NativeSuccess "OpenAPI contracts"

    Write-Host "[6/8] frontend tests and production build"
    Push-Location "apps/frontend"
    npm.cmd test
    Assert-NativeSuccess "Frontend tests"
    npm.cmd run build
    Assert-NativeSuccess "Frontend build"
    Pop-Location

    Write-Host "[7/8] conflict markers"
    $markers = git grep -n -E "^(<<<<<<<|=======|>>>>>>>)" -- . ":(exclude)apps/frontend/package-lock.json"
    if ($LASTEXITCODE -eq 0) { throw "Merge conflict markers found:`n$markers" }

    Write-Host "[8/8] docker compose config"
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker compose -f infra/docker-compose.yml --env-file infra/.env.example config | Out-Null
        Assert-NativeSuccess "Docker Compose validation"
    } else {
        Write-Host "Docker CLI not available; compose validation skipped."
    }
    Write-Host "Phase 5 verification completed."
} finally {
    Pop-Location
}
