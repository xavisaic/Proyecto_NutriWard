# ADR-001: Uso de UUID como identificador principal

- **Estado**: Aprobado
- **Fecha**: 2026-05-25
- **Contexto**: La plataforma tendrá múltiples entidades clínicas y operativas, con integración futura a otros sistemas hospitalarios.

## Decisión
Se usará `UUID` como llave primaria en todas las entidades de dominio del sistema (usuarios, pacientes, hospitalizaciones, registros clínicos, movimientos, etc.).

## Justificación
- Reduce riesgo de colisión al generar IDs en distintos entornos.
- Facilita sincronización y exportación entre sistemas heterogéneos.
- Evita exposición de volumen/orden de registros por IDs secuenciales.
- Permite operaciones offline/future-proof para cargas diferidas.

## Consecuencias
- Índices ligeramente más pesados que enteros secuenciales.
- Necesidad de estandarizar serialización UUID en API y frontend.

## Implementación
- PostgreSQL: tipo `uuid`.
- Backend: `uuid.UUID` en modelos y esquemas.
- Generación por defecto: UUID v4.
