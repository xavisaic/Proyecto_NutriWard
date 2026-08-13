# Fase 8: ficha del paciente con pestañas

## Resultado

La ficha longitudinal utiliza rutas propias y mantiene separados:

- la identidad del paciente (`patient_id`);
- la hospitalización o episodio (`admission_id`);
- los movimientos operacionales;
- los futuros documentos clínico-nutricionales.

No se agregaron tablas ni migraciones. La cabeza Alembic continúa siendo
`20260812_0009`.

## Rutas

- `/patients`: listado y búsqueda.
- `/patients/:patient_id`: normaliza a `summary`.
- `/patients/:patient_id/:tab`: ficha y pestaña.
- `?admission_id={uuid}`: episodio seleccionado.
- `?return_to={ruta}`: retorno opcional al listado preservado.

Pestañas canónicas: `summary`, `care`, `assessment`, `prescription`, `intake`,
`labs`, `nitrogen-balance`, `hourly-sheet`, `logbook`, `movements` y `history`.
Una pestaña desconocida se normaliza a `summary`. El episodio activo se selecciona
por defecto; si no existe, se selecciona el más reciente y la URL se normaliza con
`replace`.

## Contratos backend

### `GET /api/v1/patients/{patient_id}/chart-summary`

Proyecta identidad, edad estructurada, episodios, ubicación actual o última histórica,
traslado abierto y cinco movimientos recientes. Rechaza con `404` un `admission_id`
ajeno al paciente. No devuelve placeholders ni datos clínicos ficticios.

La edad usa días bajo 28 días, meses bajo dos años y años posteriormente. Para cada
episodio también se entrega la edad al ingreso; los futuros documentos clínicos deberán
guardar su propio snapshot a la fecha del documento.

### `GET /api/v1/admissions/{admission_id}/operational-timeline`

Construye una proyección paginada desde:

- `admission_status_history`;
- `patient_location_history`;
- `patient_transfer_requests`;
- `patient_transfer_request_status_history`.

No persiste un timeline, no lee `audit_logs` y no expone usuarios, snapshots o JSON
técnico. Los identificadores y el orden son deterministas.

## Episodios históricos

Un episodio terminado muestra `Episodio histórico · Solo lectura`. Su última ubicación
se conserva con `is_current=false`. Las pestañas futuras reciben el episodio ya validado
y deben bloquear mutaciones históricas.

## Atenciones, evaluación y Bitácora

Una futura **atención** será un agrupador temporal de trabajo nutricional. Podrá reunir
evaluaciones, cambios de prescripción, revisiones de ingesta o notas relacionadas. No
implica presencia física y no registra modalidad presencial/remota.

Una **evaluación** será un documento clínico estructurado, firmado y versionado. La
pestaña ya recibe `patient_id`, `admission_id`, el estado histórico y los permisos desde
el contenedor de la ficha, lo que permite implementar Fase 9 sin rehacer el router.

La **Bitácora** se reserva para continuidad profesional, coordinación, pendientes e
incidencias operacionales. No reemplaza evaluación, diagnóstico, prescripción, ingesta,
movimientos ni auditoría técnica.

## Permisos y privacidad

- Nutricionista y jefatura: todas las pestañas.
- Administrador: Resumen, Movimientos e Historial; sin pestañas clínicas.
- Alimentación: sin acceso a la ficha ni a sus endpoints.
- Fichas fusionadas: aviso y enlace explícito a la ficha canónica, sin redirección
  silenciosa.

Los módulos operacionales sólo muestran `Abrir ficha completa` a roles que ya tienen
acceso. El backend aplica la autorización aunque se escriba la URL manualmente.

## Preparación para Fase 9

La pestaña Evaluación puede reemplazar su placeholder por un componente real sin tocar
el router, AppShell, selector de episodios o cabecera. Los errores de cada pestaña se
mantienen dentro de la ficha y el timeline sólo se carga al entrar en Movimientos.

## Fuera de alcance

No se implementaron atenciones, evaluaciones, diagnósticos, cálculos, prescripciones,
regímenes, minutas, ingesta, exámenes, balance nitrogenado, hoja horaria, Bitácora,
TrakCare, raciones, etiquetas, WebSockets ni notificaciones push.
