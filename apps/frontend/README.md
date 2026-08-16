# Frontend (Fase 9.4)

La navegación principal está gobernada por URL. `/patients` muestra el listado y
`/patients/:patient_id/:tab?admission_id=...` abre la ficha sin duplicar `AppShell`.
Resumen, Evolución nutricional, Evaluación, Prescripción, Minutas e ingesta, Exámenes,
Movimientos e Historial son funcionales. Evolución nutricional ofrece evaluación inicial,
seguimiento rápido y acción específica. Estos dos últimos flujos abren sólo los módulos
seleccionados. Balance nitrogenado, Hoja horaria y Bitácora continúan como placeholders.

Administrador no ve pestañas ni resumen nutricional. Alimentación no accede a la ficha.
La línea de tiempo muestra qué cambió en cada evolución. Evaluación, Prescripción, Ingesta
y Exámenes permiten iniciar actualizaciones directamente. El editor guarda borradores sólo
mediante acción explícita, advierte cambios sin guardar, confirma antes de finalizar,
permite cancelar borradores y muestra conflictos de versión.

La pestaña **Diagnósticos y antecedentes** permite pegar listas, convertirlas en hasta 100
filas revisables, asignar fuente y estados comunes, ajustar CIE-10/tipo/presencia al ingreso
por fila y actualizar estados con trazabilidad. Los antecedentes son longitudinales; los
diagnósticos pertenecen al episodio. Resumen muestra los registros activos.

La misma pestaña incorpora **Historia del episodio actual**, un editor amplio para pegar o
redactar varios párrafos sobre los acontecimientos previos a la hospitalización. Registra
fuente y fecha de inicio opcional; cada actualización exige motivo y conserva las versiones
anteriores. No crea diagnósticos automáticamente, advierte cambios sin guardar y queda en
solo lectura al revisar un episodio histórico.

En la misma pestaña, **Alergias e intolerancias** permite pegado masivo con revisión por
fila, categoría, tipo, criticidad, verificación, múltiples reacciones e historial. También
distingue explícitamente entre “sin alergias conocidas”, “información no disponible” y
“aún no revisado”. Alimentación no abre la ficha: el panel de una cama ocupada presenta
únicamente la alerta alimentaria mínima necesaria para preparar una dieta segura.

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
