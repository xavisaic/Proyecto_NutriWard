# ADR-004: Política de auditoría transversal

- **Estado**: Aprobado
- **Fecha**: 2026-05-25

## Decisión
Se implementa auditoría transversal en entidades críticas con doble nivel:

1. **Metadatos por fila**: `created_by`, `updated_by`, timestamps.
2. **Bitácora de eventos** (`audit_logs`): inserción/actualización/cambio de estado relevante.

## Qué se audita obligatoriamente
- login/logout
- cambios de rol/permisos
- cambios de ubicación del paciente
- estados de traslado y recepción
- emisión/modificación de prescripción
- cambios en raciones consolidadas
- generación de reportes de contingencia

## Contenido mínimo de `audit_logs`
- actor (`user_id`)
- tipo de entidad y `entity_id`
- acción
- timestamp UTC
- snapshot mínimo antes/después o diff estructurado
- contexto clínico (`admission_id` si aplica)
