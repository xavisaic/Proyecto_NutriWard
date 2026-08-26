# Backend (Fase 9.8)

La ficha conserva las proyecciones administrativas de Fase 8 y agrega una API clínica
separada, autorizada sólo para `nutricionista` y `jefatura`:

- `GET /api/v1/patients/{patient_id}/chart-summary`
- `GET /api/v1/admissions/{admission_id}/operational-timeline`
- `GET|POST /api/v1/admissions/{admission_id}/nutrition-care-encounters`
- `GET|PATCH /api/v1/nutrition-care-encounters/{encounter_id}`
- `POST /api/v1/nutrition-care-encounters/{encounter_id}/finalize|correct|cancel`
- `GET /api/v1/admissions/{admission_id}/nutrition-latest`
- `GET /api/v1/admissions/{admission_id}/nutrition-assessments|nutrition-prescriptions|nutrition-intake|nutrition-labs`
- `GET /api/v1/admissions/{admission_id}/clinical-context`
- `POST|PATCH /api/v1/admissions/{admission_id}/clinical-history`
- `POST /api/v1/patients/{patient_id}/conditions`
- `POST /api/v1/admissions/{admission_id}/diagnoses`
- `PATCH /api/v1/patient-conditions/{condition_id}/status`
- `PATCH /api/v1/admission-diagnoses/{diagnosis_id}/status`
- `GET|POST /api/v1/admissions/{admission_id}/allergy-intolerances`
- `PATCH /api/v1/allergy-intolerances/{allergy_id}/status`
- `POST /api/v1/allergy-intolerances/{allergy_id}/reactions`
- `POST /api/v1/admissions/{admission_id}/allergy-review-assertions`
- `GET /api/v1/admissions/{admission_id}/food-safety-allergies`
- `GET /api/v1/admissions/{admission_id}/nutrition-prescription-workspace`
- `POST /api/v1/admissions/{admission_id}/nutrition-prescription-orders`
- `PATCH /api/v1/nutrition-prescription-orders/{order_id}`
- `POST /api/v1/nutrition-prescription-orders/{order_id}/validate|activate|suspend|clone`
- `POST /api/v1/enteral-formula-catalog`
- `PUT /api/v1/nutrition-prescription-settings`

La API clínica no expone `audit_logs`, exige CSRF en mutaciones y bloquea administrador y
Alimentación con `403`. La única excepción es la proyección de seguridad alimentaria de
solo lectura: Alimentación puede consultar sustancia, tipo, criticidad y manifestaciones
alimentarias activas, sin fuentes, notas, actores ni alergias farmacológicas. La cabeza
Alembic es `20260817_0014`; el modelo se documenta en
`docs/planning/FASE-9-FICHA-NUTRICIONAL-CLINICA.md`,
`docs/planning/FASE-9.8-PRESCRIPCION-NUTRICIONAL.md`,
`docs/planning/FASE-9.3-EVOLUCION-NUTRICIONAL-MODULAR.md` y
`docs/planning/FASE-9.4-HISTORIA-EPISODIO-ACTUAL.md`. Los protocolos de antropometría
avanzada se detallan en `docs/planning/FASE-9.5-ANTROPOMETRIA-AVANZADA.md`.
El formulario y algoritmo NRS-2002 guiado se documentan en
`docs/planning/FASE-9.6-NRS-2002-GUIADO.md`.

La historia del episodio actual es una narrativa exclusiva de la hospitalización. Cada
actualización inserta una versión clínica inmutable con fuente, fecha, autor y motivo; la
auditoría técnica conserva sólo identificadores y números de versión, nunca el contenido.

La evaluación inicial exige población, tamizaje y PES antes de finalizar. Seguimientos,
reevaluaciones y acciones específicas requieren contexto y síntesis, pero pueden publicar
un subconjunto de módulos. `nutrition-latest` resuelve cada dato vigente desde la evolución
finalizada más reciente que realmente lo modificó, evitando que un control parcial oculte
una prescripción, un PES o un tamizaje previo.

Las mediciones avanzadas se guardan por sesión con protocolo, dispositivo, condiciones,
valores originales y resultados derivados. El backend calcula el máximo de tres intentos
por mano y bilateral, y la media de tres lecturas por cada pliegue más la sumatoria de los
cuatro sitios. Las salidas BIA son informadas por el equipo y no se interpretan ni
recalculan automáticamente.

NRS-2002 `espen-nrs2002-v2` recibe respuestas clínicas estructuradas y calcula en backend
el mayor de los criterios de pérdida de peso, ingesta e IMC con deterioro. Luego suma la
gravedad confirmada y el punto por edad. Una fecha de nacimiento exacta prevalece sobre el
valor enviado; un tamizaje incompleto puede persistir en borrador, pero no finalizarse.

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
- `POST /api/v1/transfer-requests`
- `GET /api/v1/transfer-requests/reception-tray`
- `GET /api/v1/transfer-requests/{transfer_request_id}`
- `GET /api/v1/admissions/{admission_id}/transfer-requests`
- `POST /api/v1/transfer-requests/{transfer_request_id}/accept`
- `POST /api/v1/transfer-requests/{transfer_request_id}/assign-bed`
- `POST /api/v1/transfer-requests/{transfer_request_id}/reject|return|cancel`

## Tablas de aplicación

`users`, `roles`, `user_roles`, `audit_logs`, `nutritionist_service_assignments`,
`services`, `rooms`, `care_units`, `care_unit_layout_positions`, `patients`,
`admissions`, `admission_status_history`, `patient_location_history`,
`patient_transfer_requests` y `patient_transfer_request_status_history`.

Las lecturas operacionales de traslados admiten los cuatro roles. Sólo `jefatura` y
`nutricionista` pueden mutar; `administrador` y `alimentacion` son de sólo lectura.
Cada transición conserva actor, UTC, secuencia, motivo u observación cuando se informa,
cobertura y `admission_id` en auditoría. La ubicación vigente es la única fuente de
ocupación. El motivo inicial es opcional; rechazo, devolución y cancelación sí exigen
motivo.

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
