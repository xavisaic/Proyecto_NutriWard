# Proyecto NutriWard

Base técnica completa de Fase 3 para una plataforma web de gestión nutricional clínica.

## Stack

- Frontend: React, TypeScript, Vite, MUI y Wouter
- Backend: FastAPI, SQLModel/SQLAlchemy y autenticación JWT
- Base de datos: PostgreSQL 16
- Migraciones: Alembic

## Funcionalidad disponible

- Login con JWT en cookie HttpOnly y protección CSRF.
- Roles `nutricionista`, `jefatura`, `alimentacion` y `administrador`.
- Restauración y cierre de sesión.
- Auditoría de autenticación y cambios en la estructura hospitalaria.
- Servicios, salas y ubicaciones asistenciales tipadas.
- Tipos de ubicación: cama, camilla, puesto y box.
- Importación idempotente de servicios, salas y ubicaciones desde Excel.
- Conservación de las observaciones de cada sala o sector.
- Consulta de la estructura activa para todos los roles autenticados.
- Administración para jefatura y administrador.
- Edición posterior de servicios, salas, ubicaciones y posiciones visuales.
- Sugerencia automática y editable de códigos de ubicación.
- Soft delete con protección de dependencias activas.
- Eliminación excepcional de registros erróneos, restringida a administrador.
- Migraciones y seeds idempotentes con datos ficticios.

## Inicio con Docker

```bash
cp infra/.env.example infra/.env
docker compose -f infra/docker-compose.yml --env-file infra/.env up --build
```

- Aplicación: http://localhost:5173
- OpenAPI: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

Las migraciones y los seeds se ejecutan automáticamente antes de iniciar la API.

## Inicio local

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

Los seeds incluyen servicios, salas y ubicaciones ficticias. No contienen información clínica real.

## Importar la estructura hospitalaria

El comando primero valida el archivo y simula la importación sin guardar:

```powershell
cd apps/backend
python -m app.cli.import_hospital_structure "C:\ruta\estructura.xlsx"
```

Si el resumen es correcto, se confirma con:

```powershell
python -m app.cli.import_hospital_structure "C:\ruta\estructura.xlsx" --apply
```

La operación es atómica e idempotente. Crea o actualiza los datos incluidos, registra el
checksum del archivo en auditoría y no elimina registros ausentes del Excel.

## Verificación

En PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts_verify_phase3.ps1
```

En Linux/macOS:

```bash
./scripts_verify_phase3.sh
```

El verificador ejecuta pruebas backend y frontend, build, contrato OpenAPI, metadata,
cadena de migraciones, detección de conflictos y validación de Compose cuando Docker
está disponible.

## Alcance

Fase 3 incluye identidad, RBAC, auditoría base e infraestructura hospitalaria. Pacientes,
hospitalizaciones, evaluaciones, prescripciones y otros datos clínicos comienzan en fases
posteriores.
