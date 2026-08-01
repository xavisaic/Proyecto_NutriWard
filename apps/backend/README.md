# Backend (Fase 5)

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

## Importar estructura desde Excel

```powershell
# Validación y simulación
python -m app.cli.import_hospital_structure "C:\ruta\estructura.xlsx"

# Confirmación
python -m app.cli.import_hospital_structure "C:\ruta\estructura.xlsx" --apply
```

El archivo debe contener las columnas `Servicio`, `Sala o sector`, `Tipo`,
`Camas/puestos`, `Cantidad` y `Observación`. La importación valida las cantidades,
admite cama, camilla, puesto y box, conserva las observaciones y puede repetirse sin
duplicar registros.

## Pruebas

```bash
python -m pytest
```

## Endpoints principales

- `GET /api/v1/health`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `GET /api/v1/users`
- `GET|PATCH|DELETE /api/v1/users/{user_id}`
- `POST /api/v1/users`
- `GET|POST /api/v1/users/{user_id}/roles`
- `DELETE /api/v1/users/{user_id}/roles/{role_id}`
- `GET /api/v1/roles`
- `GET /api/v1/roles/{role_id}/users`
- `GET|POST /api/v1/nutritionist-service-assignments`
- `PATCH|DELETE /api/v1/nutritionist-service-assignments/{assignment_id}`
- `GET /api/v1/hospital/structure`
- `POST|PATCH /api/v1/hospital/services`
- `POST|PATCH /api/v1/hospital/rooms`
- `POST|PATCH /api/v1/hospital/care-units`
- `PUT /api/v1/hospital/care-units/{care_unit_id}/layout`
- `DELETE /api/v1/hospital/services/{service_id}` (sólo administrador)
- `DELETE /api/v1/hospital/rooms/{room_id}` (sólo administrador)
- `DELETE /api/v1/hospital/care-units/{care_unit_id}` (sólo administrador)
- `GET|POST /api/v1/patients`
- `POST /api/v1/patients/unidentified`
- `GET /api/v1/patients/{patient_id}`
- `PATCH /api/v1/patients/{patient_id}/identity`
- `POST /api/v1/patients/{patient_id}/reconcile`
- `GET /api/v1/patients/{patient_id}/admissions`
- `POST /api/v1/admissions`
- `GET /api/v1/admissions/active`
- `GET /api/v1/admissions/{admission_id}`
- `PATCH /api/v1/admissions/{admission_id}/status`
- `GET|POST /api/v1/admissions/{admission_id}/location`
- `GET /api/v1/admissions/{admission_id}/location-history`

## Tablas de aplicación

`users`, `roles`, `user_roles`, `audit_logs`, `nutritionist_service_assignments`,
`services`, `rooms`, `care_units`, `care_unit_layout_positions`, `patients`,
`admissions`, `admission_status_history` y `patient_location_history`.

Las mutaciones hospitalarias requieren rol `jefatura` o `administrador` y token CSRF.
La inactivación se realiza con `PATCH {"is_active": false}`; no existe borrado físico
operativo para estas entidades.

Las lecturas administrativas requieren `jefatura` o `administrador`. Solo
`administrador` puede modificar usuarios, roles y asignaciones habituales, siempre con
CSRF. Los `DELETE` administrativos inactivan registros y conservan su historial.

Las lecturas de pacientes permiten `nutricionista`, `jefatura` o `administrador`.
Las mutaciones clínicas están restringidas a `nutricionista` y `jefatura`;
`administrador` opera en modo de sólo lectura para soporte. `alimentacion` no
tiene acceso a las fichas. Todas las mutaciones requieren CSRF y generan auditoría.
