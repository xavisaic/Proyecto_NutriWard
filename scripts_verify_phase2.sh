#!/usr/bin/env bash
set -euo pipefail

echo "[1/6] backend tests"
(cd apps/backend && python -m pytest)

echo "[2/6] backend import app.main"
python -c "import sys; sys.path.insert(0, 'apps/backend'); import app.main; print('import ok')"

echo "[3/6] health endpoint"
python - <<'PY'
import sys
sys.path.insert(0, 'apps/backend')
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
resp = client.get('/api/v1/health')
print(resp.status_code, resp.json())
assert resp.status_code == 200
assert resp.json()['status'] == 'ok'
PY

echo "[4/6] frontend tests and build"
cd apps/frontend
npm test
npm run build
cd - >/dev/null

echo "[5/6] alembic metadata and conflict markers"
python -c "import sys; sys.path.insert(0, 'apps/backend'); from app.db.base import get_metadata; m=get_metadata(); print('tables', list(m.tables.keys()))"
if git grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- . ':!package-lock.json'; then
  echo "Merge conflict markers found."
  exit 1
fi

echo "[6/6] docker compose config"
if command -v docker >/dev/null 2>&1; then
  docker compose -f infra/docker-compose.yml --env-file infra/.env.example config >/tmp/nutriward-docker-config.out
else
  echo "Docker CLI not available; compose validation skipped."
fi

echo "Phase 2 verification completed."
