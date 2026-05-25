# ADR-009: Política de reglas de agregación para resumen 24 h

- **Estado**: Aprobado
- **Fecha**: 2026-05-25

## Decisión
Cada variable de hoja horaria tendrá tipo de agregación explícito persistido y trazable.

## Tipos de agregación
- `sum`
- `avg`
- `min`
- `max`
- `last`
- `mode` (predominante)

## Reglas iniciales
- volúmenes y aportes (NE/NP/propofol/dextrosa/diuresis): `sum`
- HGT: `min`, `max`, `avg`, `last`
- insulina: `sum` (si unidad compatible)
- Bristol: `mode`
- deposiciones: cantidad `sum`, patrón Bristol `mode`

## Implementación
`daily_24h_summaries` almacenará resultados calculados y metadatos de regla aplicada por métrica.
