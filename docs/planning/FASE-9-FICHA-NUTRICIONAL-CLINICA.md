# Fase 9: ficha nutricional clínica estructurada

## Resultado y límites del dominio

La ficha nutricional se implementa como información clínica sensible vinculada siempre a
`admission_id`. El modelo separa:

1. `patients`: identidad longitudinal y demografía;
2. `admissions`: episodio clínico;
3. `nutritional_care_encounters`: instancia temporal de trabajo nutricional;
4. evaluación, contexto, antropometría, tamizaje y requerimientos;
5. diagnósticos PES y prescripción;
6. seguimiento, ingesta, exámenes y alertas;
7. `audit_logs`: trazabilidad técnica mínima, nunca contenido de la ficha.

Una atención describe su propósito (`initial_assessment`, `follow_up`, `reassessment`,
`discharge_planning`, `other`). No persiste presencia física, modalidad presencial/remota
ni ubicación del profesional. La Bitácora sigue reservada para continuidad y pendientes
operacionales; no reemplaza documentación clínica.

No hay copia automática entre hospitalizaciones. Cada fila clínica contiene
`admission_id` y `encounter_id`; un episodio terminado es de sólo lectura. La aplicación
puede mostrar historia de episodios previos, pero reutilizarla requerirá una acción y
confirmación profesional explícitas en una fase futura.

## Borradores, finalización, corrección y cancelación

- Crear una atención es una acción explícita y produce `draft` versión 1.
- Sólo su autor o `jefatura` puede modificar el borrador.
- Cada `PATCH` exige la versión vigente y la incrementa. Una versión obsoleta responde
  `409`.
- Finalizar exige episodio activo, motivo, fuente, síntesis, población, tamizaje y al
  menos un diagnóstico PES. Los errores se localizan por sección y responden `422`.
- `finalized` y `corrected` son inmutables. Una corrección crea un nuevo borrador con
  `corrected_encounter_id` y motivo; el original no cambia.
- Cancelar conserva fila, actor, fecha, versión y motivo. No existe `DELETE` clínico.
- Auditoría guarda acción, actor, entidad, episodio, estado y versión; nunca el cuerpo
  clínico completo.

## Modelo de datos

La migración `20260813_0010` parte de `20260812_0009` y crea:

- `nutritional_care_encounters`;
- `nutritional_assessments`;
- `nutritional_clinical_context_items`;
- `nutritional_anthropometric_measurements`;
- `nutritional_screenings` y `nutritional_screening_answers`;
- `nutritional_requirement_calculations`;
- `nutritional_diagnoses`;
- `nutritional_prescriptions` y `nutritional_prescription_meal_times`;
- `nutritional_monitoring_records`;
- `nutritional_intake_records`;
- `nutritional_lab_observations`;
- `nutritional_alerts`.

Los valores clínicos numéricos usan `NUMERIC/Decimal`; porcentajes y estados tienen
restricciones; fechas clínicas conservan zona horaria; las tablas se indexan por episodio,
atención y fecha/estado. JSON se limita a snapshots versionados de entradas de algoritmos,
no reemplaza campos consultables.

Los seeds existentes permanecen idempotentes y no agregan evaluaciones, diagnósticos,
prescripciones ni pacientes clínicos de Fase 9.

## Poblaciones y antropometría

Cada evaluación declara `adult`, `pediatric`, `neonatal` o `pregnancy`. Cambiar la
población adapta el editor sin borrar otros campos. Las mediciones distinguen peso actual
medido/informado, habitual, seco, ideal, ajustado, objetivo, pregestacional, al nacer,
neonatal mínimo y de cálculo, además de tallas y perímetros. Cada una conserva unidad,
fecha, método, fuente, confiabilidad, naturaleza y autor.

El backend calcula IMC únicamente cuando encuentra peso actual en kg y talla en cm/m.
También calcula porcentaje de cambio respecto del peso habitual cuando ambos pesos están
disponibles. El resultado calculado y un eventual valor manual se separan; un ajuste manual
requiere motivo. Elegir peso ideal o ajustado nunca es automático.

Las curvas OMS/MINSAL quedan registrables con código y versión, pero esta fase no calcula
puntajes Z ni percentiles: no se incorporó todavía una biblioteca/dataset oficial local
versionado con casos de referencia. Neonatología y embarazo tampoco reciben una
clasificación automática de crecimiento o ganancia gestacional.

