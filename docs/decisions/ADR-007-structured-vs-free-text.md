# ADR-007: Política de datos estructurados vs texto libre

- **Estado**: Aprobado
- **Fecha**: 2026-05-25

## Decisión
Campos clínicos críticos serán estructurados por defecto; texto libre será complementario.

## Estructurado obligatorio
- vía de alimentación
- soporte nutricional
- régimen base y modificadores
- parámetros numéricos (peso, talla, IMC, diuresis, HGT, etc.)
- estados de flujo operativo (traslado, evaluación, cobertura)

## Texto libre permitido
- observación clínica
- justificación de ajustes
- observación para central
- notas evolutivas narrativas

## Regla de diseño
No almacenar información analíticamente crítica solo en texto libre.
