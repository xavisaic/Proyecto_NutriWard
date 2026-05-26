# Backend (Fase 2 Bootstrap)

## Run local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp ../../infra/.env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Health endpoint
- `GET http://localhost:8000/api/v1/health`