## Tamizajes clínicos

La aplicación congela `tool_code`, versión de herramienta, versión del algoritmo,
respuestas, puntajes por componente, total, clasificación, fecha y autor. Un cambio futuro
de algoritmo no recalcula registros históricos.

### NRS-2002

Implementación `espen-nrs2002-v1` para adultos hospitalizados:

- acepta las cuatro respuestas de tamizaje inicial;
- si todas son negativas, conserva total 0 y `initial_screen_negative`;
- cuando corresponde tamizaje final, suma estado nutricional 0–3, gravedad de enfermedad
  0–3 y un punto por edad mayor o igual a 70 años;
- total mayor o igual a 3 clasifica `nutritional_risk`.

El frontend no puede enviar el total como autoridad. Los criterios clínicos que producen
cada componente deben ser elegidos y documentados por el profesional; NutriWard no asigna
gravedad por diagnóstico.

### STRONGkids

Implementación `strongkids-original-v1`:

- evaluación clínica subjetiva: 1;
- enfermedad de alto riesgo: 2;
- ingesta/pérdidas: 1;
- pérdida o mala ganancia de peso: 1;
- 0 bajo, 1–3 medio y 4–5 alto.

El valor predeterminado es NRS-2002 para adulto, STRONGkids para pediatría y `none` con
motivo para neonatología y embarazo. Es un valor inicial de interfaz, no una decisión
automática irreversible: el profesional puede elegir otra herramienta configurada.

## Requerimientos

El método general inicial es factorial y persiste resultado basal, factores de actividad,
estrés y térmico, ecuación visible, entradas congeladas, redondeo y resultado adoptado.
Los factores nunca se infieren desde diagnósticos. Se soportan kcal/kg, Mifflin-St Jeor,
Harris-Benedict revisada, Schofield adulto, calorimetría, manual y otro documentado.

Los métodos factorial, kcal/kg y ecuaciones adultas se bloquean para pediatría,
neonatología y embarazo. En esas poblaciones se ofrece cálculo manual razonado o valor
medido mientras no exista un método local validado. Un ajuste del resultado automático
requiere justificación. El cálculo no genera una prescripción automática.

## PES, prescripción, ingesta y exámenes

Cada PES conserva por separado problema, etiología, signos/síntomas, prioridad y estado;
el backend genera «[Problema] relacionado con [Etiología], evidenciado por [Signos y
síntomas]». No se incluye un catálogo eNCPT licenciado.

La prescripción es independiente del cálculo y admite vía, vigencia, objetivos, régimen,
textura, restricciones, alergias consideradas, suplementos, soporte y detalle por tiempo
de comida. La futura fuente clínica de raciones será la última prescripción finalizada,
vigente y no reemplazada de la hospitalización activa. Un borrador o episodio terminado
nunca alimentará producción; Alimentación no recibe esta proyección en Fase 9.

Ingesta conserva fecha, tiempo, porcentaje/cantidades, unidad, motivo, fuente y autor.
«Minutas e ingesta» informa que minutas, raciones y cocina siguen pendientes. Los exámenes
son transcripción manual; cuando la fuente es `trakcare_manual` la interfaz muestra
«Dato transcrito manualmente desde TrakCare». No hay integración, interpretación crítica
ni recomendación farmacológica.

## API y proyecciones

Mutaciones y lecturas clínicas requieren `nutricionista` o `jefatura`; las mutaciones
además exigen CSRF. `administrador` y `alimentacion` reciben `403` y el frontend no hace
llamadas clínicas para ellos.

- `GET|POST /api/v1/admissions/{admission_id}/nutrition-care-encounters`
- `GET|PATCH /api/v1/nutrition-care-encounters/{encounter_id}`
- `POST /api/v1/nutrition-care-encounters/{encounter_id}/finalize|correct|cancel`
- `GET /api/v1/admissions/{admission_id}/nutrition-latest`
- `GET /api/v1/admissions/{admission_id}/nutrition-assessments`
- `GET /api/v1/admissions/{admission_id}/nutrition-prescriptions`
- `GET /api/v1/admissions/{admission_id}/nutrition-intake`
- `GET /api/v1/admissions/{admission_id}/nutrition-labs`
- `GET /api/v1/nutrition-catalogs`

