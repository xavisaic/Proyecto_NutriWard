# ADR-008: Política de historial clínico no destructivo

- **Estado**: Aprobado
- **Fecha**: 2026-05-25

## Decisión
Los registros clínicos longitudinales no se sobrescriben destructivamente; se crean nuevas entradas o versiones.

## Aplica a
- visitas clínicas
- evaluaciones nutricionales
- diagnósticos y evoluciones
- prescripciones
- controles de ingesta
- resultados de laboratorio
- cálculos de balance nitrogenado
- hoja horaria y resumen 24h
- eventos de bitácora

## Regla
- Corrección de error: marcar registro como corregido/inactivo y crear nuevo registro vinculado.
- Mantener trazabilidad del autor y motivo de corrección.
