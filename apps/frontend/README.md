# Frontend (Fase 8)

La navegación principal está gobernada por URL. `/patients` muestra el listado y
`/patients/:patient_id/:tab?admission_id=...` abre la ficha sin duplicar `AppShell`.
Resumen, Movimientos e Historial son funcionales; las demás pestañas son placeholders
sin llamadas API.

## Ejecución local

```bash
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## Verificación

```bash
npm test
npm run build
```

La pantalla principal muestra servicios, salas, ubicaciones asistenciales tipadas, posiciones
y contadores. Los roles
`jefatura` y `administrador` pueden crear e inactivar elementos; los roles operacionales
tienen acceso de consulta.

El módulo Administración ofrece las vistas `Usuarios y roles` y `Asignaciones de
servicios`. Jefatura dispone de consulta; administrador puede crear y editar usuarios,
asignar o retirar roles y agregar o inactivar coberturas habituales.
