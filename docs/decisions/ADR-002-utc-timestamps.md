# ADR-002: Uso de timestamps UTC

- **Estado**: Aprobado
- **Fecha**: 2026-05-25

## Decisión
Todos los timestamps persistidos se guardarán en UTC.

## Alcance
- `created_at`, `updated_at`, `deleted_at`
- fechas clínicas con marca horaria (`recorded_at`, `occurred_at`, `requested_at`, etc.)
- auditoría y exportaciones

## Justificación
- Evita ambigüedad por horario de verano o configuración local.
- Consistencia para auditoría legal y trazabilidad clínica.
- Simplifica integraciones futuras y analítica temporal.

## Reglas
- Base de datos: `timestamptz`.
- API: ISO 8601 en UTC.
- Frontend: render en zona local del usuario cuando corresponda, sin alterar almacenamiento base.
