# ADR-010: Política de roles y cobertura entre nutricionistas

- **Estado**: Aprobado
- **Fecha**: 2026-05-25

## Decisión
Se aplicará RBAC con cobertura clínica flexible:
- Roles controlan capacidades.
- Asignaciones de servicio orientan operación habitual.
- Cobertura fuera de servicio permitido con trazabilidad obligatoria.

## Roles base MVP
- nutricionista
- jefatura
- alimentacion
- administrador

## Regla de cobertura
Un nutricionista puede intervenir en pacientes fuera de su servicio habitual sin bloqueo rígido; el sistema marcará la acción como `cobertura/apoyo` con usuario, fecha/hora y servicio intervenido.

## Beneficio
Mantiene continuidad asistencial real del hospital sin perder gobernanza ni trazabilidad.
