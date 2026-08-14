# Frontend (Fase 9)

La navegación principal está gobernada por URL. `/patients` muestra el listado y
`/patients/:patient_id/:tab?admission_id=...` abre la ficha sin duplicar `AppShell`.
Resumen, Atenciones, Evaluación, Prescripción, Minutas e ingesta, Exámenes, Movimientos e
Historial son funcionales. Atenciones contiene el editor clínico de diez secciones; las
otras pestañas clínicas son proyecciones de atenciones finalizadas. Balance nitrogenado,
Hoja horaria y Bitácora continúan como placeholders.

Administrador no ve pestañas ni resumen nutricional. Alimentación no accede a la ficha.
El editor guarda borradores sólo mediante acción explícita, advierte cambios sin guardar,
confirma la finalización y muestra conflictos de versión.

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
