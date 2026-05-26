# Proyecto NutriWard

Bootstrap técnico inicial (Fase 2) para plataforma web de gestión nutricional clínica.

## Stack
- Frontend: React + TypeScript + Vite + MUI
- Backend: FastAPI + SQLModel/SQLAlchemy
- DB: PostgreSQL
- Migraciones: Alembic

## Estructura
- `apps/backend`: API FastAPI mínima con `/api/v1/health`
- `apps/frontend`: SPA mínima de inicio
- `infra`: Docker Compose + variables de entorno de ejemplo
- `docs/decisions`: ADRs aprobados

## Levantar con Docker
```bash
cp infra/.env.example infra/.env
docker compose -f infra/docker-compose.yml --env-file infra/.env up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Health: http://localhost:8000/api/v1/health

## Levantar local (sin Docker)
### Backend
```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp ../../infra/.env.example .env
# Ajustar DATABASE_URL a localhost si corresponde
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd apps/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## Verificación Fase 2
### Script único
```bash
./scripts_verify_phase2.sh
```

### Verificaciones manuales
```bash
# 1) Docker Compose válido
docker compose -f infra/docker-compose.yml --env-file infra/.env.example config

# 2) Backend importa app.main
python -c "import sys; sys.path.insert(0, 'apps/backend'); import app.main"

# 3) Health endpoint con TestClient
python - <<'PY'
import sys
sys.path.insert(0, 'apps/backend')
from fastapi.testclient import TestClient
from app.main import app
resp = TestClient(app).get('/api/v1/health')
print(resp.status_code, resp.json())
PY

# 4) Build frontend
cd apps/frontend && npm install && npm run build

# 5) Alembic/metadata
python -c "import sys; sys.path.insert(0, 'apps/backend'); from app.db.base import get_metadata; print(get_metadata())"
```

## Troubleshooting básico
- `docker: command not found`: instalar Docker Desktop/Engine o usar el flujo local sin Docker.
- `ModuleNotFoundError: app`: ejecutar comandos desde raíz repo o exportar `PYTHONPATH=apps/backend`.
- `npm: command not found`: instalar Node.js 20+.
- Error de conexión PostgreSQL local: revisar `DATABASE_URL` y puerto `5432`.
- `alembic` no encuentra configuración: ejecutar desde `apps/backend` o usar `alembic -c apps/backend/alembic.ini ...`.

## Alcance actual
- Base técnica solamente.
- Sin módulos clínicos avanzados.
- Sin datos reales.
