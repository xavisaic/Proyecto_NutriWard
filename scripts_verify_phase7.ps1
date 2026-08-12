$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $repoRoot

function Assert-NativeSuccess([string]$step) {
    if ($LASTEXITCODE -ne 0) { throw "$step failed with exit code $LASTEXITCODE." }
}

try {
    Write-Host "[1/10] backend tests"
    Push-Location "apps/backend"
    python -m pytest
    Assert-NativeSuccess "Backend tests"
    Pop-Location

    Write-Host "[2/10] frontend tests"
    Push-Location "apps/frontend"
    npm.cmd test -- --run
    Assert-NativeSuccess "Frontend tests"
    Pop-Location

    Write-Host "[3/10] frontend production build"
    Push-Location "apps/frontend"
    npm.cmd run build
    Assert-NativeSuccess "Frontend build"
    Pop-Location

    $env:PYTHONPATH = "apps/backend"
    Write-Host "[4/10] Phase 7 metadata"
    python -c "from app.db.base import get_metadata; expected={'audit_logs','nutritionist_service_assignments','roles','users','user_roles','services','rooms','care_units','care_unit_layout_positions','patients','admissions','admission_status_history','patient_location_history','patient_transfer_requests','patient_transfer_request_status_history'}; actual=set(get_metadata().tables); assert expected==actual,(expected-actual,actual-expected); transfer=get_metadata().tables['patient_transfer_requests']; assert {'admission_id','origin_service_id','destination_service_id','origin_care_unit_id','destination_care_unit_id','transfer_mode','status'} <= set(transfer.c.keys()); print('phase 7 tables', sorted(actual))"
    Assert-NativeSuccess "Database metadata"

    Write-Host "[5/10] single Alembic head and chain"
    Push-Location "apps/backend"
    $heads = @(alembic heads)
    Assert-NativeSuccess "Alembic heads"
    if ($heads.Count -ne 1 -or $heads[0] -notmatch "20260812_0009" -or $heads[0] -match "branchpoint") { throw "Unexpected Alembic heads: $heads" }
    $history = (alembic history) -join "`n"
    Assert-NativeSuccess "Alembic history"
    if ($history -notmatch "20260805_0008 -> 20260812_0009") { throw "Phase 7 is not chained from 20260805_0008." }
    alembic upgrade head --sql | Out-Null
    Assert-NativeSuccess "Alembic upgrade SQL"
    alembic downgrade 20260812_0009:20260805_0008 --sql | Out-Null
    Assert-NativeSuccess "Alembic downgrade SQL"
    Pop-Location

    Write-Host "[6/10] OpenAPI transfer contract"
    python -c "from app.main import app; s=app.openapi(); p=s['paths']; expected={'/api/v1/transfer-requests','/api/v1/transfer-requests/reception-tray','/api/v1/transfer-requests/{transfer_request_id}','/api/v1/admissions/{admission_id}/transfer-requests','/api/v1/transfer-requests/{transfer_request_id}/accept','/api/v1/transfer-requests/{transfer_request_id}/assign-bed','/api/v1/transfer-requests/{transfer_request_id}/reject','/api/v1/transfer-requests/{transfer_request_id}/return','/api/v1/transfer-requests/{transfer_request_id}/cancel'}; assert expected<=set(p),expected-set(p); patient=s['components']['schemas']['TransferPatientSummary']; assert set(patient['properties'])=={'id','display_name','identity_status','age_years','age_is_estimated'}; create=s['components']['schemas']['TransferRequestCreate']; assert 'reason' not in create.get('required',[]); assert 'patch' not in p['/api/v1/transfer-requests/{transfer_request_id}']; print('phase 7 OpenAPI valid')"
    Assert-NativeSuccess "OpenAPI"

    Write-Host "[7/10] idempotent Phase 7 seeds"
    python -c "from sqlalchemy.pool import StaticPool; from sqlmodel import Session,create_engine,select; from app.db.base import get_metadata; from app.db.seed import seed_database; from app.models.patient_transfer_request import PatientTransferRequest; from app.models.patient_transfer_request_status_history import PatientTransferRequestStatusHistory; from app.models.patient_location_history import PatientLocationHistory; e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool); get_metadata().create_all(e); s=Session(e); seed_database(s); first=(len(s.exec(select(PatientTransferRequest)).all()),len(s.exec(select(PatientTransferRequestStatusHistory)).all()),len(s.exec(select(PatientLocationHistory)).all())); seed_database(s); second=(len(s.exec(select(PatientTransferRequest)).all()),len(s.exec(select(PatientTransferRequestStatusHistory)).all()),len(s.exec(select(PatientLocationHistory)).all())); statuses=set(s.exec(select(PatientTransferRequest.status)).all()); assert first==second and first[0]==6,(first,second); assert {'pending_reception','pending_bed','assigned_to_bed','rejected','returned','cancelled'}<=statuses; print('seed counts stable', second)"
    Assert-NativeSuccess "Seeds"

    Write-Host "[8/10] no merge conflict markers"
    $markers = git grep -n -E "^(<<<<<<<|=======|>>>>>>>)" -- . ":(exclude)apps/frontend/package-lock.json"
    if ($LASTEXITCODE -eq 0) { throw "Merge conflict markers found:`n$markers" }

    Write-Host "[9/10] Python compilation"
    Push-Location "apps/backend"
    python -m compileall -q app tests
    Assert-NativeSuccess "Python compilation"
    Pop-Location

    Write-Host "[10/10] Docker Compose config"
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker compose -f infra/docker-compose.yml --env-file infra/.env.example config | Out-Null
        Assert-NativeSuccess "Docker Compose validation"
    } else {
        Write-Host "Docker CLI not available; compose validation skipped."
    }
    Write-Host "Phase 7 verification completed."
} finally {
    Pop-Location
}
