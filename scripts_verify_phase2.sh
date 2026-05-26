#!/usr/bin/env bash
set -euo pipefail

echo "[1/5] docker compose config"
docker compose -f infra/docker-compose.yml --env-file infra/.env.example config >/tmp/nutriward-docker-config.out

echo "[2/5] backend import app.main"
python -c "import sys; sys.path.insert(0, 'apps/backend'); import app.main; print('import ok')"

echo "[3/5] health endpoint"
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

echo "[4/5] frontend build"
cd apps/frontend
npm run build
cd - >/dev/null

echo "[5/5] alembic metadata load"
python -c "import sys; sys.path.insert(0, 'apps/backend'); from app.db.base import get_metadata; m=get_metadata(); print('tables', list(m.tables.keys()))"

echo "Phase 2 verification completed."
