# Iteración 0: alcance previo a Fase 2

- **Fecha**: 2026-05-25
- **Estado**: Aprobado para iniciar Fase 2

## 1) Lista final de entidades iniciales para Fase 2 y Fase 3

## Fase 2 (Base técnica + autenticación mínima)
- `users`
- `roles`
- `user_roles`
- `nutritionist_service_assignments`
- `audit_logs` (estructura base)

## Fase 3 (Base hospitalaria)
- `services`
- `rooms`
- `beds`
- `bed_layout_positions`

> Nota: entidades clínicas avanzadas quedan fuera de Fase 2/3 y parten desde Fase 4+.

## 2) Alcance exacto de Fase 2

1. Estructura monorepo (`apps/backend`, `apps/frontend`, `docs`, `infra`).
2. Backend FastAPI operativo con:
   - settings por entorno
   - conexión PostgreSQL
   - SQLModel/SQLAlchemy base
   - Alembic configurado
   - módulo auth básico (login/logout simulado o JWT inicial)
   - endpoints base: `/health`, `/auth`, `/users` (mínimos)
3. Frontend React + Vite + TypeScript con:
   - layout inicial
   - router base
   - pantalla login mínima
   - cliente API base
4. Infra local con Docker Compose:
   - PostgreSQL
   - backend
   - frontend
5. Seeds mínimos:
   - roles
   - usuarios demo (nutricionista, jefatura, alimentación, administrador)
6. Documentación inicial:
   - README raíz
   - README backend/frontend
   - variables de entorno
   - comandos de migración y seeds

## 3) Comandos esperados para levantar backend/frontend/base de datos

## Infra completa (Docker Compose)
```bash
docker compose up --build
```

## Solo base de datos
```bash
docker compose up -d db
```

## Backend local
```bash
cd apps/backend
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend local
```bash
cd apps/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## 4) Estructura inicial de archivos a crear en Fase 2

```text
Proyecto_NutriWard/
  apps/
    backend/
      app/
        api/v1/endpoints/
          auth.py
          users.py
          health.py
        core/
          config.py
          security.py
        db/
          session.py
          base.py
          seed.py
        models/
          user.py
          role.py
          user_role.py
          nutritionist_service_assignment.py
          audit_log.py
        schemas/
          auth.py
          user.py
        services/
          auth_service.py
          user_service.py
        main.py
      alembic/
      alembic.ini
      pyproject.toml
      README.md

    frontend/
      src/
        app/
          router.tsx
          providers.tsx
        modules/
          auth/
            LoginPage.tsx
        shared/
          services/api.ts
          components/
        main.tsx
      index.html
      package.json
      vite.config.ts
      README.md

  docs/
    decisions/
      ADR-001-uuid-primary-keys.md
      ADR-002-utc-timestamps.md
      ADR-003-soft-delete-policy.md
      ADR-004-audit-policy.md
      ADR-005-transfer-states-policy.md
      ADR-006-rations-source-of-truth.md
      ADR-007-structured-vs-free-text.md
      ADR-008-non-destructive-clinical-history.md
      ADR-009-24h-aggregation-rules.md
      ADR-010-roles-and-coverage-policy.md
    planning/
      ITERATION-0-BASE-TECNICA.md

  infra/
    docker-compose.yml
    .env.example

  README.md
```
