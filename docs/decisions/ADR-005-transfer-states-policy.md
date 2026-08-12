# ADR-005: Política de estados de traslado y bandeja de recepción

- **Estado**: Aprobado
- **Fecha**: 2026-05-25
- **Actualizado**: 2026-08-12 (Fase 7)

## Decisión

Los valores persistidos y expuestos por API son nombres canónicos en inglés:

- `requested`
- `pending_reception`
- `accepted`
- `pending_bed`
- `assigned_to_bed`
- `rejected`
- `returned`
- `cancelled`

Las etiquetas en español son sólo presentación y nunca se persisten. Toda transición
registra estado anterior y posterior, actor, timestamp UTC, motivo u observación,
secuencia incremental e indicador de cobertura cuando corresponda.

## Máquina de estados

- Bandeja: `requested → pending_reception`.
- Aceptación sin cama: `pending_reception → accepted → pending_bed`.
- Aceptación con cama: `pending_reception → accepted → assigned_to_bed`.
- Asignación posterior: `pending_bed → assigned_to_bed`.
- Directo coordinado: `requested → pending_reception → accepted → assigned_to_bed`.
- `rejected` sólo nace de `pending_reception`; `returned`, de `pending_bed`.
- `cancelled` nace de `pending_reception` o `pending_bed`, o automáticamente al
  terminar la hospitalización.
- `assigned_to_bed` es terminal. Regresar requiere una solicitud nueva.

Los hitos automáticos quedan en historial aunque compartan timestamp, ordenados por
`sequence_number`. No existe un `PATCH` genérico de estado.
