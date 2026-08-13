# Proyecto NutriWard

Base técnica completa hasta Fase 8 para una plataforma web de gestión nutricional clínica.

Fase 8 incorpora una ficha longitudinal navegable en `/patients/:patient_id/:tab`,
con selector de hospitalización, Resumen, Movimientos e Historial funcionales. Los
módulos clínico-nutricionales permanecen como placeholders sin persistencia. Ver
`docs/planning/FASE-8-FICHA-PACIENTE-PESTANAS.md`.

## Stack

- Frontend: React, TypeScript, Vite, MUI y Wouter
- Backend: FastAPI, SQLModel/SQLAlchemy y autenticación JWT
- Base de datos: PostgreSQL 16
- Migraciones: Alembic

## Funcionalidad disponible

- Login con JWT en cookie HttpOnly y protección CSRF.
- Roles `nutricionista`, `jefatura`, `alimentacion` y `administrador`.
- Administración de usuarios con creación, edición e inactivación lógica.
- Asignación y retiro lógico de múltiples roles por usuario.
- Coberturas habituales no exclusivas de nutricionistas en uno o varios servicios.
- Vistas de administración para usuarios/roles y asignaciones de servicios.
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
- Pacientes identificados, provisorios y NN con RUT validado o identificador temporal único.
- Número de ficha hospitalaria opcional y único para vincular cada paciente con su registro institucional.
- Registro opcional de nombre informado y edad estimada al crear pacientes NN.
- Normalización a mayúsculas y unicidad del número de ficha hospitalaria.
- Revisión de coincidencias potenciales antes de crear una ficha duplicada.
- Hospitalizaciones longitudinales con una sola activa por paciente.
- Asignación y traslado entre camas con ubicación actual e historial completo.
- Identificación posterior y conciliación no destructiva de fichas provisorias.
- Comparación explícita de ficha NN e histórica antes de conciliar un RUT existente.
- Resolución por jefatura de ingresos activos duplicados mediante cierre administrativo,
  distinto del alta médica y con conservación íntegra del historial.
- Mapa visual de camas por servicio y sala, con estados libre y ocupada.
- Selección inicial y restauración del último servicio activo asignado al nutricionista.
- Posicionamiento espacial mediante CSS Grid, incluyendo camas sin posición y conflictos.
- Panel operacional mínimo de solo lectura, sin consultas adicionales ni datos personales innecesarios.
- Actualización manual y automática del mapa cada 45 segundos, sensible a la visibilidad.
- Cambios directos de cama dentro del mismo servicio sin crear una solicitud.
- Traslados directos atómicos entre servicios con cama coordinada.
- Bandeja de recepción por servicio, aceptación con o sin cama y terminales historizados.
- Sincronización de mapa y bandeja, privacidad operacional y cobertura/apoyo trazable.
- Cancelación automática de traslados abiertos al terminar una hospitalización.

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

Los seeds incluyen servicios, salas, camas y pacientes ficticios, ingresos activos e
históricos, una hospitalización sin cama y las asignaciones habituales del nutricionista
demo a Medicina y UCI. También incluyen traslados ficticios pendiente de recepción,
pendiente de cama, directo completado, rechazado, devuelto y cancelado. No contienen
información clínica real.

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
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts_verify_phase7.ps1
```

En Linux/macOS:

```bash
./scripts_verify_phase7.sh
```

El verificador ejecuta pruebas backend y frontend, build, contrato OpenAPI, metadata,
cadena de migraciones, detección de conflictos y validación de Compose cuando Docker
está disponible.

## Alcance

Fase 7 incluye identidad, RBAC, auditoría, infraestructura hospitalaria, pacientes,
hospitalizaciones, ubicación actual, mapa de camas y traslados directos o mediante
bandeja de recepción.
Evaluaciones nutricionales, diagnósticos, requerimientos, prescripciones, regímenes,
raciones, etiquetas y otros datos clínico-nutricionales permanecen fuera de alcance.
