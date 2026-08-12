#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

echo "[1/10] backend tests"
(cd apps/backend && python -m pytest)

echo "[2/10] frontend tests"
(cd apps/frontend && npm test -- --run)

echo "[3/10] frontend production build"
(cd apps/frontend && npm run build)

export PYTHONPATH=apps/backend
echo "[4/10] Phase 7 metadata"
python -c "from app.db.base import get_metadata; expected={'audit_logs','nutritionist_service_assignments','roles','users','user_roles','services','rooms','care_units','care_unit_layout_positions','patients','admissions','admission_status_history','patient_location_history','patient_transfer_requests','patient_transfer_request_status_history'}; actual=set(get_metadata().tables); assert expected==actual,(expected-actual,actual-expected); assert {'admission_id','origin_service_id','destination_service_id','origin_care_unit_id','destination_care_unit_id','transfer_mode','status'} <= set(get_metadata().tables['patient_transfer_requests'].c.keys())"

echo "[5/10] single Alembic head and chain"
(cd apps/backend && test "$(alembic heads | wc -l | tr -d ' ')" -eq 1 && alembic heads | grep -q '20260812_0009' && alembic history | grep -q '20260805_0008 -> 20260812_0009' && alembic upgrade head --sql >/dev/null && alembic downgrade 20260812_0009:20260805_0008 --sql >/dev/null)

echo "[6/10] OpenAPI transfer contract"
python -c "from app.main import app; s=app.openapi(); p=s['paths']; expected={'/api/v1/transfer-requests','/api/v1/transfer-requests/reception-tray','/api/v1/transfer-requests/{transfer_request_id}','/api/v1/admissions/{admission_id}/transfer-requests','/api/v1/transfer-requests/{transfer_request_id}/accept','/api/v1/transfer-requests/{transfer_request_id}/assign-bed','/api/v1/transfer-requests/{transfer_request_id}/reject','/api/v1/transfer-requests/{transfer_request_id}/return','/api/v1/transfer-requests/{transfer_request_id}/cancel'}; assert expected<=set(p),expected-set(p); assert set(s['components']['schemas']['TransferPatientSummary']['properties'])=={'id','display_name','identity_status','age_years','age_is_estimated'}; assert 'reason' not in s['components']['schemas']['TransferRequestCreate'].get('required',[]); assert 'patch' not in p['/api/v1/transfer-requests/{transfer_request_id}']"

echo "[7/10] idempotent Phase 7 seeds"
python -c "from sqlalchemy.pool import StaticPool; from sqlmodel import Session,create_engine,select; from app.db.base import get_metadata; from app.db.seed import seed_database; from app.models.patient_transfer_request import PatientTransferRequest; from app.models.patient_transfer_request_status_history import PatientTransferRequestStatusHistory; from app.models.patient_location_history import PatientLocationHistory; e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool); get_metadata().create_all(e); s=Session(e); seed_database(s); first=(len(s.exec(select(PatientTransferRequest)).all()),len(s.exec(select(PatientTransferRequestStatusHistory)).all()),len(s.exec(select(PatientLocationHistory)).all())); seed_database(s); second=(len(s.exec(select(PatientTransferRequest)).all()),len(s.exec(select(PatientTransferRequestStatusHistory)).all()),len(s.exec(select(PatientLocationHistory)).all())); statuses=set(s.exec(select(PatientTransferRequest.status)).all()); assert first==second and first[0]==6,(first,second); assert {'pending_reception','pending_bed','assigned_to_bed','rejected','returned','cancelled'}<=statuses"

echo "[8/10] no merge conflict markers"
if git grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- . ':(exclude)apps/frontend/package-lock.json'; then
  echo "Merge conflict markers found." >&2
  exit 1
fi

echo "[9/10] Python compilation"
(cd apps/backend && python -m compileall -q app tests)

echo "[10/10] Docker Compose config"
if command -v docker >/dev/null 2>&1; then
  docker compose -f infra/docker-compose.yml --env-file infra/.env.example config >/dev/null
else
  echo "Docker CLI not available; compose validation skipped."
fi

echo "Phase 7 verification completed."
