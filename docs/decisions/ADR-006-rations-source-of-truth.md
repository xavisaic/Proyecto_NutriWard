# ADR-006: Fuente de verdad futura para raciones durante traslados

- **Estado**: Aprobado
- **Fecha**: 2026-05-25
- **Aclarado**: 2026-08-12 (Fase 7; raciones aún fuera de alcance)

## Decisión

La futura fuente operacional de raciones será la ubicación vigente de la
hospitalización. Una solicitud en bandeja no crea una segunda ubicación.

- En `pending_reception` o `pending_bed`, la ubicación y futura fuente continúan en
  el servicio origen. La bandeja destino no debe duplicar al paciente en consolidados.
- Al llegar a `assigned_to_bed`, la ubicación efectiva y futura fuente cambian al
  servicio destino.
- `rejected`, `returned` y `cancelled` conservan ubicación y fuente en origen.
- El traslado directo cambia la fuente al destino al completarse atómicamente.

## Consecuencia

La recepción anticipa trabajo sin contabilización doble. Fase 7 documenta esta regla,
pero no implementa raciones, regímenes, prescripciones, consolidados ni etiquetas.
