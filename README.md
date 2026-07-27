# Proyecto NutriWard

Base técnica completa de Fase 2 para una plataforma web de gestión nutricional clínica.

## Stack

- Frontend: React, TypeScript, Vite, MUI y Wouter
- Backend: FastAPI, SQLModel/SQLAlchemy y autenticación JWT
- Base de datos: PostgreSQL 16
- Migraciones: Alembic

## Funcionalidad disponible

- Login con JWT en cookie HttpOnly y protección CSRF.
- Roles `nutricionista`, `jefatura`, `alimentacion` y `administrador`.
- Restauración y cierre de sesión.
- Perfil autenticado y listado de usuarios protegido para jefatura/administrador.
- Auditoría de login exitoso, login fallido y logout.
- Migración inicial y seeds idempotentes con datos ficticios.

## Inicio con Docker

```bash
cp infra/.env.example infra/.env
docker compose -f infra/docker-compose.yml --env-file infra/.env up --build
```

- Aplicación: http://localhost:5173
- OpenAPI: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

La migración y los seeds se ejecutan automáticamente antes de iniciar la API.

## Inicio local

Backend en Linux/macOS:

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
cp ../../infra/.env.example .env
# En .env, cambiar db por localhost en DATABASE_URL.
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

Backend en PowerShell:

```powershell
cd apps/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
Copy-Item ..\..\infra\.env.example .env
# En .env, cambiar db por localhost en DATABASE_URL.
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd apps/frontend
npm install
npm run dev
```

## Usuarios demo

Todos usan la contraseña definida en `DEMO_USER_PASSWORD`:

- `nutricionista@nutriward.local`
- `jefatura@nutriward.local`
- `alimentacion@nutriward.local`
- `administrador@nutriward.local`

Las credenciales son ficticias y solo deben utilizarse en desarrollo.

## Verificación

```bash
./scripts_verify_phase2.sh
```

```powershell
.\scripts_verify_phase2.ps1
```

Los scripts ejecutan pruebas backend y frontend, build, carga de metadata, detección de conflictos y validación de Compose cuando Docker está disponible.

## Alcance

Fase 2 incluye identidad, RBAC, auditoría base e infraestructura local. Servicios, salas, camas y módulos clínicos comienzan en fases posteriores. No se incluyen datos reales.
