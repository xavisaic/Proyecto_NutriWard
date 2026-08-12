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
PYTHONPATH=apps/backend python -c "from app.db.base import get_metadata; expected={'audit_logs','nutritionist_service_assignments','roles','users','user_roles','services','rooms','care_units','care_unit_layout_positions'}; actual=set(get_metadata().tables); assert expected <= actual, expected-actual; print('tables', sorted(actual))"

echo "[3/7] migration chain"
(
  cd apps/backend
  test "$(alembic heads | wc -l | tr -d ' ')" -eq 1 && alembic history | grep -q "20260728_0005"
  alembic upgrade head --sql >/dev/null
)

echo "[4/7] OpenAPI and health contracts"
PYTHONPATH=apps/backend python -c "from fastapi.testclient import TestClient; from app.main import app; paths=app.openapi()['paths']; expected={'/api/v1/users','/api/v1/users/{user_id}','/api/v1/users/{user_id}/roles','/api/v1/users/{user_id}/roles/{role_id}','/api/v1/users/{user_id}/service-assignments','/api/v1/roles','/api/v1/roles/{role_id}/users','/api/v1/nutritionist-service-assignments','/api/v1/nutritionist-service-assignments/{assignment_id}'}; assert expected <= set(paths), expected-set(paths); assert TestClient(app).get('/api/v1/health').status_code == 200; print('phase 4 endpoints', len(expected))"

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

echo "Phase 4 verification completed."
