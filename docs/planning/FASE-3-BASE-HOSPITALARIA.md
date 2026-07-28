# Fase 3: base hospitalaria

- **Fecha de implementación**: 2026-07-27
- **Estado**: Implementada

## Objetivo

Representar la estructura física y organizacional mínima del hospital, reutilizando la
identidad, RBAC, CSRF y auditoría construidos en Fase 2.

## Modelo

```text
services 1 ── N rooms 1 ── N care_units 1 ── 0..1 care_unit_layout_positions
    │
    └── N nutritionist_service_assignments
```

Todas las entidades de dominio utilizan UUID y timestamps UTC. Servicios, salas y ubicaciones
se inactivan mediante soft delete. Las salas conservan observaciones administrativas
provenientes de la fuente institucional.

## Reglas implementadas

1. Código y nombre de servicio son únicos.
2. El código de sala es único dentro de un servicio.
3. El código de ubicación es único dentro de una sala.
4. Cada ubicación se clasifica como cama, camilla, puesto o box.
5. No se crean ni reactivan hijos activos bajo un padre inactivo.
6. Un servicio con salas activas no puede inactivarse.
7. Una sala con ubicaciones activas no puede inactivarse.
8. Las coordenadas de ubicación son enteros no negativos.
9. Todos los roles autenticados pueden consultar la estructura.
10. Sólo jefatura y administrador pueden modificarla.
11. Toda mutación requiere CSRF y genera un evento de auditoría.
12. Los códigos de ubicación se sugieren automáticamente y pueden editarse antes de guardar.
12. Sólo administrador puede eliminar definitivamente registros inactivos sin dependencias.
13. Toda eliminación definitiva exige un motivo y conserva una instantánea en auditoría.

## API

- `GET /api/v1/hospital/structure?include_inactive=false`
- `POST /api/v1/hospital/services`
- `PATCH /api/v1/hospital/services/{service_id}`
- `POST /api/v1/hospital/rooms`
- `PATCH /api/v1/hospital/rooms/{room_id}`
- `POST /api/v1/hospital/care-units`
- `PATCH /api/v1/hospital/care-units/{care_unit_id}`
- `PUT /api/v1/hospital/care-units/{care_unit_id}/layout`
- `DELETE /api/v1/hospital/services/{service_id}`
- `DELETE /api/v1/hospital/rooms/{room_id}`
- `DELETE /api/v1/hospital/care-units/{care_unit_id}`

## Seeds ficticios

- Servicios: Medicina, Unidad de Cuidados Intensivos, Unidad de Tratamiento Intermedio y Cirugía.
- Cinco salas.
- Diez ubicaciones de tipo cama con posición visual.
- Asignación del nutricionista demo al servicio Medicina.

## Importación institucional

La carga de estructura dispone de un importador Excel transaccional e idempotente. Valida el
esquema, la cantidad declarada contra los códigos enumerados, los tipos admitidos y registra el
nombre y checksum de la fuente en auditoría. La importación no elimina registros ausentes del
archivo.

## Criterios de cierre

- Migración Alembic encadenada desde Fase 2.
- Metadata contiene las nueve tablas esperadas.
- Backend y frontend cuentan con pruebas automatizadas.
- Build de producción exitoso.
- Contrato OpenAPI contiene todos los endpoints hospitalarios.
- Documentación y scripts de verificación disponibles.

## Fuera de alcance

Pacientes, hospitalizaciones, movimientos clínicos, evaluaciones, prescripciones, raciones
y reportes clínicos permanecen fuera de Fase 3.
