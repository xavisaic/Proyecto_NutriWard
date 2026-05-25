# ADR-006: Política de fuente de verdad para raciones durante traslados

- **Estado**: Aprobado
- **Fecha**: 2026-05-25

## Decisión
La fuente de verdad operativa para raciones será la **ubicación activa efectiva** de la hospitalización en combinación con estado de traslado.

## Regla operativa
- Mientras traslado esté en `solicitado` o `pendiente_recepcion`: ración sigue en servicio origen.
- En `aceptado` sin cama: visible en bandeja destino, **sin duplicar consolidado**.
- En `asignado_cama`: ración pasa al servicio destino.
- Estados terminales (`rechazado`, `devuelto`, `cancelado`): se conserva lógica previa sin duplicación.

## Consecuencia
Se evita contabilización doble en consolidados de central de alimentación.
