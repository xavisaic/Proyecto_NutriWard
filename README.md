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

## Alcance actual
- Base técnica solamente.
- Sin módulos clínicos avanzados.
- Sin datos reales.
