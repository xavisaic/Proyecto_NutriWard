# Fase 4: usuarios, roles y asignaciones habituales

- **Fecha de implementación**: 2026-07-28
- **Estado**: Implementada

## Entidades reutilizadas

La fase completa las entidades existentes `users`, `roles`, `user_roles` y
`nutritionist_service_assignments`; no recrea tablas ni introduce entidades clínicas.
También reutiliza `services` para validar la cobertura habitual y `audit_logs` para la
trazabilidad transversal.

La única ampliación de esquema agrega `is_active` y `updated_at` a `user_roles`, junto con
índices de estado. Esto permite retirar y reasignar roles sin borrar el vínculo histórico.
Los UUID, timestamps UTC, claves foráneas y restricciones únicas existentes se conservan.

## Permisos

| Capacidad | administrador | jefatura | nutricionista | alimentacion |
| --- | --- | --- | --- | --- |
| Listar usuarios, roles y asignaciones | Sí | Sí | No | No |
| Consultar detalle de usuario | Sí | Sí | No | No |
| Crear, editar o inactivar usuarios | Sí | No | No | No |
| Asignar o retirar roles | Sí | No | No | No |
| Crear, editar o inactivar asignaciones | Sí | No | No | No |

Todas las lecturas requieren sesión autenticada. Todas las mutaciones requieren además el
encabezado `X-CSRF-Token`.

## Endpoints

- `GET|POST /api/v1/users`
- `GET|PATCH|DELETE /api/v1/users/{user_id}`
- `GET|POST /api/v1/users/{user_id}/roles`
- `DELETE /api/v1/users/{user_id}/roles/{role_id}`
- `GET /api/v1/users/{user_id}/service-assignments`
- `GET /api/v1/roles`
- `GET /api/v1/roles/{role_id}/users`
- `GET|POST /api/v1/nutritionist-service-assignments`
- `PATCH|DELETE /api/v1/nutritionist-service-assignments/{assignment_id}`

`DELETE` representa inactivación lógica en usuarios, roles asignados y coberturas; no elimina
filas físicamente.

## Reglas de negocio

1. Se conservan los roles oficiales `administrador`, `nutricionista`, `jefatura` y
   `alimentacion`.
2. Un usuario activo puede tener múltiples roles, sin vínculos activos duplicados.
3. Retirar un rol inactiva `user_roles`; reasignarlo reactiva el mismo registro histórico.
4. Solo un usuario activo con rol `nutricionista` puede recibir coberturas habituales.
5. El servicio debe existir y estar activo.
6. Un nutricionista puede tener múltiples servicios habituales, sin duplicar el par
   nutricionista/servicio.
7. Inactivar un usuario o retirar su rol nutricionista inactiva sus coberturas activas.
8. La cobertura es habitual y no exclusiva; no restringe futuras intervenciones en otros
   servicios.

## Auditoría

Se registran actor, entidad, acción, timestamp UTC y estados anterior/posterior para:

- creación, actualización e inactivación de usuarios;
- asignación y retiro de roles;
- creación, actualización, reactivación e inactivación de coberturas habituales.

## Seeds

El seed mantiene los cuatro usuarios y roles demo. El nutricionista demo queda asignado
habitualmente a Medicina y UCI. Las ejecuciones repetidas reusan o reactivan registros sin
crear duplicados.

## Ejecución y verificación

```powershell
cd apps/backend
alembic upgrade head
python -m app.db.seed
python -m app.db.seed
python -m pytest

cd ../frontend
npm test
npm run build
```

Con Docker:

```powershell
docker compose -f infra/docker-compose.yml --env-file infra/.env.example up --build
```

El health check permanece en `GET /api/v1/health`. Pacientes, hospitalizaciones, módulos
clínicos, agenda de turnos y cobertura automática continúan fuera de alcance.
