# ADR-003: Política de soft delete y cuándo aplicarlo

- **Estado**: Aprobado
- **Fecha**: 2026-05-25

## Decisión
Se aplicará **soft delete** en catálogos y entidades administrativas; en datos clínicos se privilegiará inactivación/versionado y nunca borrado físico operativo.

## Aplicar soft delete en
- Usuarios (si se deshabilitan)
- Catálogos: alimentos, preparaciones, regímenes base, modificadores, exámenes
- Estructura hospitalaria: servicios/salas/ubicaciones asistenciales (si salen de uso)

## No aplicar delete destructivo en
- hospitalizaciones
- visitas clínicas
- evaluaciones
- prescripciones emitidas
- resultados de laboratorio
- controles de ingesta
- hoja horaria y resumen 24h
- traslados/movimientos

## Regla operacional
- Eliminación real solo por procedimientos excepcionales (corrección de carga errónea grave) mediante proceso auditado y restringido a administrador.
