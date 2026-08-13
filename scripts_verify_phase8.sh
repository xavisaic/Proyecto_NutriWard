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

export PYTHONPATH=apps/backend
echo "[4/9] metadata unchanged"
python -c "from app.db.base import get_metadata; expected={'audit_logs','nutritionist_service_assignments','roles','users','user_roles','services','rooms','care_units','care_unit_layout_positions','patients','admissions','admission_status_history','patient_location_history','patient_transfer_requests','patient_transfer_request_status_history'}; actual=set(get_metadata().tables); assert expected==actual,(expected-actual,actual-expected)"
echo "[5/9] OpenAPI chart contracts"
python -c "from app.main import app; s=app.openapi(); p=s['paths']; expected={'/api/v1/patients/{patient_id}/chart-summary','/api/v1/admissions/{admission_id}/operational-timeline'}; assert expected<=set(p); assert {'page','page_size'}<={x['name'] for x in p['/api/v1/admissions/{admission_id}/operational-timeline']['get']['parameters']}"
echo "[6/9] single Alembic head"
(cd apps/backend && test "$(alembic heads | wc -l | tr -d ' ')" -eq 1 && alembic heads | grep -q '20260812_0009')
echo "[7/9] idempotent seeds"
python -c "from sqlalchemy.pool import StaticPool; from sqlmodel import Session,create_engine; from app.db.base import get_metadata; from app.db.seed import seed_database; e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool); get_metadata().create_all(e); s=Session(e); seed_database(s); first={k:len(s.exec(t.select()).all()) for k,t in get_metadata().tables.items()}; seed_database(s); second={k:len(s.exec(t.select()).all()) for k,t in get_metadata().tables.items()}; assert first==second,(first,second)"
echo "[8/9] compilation and conflict markers"
(cd apps/backend && python -m compileall -q app tests)
if git grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- . ':(exclude)apps/frontend/package-lock.json'; then exit 1; fi
echo "[9/9] Docker Compose config"
if command -v docker >/dev/null 2>&1; then docker compose -f infra/docker-compose.yml --env-file infra/.env.example config >/dev/null; else echo "Docker CLI unavailable; skipped."; fi
echo "Phase 8 verification completed."
