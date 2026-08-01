#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

echo "[1/8] backend tests"
(cd apps/backend && python -m pytest)

echo "[2/8] database metadata"
PYTHONPATH=apps/backend python -c "from app.db.base import get_metadata; expected={'audit_logs','nutritionist_service_assignments','roles','users','user_roles','services','rooms','care_units','care_unit_layout_positions','patients','admissions','admission_status_history','patient_location_history'}; actual=set(get_metadata().tables); assert expected == actual, (expected-actual, actual-expected)"

echo "[3/8] migration chain and reversible SQL"
(cd apps/backend && alembic heads | grep -q "20260731_0006" && alembic upgrade head --sql >/dev/null && alembic downgrade 20260731_0006:20260728_0005 --sql >/dev/null)

echo "[4/8] idempotent Phase 5 seeds"
PYTHONPATH=apps/backend python -c "from sqlalchemy.pool import StaticPool; from sqlmodel import Session,create_engine,func,select; from app.db.base import get_metadata; from app.db.seed import seed_database; from app.models.patient import Patient; from app.models.admission import Admission; e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool); get_metadata().create_all(e); s=Session(e); seed_database(s); seed_database(s); assert s.exec(select(func.count()).select_from(Patient)).one()==4; assert s.exec(select(func.count()).select_from(Admission)).one()==4"

echo "[5/8] OpenAPI contracts"
PYTHONPATH=apps/backend python -c "from app.main import app; paths=app.openapi()['paths']; expected={'/api/v1/patients','/api/v1/patients/unidentified','/api/v1/patients/{patient_id}','/api/v1/patients/{patient_id}/identity','/api/v1/patients/{patient_id}/reconcile','/api/v1/patients/{patient_id}/admissions','/api/v1/admissions','/api/v1/admissions/active','/api/v1/admissions/{admission_id}','/api/v1/admissions/{admission_id}/status','/api/v1/admissions/{admission_id}/location','/api/v1/admissions/{admission_id}/location-history'}; assert expected <= set(paths), expected-set(paths)"

echo "[6/8] frontend tests and production build"
(cd apps/frontend && npm test && npm run build)

echo "[7/8] conflict markers"
if git grep -n -E "^(<<<<<<<|=======|>>>>>>>)" -- . ":(exclude)apps/frontend/package-lock.json"; then exit 1; fi

echo "[8/8] docker compose config"
if command -v docker >/dev/null 2>&1; then
  docker compose -f infra/docker-compose.yml --env-file infra/.env.example config >/dev/null
fi

echo "Phase 5 verification completed."
