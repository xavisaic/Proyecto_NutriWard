# Backend (Fase 2)

## Ejecución local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
cp ../../infra/.env.example .env
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Pruebas

```bash
python -m pytest
```

## Endpoints

- `GET http://localhost:8000/api/v1/health`
- `POST http://localhost:8000/api/v1/auth/login`
- `GET http://localhost:8000/api/v1/auth/me`
- `POST http://localhost:8000/api/v1/auth/logout`
- `GET http://localhost:8000/api/v1/users`
