#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

echo "[1/12] backend full suite"
(cd apps/backend && python -m pytest)
echo "[2/12] frontend full suite"
(cd apps/frontend && npm test)
echo "[3/12] frontend production build"
(cd apps/frontend && npm run build)

echo "[4/12] OpenAPI clinical contracts and privacy"
(cd apps/backend && python -c "from app.main import app; p=app.openapi()['paths']; expected={'/api/v1/admissions/{admission_id}/nutrition-care-encounters','/api/v1/nutrition-care-encounters/{encounter_id}','/api/v1/nutrition-care-encounters/{encounter_id}/finalize','/api/v1/nutrition-care-encounters/{encounter_id}/correct','/api/v1/nutrition-care-encounters/{encounter_id}/cancel','/api/v1/admissions/{admission_id}/nutrition-latest','/api/v1/admissions/{admission_id}/nutrition-assessments','/api/v1/admissions/{admission_id}/nutrition-prescriptions','/api/v1/admissions/{admission_id}/nutrition-intake','/api/v1/admissions/{admission_id}/nutrition-labs','/api/v1/admissions/{admission_id}/clinical-context','/api/v1/admissions/{admission_id}/clinical-history','/api/v1/patients/{patient_id}/conditions','/api/v1/admissions/{admission_id}/diagnoses','/api/v1/patient-conditions/{condition_id}/status','/api/v1/admission-diagnoses/{diagnosis_id}/status','/api/v1/admissions/{admission_id}/allergy-intolerances','/api/v1/allergy-intolerances/{allergy_id}/status','/api/v1/allergy-intolerances/{allergy_id}/reactions','/api/v1/admissions/{admission_id}/allergy-review-assertions','/api/v1/admissions/{admission_id}/food-safety-allergies'}; assert expected<=set(p); assert not any('audit_logs' in path for path in p)")
echo "[5/12] metadata tables, constraints, precision and indexes"
(cd apps/backend && python -c "from app.db.base import get_metadata; m=get_metadata(); expected={'nutritional_care_encounters','nutritional_assessments','nutritional_clinical_context_items','nutritional_anthropometric_measurements','nutritional_measurement_sessions','nutritional_measurement_values','nutritional_screenings','nutritional_screening_answers','nutritional_requirement_calculations','nutritional_diagnoses','nutritional_prescriptions','nutritional_prescription_meal_times','nutritional_monitoring_records','nutritional_intake_records','nutritional_lab_observations','nutritional_alerts','patient_conditions','patient_condition_status_history','admission_diagnoses','admission_diagnosis_status_history','admission_clinical_history_versions','patient_allergy_intolerances','allergy_intolerance_reactions','allergy_intolerance_status_history','patient_allergy_review_assertions'}; assert expected<=set(m.tables); e=m.tables['nutritional_care_encounters']; assert {'admission_id','encounter_datetime','status','version'}<=set(e.c.keys()); assert any(i.name=='ix_nutrition_encounter_admission_datetime_status' for i in e.indexes); assert str(m.tables['nutritional_measurement_values'].c.value.type).startswith('NUMERIC')")
echo "[6/12] isolated migration upgrade, downgrade and re-upgrade"
(cd apps/backend && python -m pytest tests/test_phase9_migration.py tests/test_phase9_1_migration.py tests/test_phase9_2_migration.py tests/test_phase9_4_migration.py tests/test_phase9_5_migration.py -q)
echo "[7/12] single Alembic head"
(cd apps/backend && test "$(alembic heads | wc -l | tr -d ' ')" -eq 1 && alembic heads | grep -q '20260817_0014')
echo "[8/12] idempotent seeds without clinical fixtures"
(cd apps/backend && python -c "from sqlalchemy.pool import StaticPool; from sqlmodel import Session,create_engine; from app.db.base import get_metadata; from app.db.seed import seed_database; e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool); get_metadata().create_all(e); s=Session(e); seed_database(s); first={k:len(s.exec(t.select()).all()) for k,t in get_metadata().tables.items()}; seed_database(s); second={k:len(s.exec(t.select()).all()) for k,t in get_metadata().tables.items()}; assert first==second,(first,second); clinical={'patient_conditions','patient_condition_status_history','admission_diagnoses','admission_diagnosis_status_history','admission_clinical_history_versions','patient_allergy_intolerances','allergy_intolerance_reactions','allergy_intolerance_status_history','patient_allergy_review_assertions'}|{name for name in second if name.startswith('nutritional_')}; assert all(second[name]==0 for name in clinical)")
echo "[9/12] clinical algorithm tests"
(cd apps/backend && python -m pytest tests/test_nutrition.py tests/test_clinical_context.py tests/test_allergies.py -q)
echo "[10/12] Python compilation"
(cd apps/backend && python -m compileall -q app tests)
echo "[11/12] conflict markers and diff whitespace"
if command -v git.exe >/dev/null 2>&1; then git_tool=git.exe; else git_tool=git; fi
if "$git_tool" grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- . ':(exclude)apps/frontend/package-lock.json'; then exit 1; fi
"$git_tool" diff --check
echo "[12/12] Docker Compose configuration"
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then docker compose -f infra/docker-compose.yml --env-file infra/.env.example config >/dev/null; else echo "Docker daemon unavailable; Compose runtime skipped."; fi
echo "Phase 9.6 verification completed."
