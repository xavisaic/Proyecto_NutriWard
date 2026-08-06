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

    Write-Host "[4/9] OpenAPI contract and application metadata"
    $env:PYTHONPATH = "apps/backend"
    python -c "from app.main import app; spec=app.openapi(); assert spec['info']['version']=='0.6.2'; paths=spec['paths']; assert {'/api/v1/patients/potential-matches','/api/v1/patients/{patient_id}/reconcile-active-conflict','/api/v1/nutritionist-service-assignments/me'} <= set(paths); operation=paths['/api/v1/bed-map']['get']; parameter=next(p for p in operation['parameters'] if p['name']=='service_id'); assert parameter['required'] and parameter['schema']['format']=='uuid'; response=spec['components']['schemas']['BedMapResponse']; assert set(response['required'])=={'generated_at','service','rooms'}; patient=spec['components']['schemas']['BedMapPatient']; assert set(patient['properties'])=={'id','display_name','identity_status','age_years','age_is_estimated'}; nn=spec['components']['schemas']['UnidentifiedPatientCreate']['properties']; assert {'given_names','first_surname','second_surname','age_years','hospital_identifier'} <= set(nn); print('phase 6 OpenAPI contract valid')"
    Assert-NativeSuccess "OpenAPI contract"

    Write-Host "[5/9] database metadata remains unchanged"
    python -c "from app.db.base import get_metadata; expected={'audit_logs','nutritionist_service_assignments','roles','users','user_roles','services','rooms','care_units','care_unit_layout_positions','patients','admissions','admission_status_history','patient_location_history'}; actual=set(get_metadata().tables); assert expected == actual, (expected-actual, actual-expected); print('tables', sorted(actual))"
    Assert-NativeSuccess "Database metadata"

    Write-Host "[6/9] Alembic chain and normalized unique patient number"
    Push-Location "apps/backend"
    $heads = alembic heads
    Assert-NativeSuccess "Alembic heads"
    if ($heads -notmatch "20260805_0008" -or $heads -match "\(branchpoint\)") { throw "Unexpected Alembic head: $heads" }
    alembic upgrade head --sql | Out-Null
    Assert-NativeSuccess "Alembic upgrade SQL"
    alembic downgrade 20260805_0008:20260805_0007 --sql | Out-Null
    Assert-NativeSuccess "Alembic patient number normalization downgrade SQL"
    alembic downgrade 20260805_0007:20260731_0006 --sql | Out-Null
    Assert-NativeSuccess "Alembic patient number uniqueness downgrade SQL"
    Pop-Location

    Write-Host "[7/9] idempotent seeds"
    python -c "from sqlalchemy.pool import StaticPool; from sqlmodel import Session,create_engine,func,select; from app.db.base import get_metadata; from app.db.seed import seed_database; from app.models.patient import Patient; from app.models.admission import Admission; from app.models.care_unit import CareUnit; e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool); get_metadata().create_all(e); s=Session(e); seed_database(s); first=(s.exec(select(func.count()).select_from(Patient)).one(),s.exec(select(func.count()).select_from(Admission)).one(),s.exec(select(func.count()).select_from(CareUnit)).one()); seed_database(s); second=(s.exec(select(func.count()).select_from(Patient)).one(),s.exec(select(func.count()).select_from(Admission)).one(),s.exec(select(func.count()).select_from(CareUnit)).one()); assert first==second==(4,4,10), (first,second); print('seed counts stable', second)"
    Assert-NativeSuccess "Idempotent seeds"

    Write-Host "[8/9] conflict markers"
    $markers = git grep -n -E "^(<<<<<<<|=======|>>>>>>>)" -- . ":(exclude)apps/frontend/package-lock.json"
    if ($LASTEXITCODE -eq 0) { throw "Merge conflict markers found:`n$markers" }

    Write-Host "[9/9] docker compose config"
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker compose -f infra/docker-compose.yml --env-file infra/.env.example config | Out-Null
        Assert-NativeSuccess "Docker Compose validation"
    } else {
        Write-Host "Docker CLI not available; compose validation skipped."
    }
    Write-Host "Phase 6 verification completed."
} finally {
    Pop-Location
}
