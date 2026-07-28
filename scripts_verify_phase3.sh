#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

echo "[1/7] backend tests"
(
  cd apps/backend
  python -m pytest
)

echo "[2/7] database metadata"
PYTHONPATH=apps/backend python -c "from app.db.base import get_metadata; expected={'audit_logs','nutritionist_service_assignments','roles','users','user_roles','services','rooms','care_units','care_unit_layout_positions'}; actual=set(get_metadata().tables); assert expected == actual, (expected-actual, actual-expected); print('tables', sorted(actual))"

echo "[3/7] migration chain"
(
  cd apps/backend
  alembic heads | grep -q "20260728_0004"
  alembic upgrade head --sql >/dev/null
)

echo "[4/7] OpenAPI contract"
PYTHONPATH=apps/backend python -c "from app.main import app; paths=app.openapi()['paths']; expected={'/api/v1/hospital/structure','/api/v1/hospital/services','/api/v1/hospital/services/{service_id}','/api/v1/hospital/rooms','/api/v1/hospital/rooms/{room_id}','/api/v1/hospital/care-units','/api/v1/hospital/care-units/{care_unit_id}','/api/v1/hospital/care-units/{care_unit_id}/layout'}; assert expected <= set(paths), expected-set(paths); print('hospital endpoints', len(expected))"

echo "[5/7] frontend tests and build"
(
  cd apps/frontend
  npm test
  npm run build
)

echo "[6/7] conflict markers"
if git grep -n -E "^(<<<<<<<|=======|>>>>>>>)" -- . ":(exclude)apps/frontend/package-lock.json"; then
  echo "Merge conflict markers found."
  exit 1
fi

echo "[7/7] docker compose config"
if command -v docker >/dev/null 2>&1; then
  docker compose -f infra/docker-compose.yml --env-file infra/.env.example config >/dev/null
else
  echo "Docker CLI not available; compose validation skipped."
fi

echo "Phase 3 verification completed."
