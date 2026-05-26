# ADR-005: Política de estados de traslado y bandeja de recepción

- **Estado**: Aprobado
- **Fecha**: 2026-05-25

## Decisión
El traslado se modelará como flujo de estados explícitos, con bandeja de recepción por servicio destino.

## Estados oficiales MVP
- `solicitado`
- `pendiente_recepcion`
- `aceptado`
- `pendiente_cama`
- `asignado_cama`
- `rechazado`
- `devuelto`
- `cancelado`

## Reglas
- Toda transición requiere usuario, timestamp y motivo/opcional observación.
- No se permite asignar cama destino sin aceptación previa.
- Al estado `asignado_cama`, se actualiza ubicación actual y se registra historial de movimiento.
- `rechazado`/`devuelto`/`cancelado` no borran solicitud; quedan históricos.
