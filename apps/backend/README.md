# Backend (Fase 3)

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
- `GET /api/v1/hospital/structure`
- `POST|PATCH /api/v1/hospital/services`
- `POST|PATCH /api/v1/hospital/rooms`
- `POST|PATCH /api/v1/hospital/care-units`
- `PUT /api/v1/hospital/care-units/{care_unit_id}/layout`
- `DELETE /api/v1/hospital/services/{service_id}` (sólo administrador)
- `DELETE /api/v1/hospital/rooms/{room_id}` (sólo administrador)
- `DELETE /api/v1/hospital/care-units/{care_unit_id}` (sólo administrador)

Las mutaciones hospitalarias requieren rol `jefatura` o `administrador` y token CSRF.
La inactivación se realiza con `PATCH {"is_active": false}`; no existe borrado físico
operativo para estas entidades.