`nutrition-latest` sólo usa atenciones finalizadas/correctivas y permanece separado del
`chart-summary` administrativo de Fase 8. Las proyecciones tienen orden determinista y
paginación. Los borradores ajenos no aparecen en la lista de un nutricionista; jefatura
puede administrarlos según política.

## Interfaz y estados

Atenciones es el flujo de edición. El diálogo tiene diez secciones, progreso, navegación
por teclado, unidades visibles, errores por sección, guardado explícito, confirmación de
finalización, advertencia `beforeunload` y confirmación al cerrar con cambios. Evaluación,
Prescripción, Minutas e ingesta, Exámenes y la tarjeta de Resumen son proyecciones de la
misma atención. Balance nitrogenado, Hoja horaria y Bitácora siguen como placeholders.

Se contemplan carga, vacío, error/reintento, `403`, `404`, `409`, episodio histórico y
cambios sin guardar. Las solicitudes usan secuencia para descartar respuestas obsoletas al
cambiar rápidamente de hospitalización. Se reutilizan MUI, componentes compartidos y
tokens de tema claro/oscuro; no se introducen colores clínicos literales.

## Decisiones clínicas y referencias

Fecha de consulta: 13 de agosto de 2026.

| Fuente y versión | Población | Implementación/prueba | Limitaciones |
|---|---|---|---|
| ESPEN, NRS-2002; Kondrup et al., 2003, DOI 10.1016/S0261-5614(02)00214-5 | Adultos hospitalizados | Componentes 0–3, edad ≥70, umbral ≥3; pruebas 0 y 3 | El profesional asigna componentes; no se infieren por diagnóstico |
| Hulst et al., STRONGkids original, Clin Nutr 2010, DOI 10.1016/j.clnu.2009.07.006 | Pediatría hospitalizada | Pesos 1/2/1/1 y límites 0, 1–3, 4–5 | No se aplica automáticamente a neonatos |
| OMS Child Growth Standards 2006 y referencia 5–19 años 2007 | 0–19 años | Sólo código/versión de referencia | Sin Z/percentiles hasta cargar dataset oficial local validado |
| MINSAL, evaluación infantil y patrones de crecimiento | Niñez/adolescencia en Chile | Referencia documentada | Sin puntos de corte inventados |
| MINSAL, nutrición y alimentación de la gestante (documento 2019 indicado) | Embarazo | Referencia configurable | Sin valores automáticos de ganancia hasta confirmar normativa vigente institucional |
| Mifflin et al. 1990; Roza y Shizgal 1984; Schofield 1985 | Adultos según variables/rango | Casos algebraicos y límites de entradas | No se ofrecen como universales |
| Academy of Nutrition and Dietetics, Nutrition Care Process/PES | Atención nutricional | Campos P/E/S y frase generada | Sin terminología eNCPT licenciada |

Referencias directas:

- https://www.espen.org/documents/Screening.pdf
- https://pubmed.ncbi.nlm.nih.gov/19682776/
- https://pubmed.ncbi.nlm.nih.gov/32371986/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC9432264/
- https://www.who.int/tools/child-growth-standards
- https://www.who.int/tools/growth-reference-data-for-5to19-years
- https://www.minsal.cl/wp-content/uploads/2021/12/Cap%C3%ADtulo-2-Web.pdf
- https://diprece.minsal.cl/patrones-de-crecimiento-para-la-evaluacion-nutricion-de-ninos-ninas-y-adolescentes-desde-el-nacimiento-a-19-anos-2/
- https://diprece.minsal.cl/wp-content/uploads/2019/06/2019.05.27-VC-Nutrici%C3%B3n-y-alimentaci%C3%B3n-gestante.pdf
- https://www.eatrightpro.org/practice/nutrition-care-process/ncp-overview/nutrition-diagnosis

## Privacidad y fuera de alcance

No se registran cuerpos clínicos en auditoría ni logs, no se exponen `audit_logs`, y la API
usa nombres de presentación. Permanecen fuera de alcance: integración TrakCare/HL7/FHIR,
curvas calculadas, raciones, cocina, minutas operacionales, etiquetas/Zebra, inventario,
insulina o farmacología, formulación enteral/parenteral avanzada, bombas, balance
nitrogenado, hoja horaria completa, Bitácora, WebSockets, push y firma electrónica legal.
