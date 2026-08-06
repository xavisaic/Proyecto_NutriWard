#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

echo "[1/9] backend tests"
(cd apps/backend && python -m pytest)

echo "[2/9] frontend tests"
(cd apps/frontend && npm test)

echo "[3/9] frontend production build"
(cd apps/frontend && npm run build)

echo "[4/9] OpenAPI contract and application metadata"
PYTHONPATH=apps/backend python -c "from app.main import app; spec=app.openapi(); assert spec['info']['version']=='0.6.2'; paths=spec['paths']; assert {'/api/v1/patients/potential-matches','/api/v1/patients/{patient_id}/reconcile-active-conflict','/api/v1/nutritionist-service-assignments/me'} <= set(paths); operation=paths['/api/v1/bed-map']['get']; parameter=next(p for p in operation['parameters'] if p['name']=='service_id'); assert parameter['required'] and parameter['schema']['format']=='uuid'; response=spec['components']['schemas']['BedMapResponse']; assert set(response['required'])=={'generated_at','service','rooms'}; patient=spec['components']['schemas']['BedMapPatient']; assert set(patient['properties'])=={'id','display_name','identity_status','age_years','age_is_estimated'}; nn=spec['components']['schemas']['UnidentifiedPatientCreate']['properties']; assert {'given_names','first_surname','second_surname','age_years','hospital_identifier'} <= set(nn)"

echo "[5/9] database metadata remains unchanged"
PYTHONPATH=apps/backend python -c "from app.db.base import get_metadata; expected={'audit_logs','nutritionist_service_assignments','roles','users','user_roles','services','rooms','care_units','care_unit_layout_positions','patients','admissions','admission_status_history','patient_location_history'}; actual=set(get_metadata().tables); assert expected == actual, (expected-actual, actual-expected)"

echo "[6/9] Alembic chain and normalized unique patient number"
(cd apps/backend && test "$(alembic heads | grep -c 20260805_0008)" -eq 1 && alembic upgrade head --sql >/dev/null && alembic downgrade 20260805_0008:20260805_0007 --sql >/dev/null && alembic downgrade 20260805_0007:20260731_0006 --sql >/dev/null)

echo "[7/9] idempotent seeds"
PYTHONPATH=apps/backend python -c "from sqlalchemy.pool import StaticPool; from sqlmodel import Session,create_engine,func,select; from app.db.base import get_metadata; from app.db.seed import seed_database; from app.models.patient import Patient; from app.models.admission import Admission; from app.models.care_unit import CareUnit; e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool); get_metadata().create_all(e); s=Session(e); seed_database(s); first=(s.exec(select(func.count()).select_from(Patient)).one(),s.exec(select(func.count()).select_from(Admission)).one(),s.exec(select(func.count()).select_from(CareUnit)).one()); seed_database(s); second=(s.exec(select(func.count()).select_from(Patient)).one(),s.exec(select(func.count()).select_from(Admission)).one(),s.exec(select(func.count()).select_from(CareUnit)).one()); assert first==second==(4,4,10), (first,second)"

echo "[8/9] conflict markers"
if git grep -n -E "^(<<<<<<<|=======|>>>>>>>)" -- . ":(exclude)apps/frontend/package-lock.json"; then exit 1; fi

echo "[9/9] docker compose config"
if command -v docker >/dev/null 2>&1; then
  docker compose -f infra/docker-compose.yml --env-file infra/.env.example config >/dev/null
fi

echo "Phase 6 verification completed."
