$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $repoRoot

function Assert-NativeSuccess([string]$step) {
    if ($LASTEXITCODE -ne 0) { throw "$step failed with exit code $LASTEXITCODE." }
}

try {
    Write-Host "[1/12] backend full suite"
    Push-Location "apps/backend"
    python -m pytest
    Assert-NativeSuccess "Backend tests"
    Pop-Location

    Write-Host "[2/12] frontend full suite"
    Push-Location "apps/frontend"
    npm.cmd test
    Assert-NativeSuccess "Frontend tests"
    Pop-Location

    Write-Host "[3/12] frontend production build"
    Push-Location "apps/frontend"
    npm.cmd run build
    Assert-NativeSuccess "Frontend build"
    Pop-Location

    $env:PYTHONPATH = "apps/backend"
    Write-Host "[4/12] OpenAPI clinical contracts and privacy"
    python -c "from app.main import app; p=app.openapi()['paths']; expected={'/api/v1/admissions/{admission_id}/nutrition-care-encounters','/api/v1/nutrition-care-encounters/{encounter_id}','/api/v1/nutrition-care-encounters/{encounter_id}/finalize','/api/v1/nutrition-care-encounters/{encounter_id}/correct','/api/v1/nutrition-care-encounters/{encounter_id}/cancel','/api/v1/admissions/{admission_id}/nutrition-latest','/api/v1/admissions/{admission_id}/nutrition-assessments','/api/v1/admissions/{admission_id}/nutrition-prescriptions','/api/v1/admissions/{admission_id}/nutrition-intake','/api/v1/admissions/{admission_id}/nutrition-labs','/api/v1/admissions/{admission_id}/clinical-context','/api/v1/admissions/{admission_id}/clinical-history','/api/v1/patients/{patient_id}/conditions','/api/v1/admissions/{admission_id}/diagnoses','/api/v1/patient-conditions/{condition_id}/status','/api/v1/admission-diagnoses/{diagnosis_id}/status','/api/v1/admissions/{admission_id}/allergy-intolerances','/api/v1/allergy-intolerances/{allergy_id}/status','/api/v1/allergy-intolerances/{allergy_id}/reactions','/api/v1/admissions/{admission_id}/allergy-review-assertions','/api/v1/admissions/{admission_id}/food-safety-allergies'}; assert expected<=set(p),expected-set(p); assert not any('audit_logs' in path for path in p); print('OpenAPI clinical contracts valid')"
    Assert-NativeSuccess "OpenAPI"

    Write-Host "[5/12] metadata tables, constraints, precision and indexes"
    python -c "from app.db.base import get_metadata; m=get_metadata(); expected={'nutritional_care_encounters','nutritional_assessments','nutritional_clinical_context_items','nutritional_anthropometric_measurements','nutritional_measurement_sessions','nutritional_measurement_values','nutritional_screenings','nutritional_screening_answers','nutritional_requirement_calculations','nutritional_diagnoses','nutritional_prescriptions','nutritional_prescription_meal_times','nutritional_monitoring_records','nutritional_intake_records','nutritional_lab_observations','nutritional_alerts','patient_conditions','patient_condition_status_history','admission_diagnoses','admission_diagnosis_status_history','admission_clinical_history_versions','patient_allergy_intolerances','allergy_intolerance_reactions','allergy_intolerance_status_history','patient_allergy_review_assertions'}; assert expected<=set(m.tables),expected-set(m.tables); e=m.tables['nutritional_care_encounters']; assert {'admission_id','encounter_datetime','status','version'}<=set(e.c.keys()); assert any(i.name=='ix_nutrition_encounter_admission_datetime_status' for i in e.indexes); assert str(m.tables['nutritional_measurement_values'].c.value.type).startswith('NUMERIC'); print('Phase 9.5 metadata valid')"
    Assert-NativeSuccess "Metadata"

    Write-Host "[6/12] isolated migration upgrade, downgrade and re-upgrade"
    Push-Location "apps/backend"
    python -m pytest tests/test_phase9_migration.py tests/test_phase9_1_migration.py tests/test_phase9_2_migration.py tests/test_phase9_4_migration.py tests/test_phase9_5_migration.py -q
    Assert-NativeSuccess "Migration cycle"
    Pop-Location

    Write-Host "[7/12] single Alembic head"
    Push-Location "apps/backend"
    $heads = @(alembic heads)
    Assert-NativeSuccess "Alembic heads"
    if ($heads.Count -ne 1 -or $heads[0] -notmatch "20260817_0014") { throw "Unexpected Alembic heads: $heads" }
    Pop-Location

    Write-Host "[8/12] idempotent seeds without clinical fixtures"
    python -c "from sqlalchemy.pool import StaticPool; from sqlmodel import Session,create_engine; from app.db.base import get_metadata; from app.db.seed import seed_database; e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool); get_metadata().create_all(e); s=Session(e); seed_database(s); first={k:len(s.exec(t.select()).all()) for k,t in get_metadata().tables.items()}; seed_database(s); second={k:len(s.exec(t.select()).all()) for k,t in get_metadata().tables.items()}; assert first==second,(first,second); clinical={'patient_conditions','patient_condition_status_history','admission_diagnoses','admission_diagnosis_status_history','admission_clinical_history_versions','patient_allergy_intolerances','allergy_intolerance_reactions','allergy_intolerance_status_history','patient_allergy_review_assertions'}|{name for name in second if name.startswith('nutritional_')}; assert all(second[name]==0 for name in clinical); print('seeds stable and clinically empty')"
    Assert-NativeSuccess "Seeds"

    Write-Host "[9/12] clinical algorithm tests"
    Push-Location "apps/backend"
    python -m pytest tests/test_nutrition.py tests/test_clinical_context.py tests/test_allergies.py -q
    Assert-NativeSuccess "Clinical algorithms"
    Pop-Location

    Write-Host "[10/12] Python compilation"
    Push-Location "apps/backend"
    python -m compileall -q app tests
    Assert-NativeSuccess "Python compilation"
    Pop-Location

    Write-Host "[11/12] conflict markers and diff whitespace"
    $markers = git grep -n -E "^(<<<<<<<|=======|>>>>>>>)" -- . ":(exclude)apps/frontend/package-lock.json"
    if ($LASTEXITCODE -eq 0) { throw "Merge conflict markers found:`n$markers" }
    git diff --check
    Assert-NativeSuccess "git diff --check"

    Write-Host "[12/12] Docker Compose configuration"
    $dockerReady = $false
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $previousErrorPreference = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"
        docker info 2>$null | Out-Null
        $dockerReady = $LASTEXITCODE -eq 0
        $ErrorActionPreference = $previousErrorPreference
    }
    if ($dockerReady) {
        docker compose -f infra/docker-compose.yml --env-file infra/.env.example config | Out-Null
        Assert-NativeSuccess "Docker Compose"
    } else { Write-Host "Docker daemon unavailable; Compose runtime skipped." }
    Write-Host "Phase 9.6 verification completed."
} finally { Pop-Location }
