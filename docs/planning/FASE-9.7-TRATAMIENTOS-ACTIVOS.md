# Fase 9.7: tratamientos activos e impacto nutricional

## Decisión implementada

Incorporar una pestaña **Tratamientos activos** en la ficha del episodio hospitalario. Su
propósito es conciliar y mantener visible la información terapéutica relevante para la
atención nutricional; no prescribe, no modifica la receta médica, no registra la
administración oficial de enfermería y no reemplaza TrakCare/SIDRA.

La pestaña pertenece a `admission_id`, porque un tratamiento corresponde al episodio y
puede cambiar fuera de una evolución nutricional. Una evolución podrá referenciar la
versión de los tratamientos que el profesional utilizó para su análisis, pero no será la
dueña de esos registros.

## Ajustes a la idea original

1. **No confundir prescripción con administración.** La dosis o velocidad indicada permite
   mostrar un aporte energético prescrito o potencial. Sólo un volumen administrado y
   verificado permite llamarlo aporte real. La integración con Hoja horaria deberá mantener
   ambas cifras separadas.
2. **Un tratamiento, varias etiquetas.** Propofol se registra una sola vez y puede tener
   categoría principal `sedation` y etiquetas `non_nutritional_energy` y `lipid_source`.
   Las vistas por categoría son proyecciones y no filas duplicadas.
3. **Separar tipos clínicos.** Medicamentos y soporte nutricional son tratamientos;
   objetivos/controles son directivas de cuidado; sondas, catéteres y ventilación son
   dispositivos. Pueden convivir en la pestaña, pero no en la misma tabla.
4. **Separar estado y verificación.** `active` describe el estado informado por la fuente;
   `verified`, `pending` o `stale` describe cuán reciente y confiable es la transcripción en
   NutriWard. No se debe presentar “sin tratamientos” como equivalente a “verificado sin
   tratamientos”.
5. **No borrar historia.** Toda corrección, modificación de dosis, pausa o suspensión crea
   una versión nueva con actor, fecha y motivo. `entered_in_error` invalida el dato sin
   eliminarlo.

Como referencia semántica, el modelo toma de HL7 FHIR R5 la separación entre
`MedicationRequest` (orden), `MedicationStatement` (información reportada sobre uso) y
`MedicationAdministration` (administración efectiva). NutriWard comienza como una
conciliación manual similar a `MedicationStatement`, conservando campos compatibles con
una futura integración de órdenes.

## Alcance de la primera versión

### Incluido

- registro manual de medicamentos y soporte nutricional relevantes;
- fuente, fecha/hora de verificación y profesional responsable obligatorios;
- nombre, categoría, esquema legible, dosis/concentración, vía, modalidad, frecuencia,
  velocidad, inicio, término previsto, indicación, estado y observación nutricional;
- lista activa filtrable, detalle expandible e historial completo;
- cambio de estado y actualización mediante versiones no destructivas;
- panel de impacto nutricional informativo, explicable y basado en reglas versionadas;
- resumen de tratamientos referenciable desde una evolución nutricional;
- episodio histórico en modo de sólo lectura;
- permisos, concurrencia optimista y auditoría técnica consistentes con la ficha actual.

### Fuera de alcance

- emisión, firma o validación legal de una receta;
- modificación de indicaciones médicas por NutriWard;
- registro oficial de administración de enfermería o control de bombas;
- cálculo de dosis farmacológicas, interacciones o incompatibilidades;
- alertas críticas o recomendaciones automáticas de suspender/progresar terapias;
- OCR como fuente definitiva e integración HL7/FHIR/TrakCare;
- cálculo de “aporte real” a partir de una mera velocidad prescrita.

## Modelo funcional

### Tratamiento estable y versiones

`admission_treatments` mantiene la identidad estable:

- `id`, `admission_id`;
- `kind`: `medication` o `nutritional_support`;
- `created_at`, `created_by`.

`admission_treatment_versions` mantiene el contenido inmutable:

- `treatment_id`, `version`, `previous_version_id`;
- `name`, código normalizado opcional y texto original de la fuente;
- categoría principal y etiquetas de impacto;
- concentración/preparación, dosis actual, vía, modalidad, frecuencia y velocidad;
- inicio, término previsto, indicación y motivo del estado;
- `order_status`: `draft`, `active`, `on_hold`, `ended`, `stopped`, `completed`,
  `cancelled`, `entered_in_error` o `unknown`;
- `source_type`, referencia visible de la fuente y fecha/hora observada;
- `verification_status`, `verified_at`, `verified_by`;
- observación nutricional, motivo del cambio y fecha de creación.

Los valores estructurados deben usar `NUMERIC/Decimal` y una unidad explícita. El texto
original de prescripción se conserva para no perder instrucciones complejas, pero no
reemplaza los campos consultables.

### Entidades separadas para etapas posteriores

- `admission_care_directives`: HGT, metas de PAM/sedación, balance, posición y otros
  controles no farmacológicos;
- `admission_devices`: CVC, línea arterial, catéter urinario, acceso enteral, ostomías,
  drenajes y ventilación;
- `nutritional_encounter_treatment_references`: snapshot de las versiones consideradas al
  finalizar una evolución;
- registros de administración/Hoja horaria: fuente futura del volumen realmente recibido.

No se recomienda guardar reglas farmacológicas dentro de cada paciente. El catálogo de
impacto debe estar versionado en código/configuración institucional y producir mensajes
recalculables, con la regla y datos que originaron cada mensaje.

## Interfaz propuesta

### 1. Encabezado de conciliación

- última verificación global y profesional;
- conteos de activos, pausados y pendientes de verificar;
- advertencia clara cuando la información esté desactualizada o nunca conciliada;
- acción **Agregar tratamiento** sólo en episodios activos.

### 2. Lista de tratamientos

Filtros por soporte nutricional, vasoactivos, sedación/analgesia, antimicrobianos,
metabólicos y otros. La vista resumida muestra nombre, dosis/velocidad actual, vía,
frecuencia, estado, verificación e indicador nutricional. El detalle muestra preparación,
dilución, horarios, fechas, indicación, fuente, observaciones e historial.

El día de antimicrobiano se deriva de la fecha de inicio y duración prevista; no se captura
como un número independiente que pueda quedar obsoleto.

### 3. Impacto nutricional actual

El panel distingue:

- **aporte prescrito/potencial**, cuando sólo existe una indicación;
- **aporte administrado**, únicamente cuando exista una fuente de administración válida;
- **dato faltante**, por ejemplo velocidad o concentración no informada;
- **consideración clínica informativa**, siempre con fundamento visible y sin ordenar una
  conducta.

Los mensajes deben usar lenguaje como “considerar/revisar/verificar”, mostrar su fuente y
permitir que el profesional confirme si se incorpora al análisis nutricional.

### 4. Historial

Una línea de tiempo inferior reúne inicio, cambios de dosis, pausas, reanudaciones,
suspensiones, término y correcciones. En episodios cerrados toda la pestaña es de sólo
lectura.

### 5. Captura asistida por arsenal

El formulario de alta usa un catálogo institucional importado del archivo
`arsenal RESTRICCIONES.xlsx`: 440 presentaciones de la hoja `Hoja1`, con código,
código alternativo, nombre, vía cuando está informada, disponibilidad para farmacia de
hospitalizados o ambulatoria y restricción. La instantánea queda versionada como
`arsenal-2025`; el libro original no se modifica.

Se admiten dos entradas equivalentes:

- búsqueda por nombre o código con disponibilidad y restricciones visibles;
- pegado de hasta 50 líneas, separadas también por viñetas, numeración o punto y coma.

Sólo una coincidencia exacta por código o nombre se selecciona automáticamente. Una
coincidencia aproximada queda como ambigua y exige elección humana; una línea sin resultado
conserva su texto original y también debe resolverse antes de guardar. El alta masiva es
atómica: si existe un duplicado o falla una fila, no se crea ninguna.

La interfaz aplica divulgación progresiva. Para un medicamento estándar solicita sólo la
indicación transcrita. En perfiles intravenosos muestra velocidad en mL/h, duración y
volumen informado. `velocidad × duración` se presenta como **volumen estimado**, separado
del volumen informado, y nunca sustituye la hoja de enfermería ni el control de bombas.

## API implementada

- `GET /api/v1/medication-catalog`: búsqueda y filtro por disponibilidad;
- `POST /api/v1/medication-catalog/match`: conciliación no mutante de líneas pegadas;
- `GET /api/v1/admissions/{admission_id}/treatments`
- `POST /api/v1/admissions/{admission_id}/treatments`
- `POST /api/v1/admissions/{admission_id}/treatments/bulk`: alta atómica de 1 a 50;
- `GET /api/v1/admission-treatments/{treatment_id}`
- `PATCH /api/v1/admission-treatments/{treatment_id}`: crea una versión nueva y exige
  `expected_version` y motivo;
- `GET /api/v1/admission-treatments/{treatment_id}/history`
- `GET /api/v1/admissions/{admission_id}/treatment-impact-summary`

No habrá `DELETE`. Los filtros activos excluyen `ended`, `stopped`, `completed`,
`cancelled` y `entered_in_error`, pero el historial conserva todas las versiones.

## Permisos, seguridad y auditoría

La primera versión conserva la frontera actual: `nutricionista` y `jefatura` pueden leer;
ambos pueden registrar conciliaciones, el autor controla su actualización y jefatura puede
corregirla. `administrador` y `alimentacion` no reciben estos datos. Un episodio terminado
rechaza mutaciones.

La auditoría registra acción, actor, entidad, episodio, versión y cambio de estado, pero no
duplica dosis, indicaciones ni observaciones clínicas. El backend valida pertenencia al
episodio, roles, CSRF y versión esperada.

Antes de incorporar médicos, enfermería o farmacia se deberá definir una matriz de permisos
distinta para ordenar, verificar, administrar y sólo leer; esos verbos no son equivalentes.

## Estado de la entrega incremental

### Corte A: conciliación segura

**Implementado en Fase 9.7.**

Migración, modelos, esquemas, servicio y API; CRUD versionado sin borrado; pestaña con lista,
formulario, filtros, detalle e historial; permisos y pruebas. Este corte ya entrega valor sin
automatización clínica.

### Corte B: impacto nutricional explicable

**Implementado en Fase 9.7.**

Catálogo controlado de categorías y reglas en código, panel informativo, datos faltantes y
resumen energético potencial. Los valores se conservan con unidades y `Decimal`. Congelar
las versiones consideradas por una evolución queda pendiente junto a la integración con
Hoja horaria.

### Corte C: directivas, dispositivos y aporte recibido

**Pendiente para una fase posterior.**

Agregar bloques separados para controles/metas y accesos; integrar posteriormente Hoja
horaria para comparar requerimiento, aporte prescrito y aporte efectivamente recibido.

## Criterios mínimos de aceptación

- un tratamiento nunca puede leerse o modificarse desde otro episodio;
- una actualización concurrente obsoleta responde `409`;
- no existe borrado físico y cada cambio conserva autor, fecha, motivo y versión;
- un episodio histórico y un usuario sin rol clínico reciben la protección esperada;
- la lista diferencia vacío no verificado de conciliación verificada sin tratamientos;
- Propofol aparece una sola vez aunque alimente varias vistas/reglas;
- el catálogo conserva las 440 presentaciones, sus códigos, disponibilidad y restricciones;
- una coincidencia aproximada o múltiple nunca se selecciona sin confirmación humana;
- el alta masiva es atómica y rechaza duplicados dentro de la lista y del episodio;
- velocidad, duración, volumen estimado y volumen informado conservan significados separados;
- la UI no llama “administrado” ni “real” a un valor derivado sólo de la prescripción;
- valores numéricos, pares valor/unidad y redondeo tienen pruebas de borde;
- carga, vacío, error/reintento, `403`, `404`, `409`, modo histórico y cambios sin guardar
  están cubiertos en frontend.

## Criterio adoptado para el MVP

El nutricionista captura los tratamientos relevantes para nutrición, no necesariamente
la receta completa. La interfaz mantiene una categoría abierta controlada para otros casos.
Se adoptó esta opción porque copiar la receta completa eleva mucho el tiempo de conciliación
y acerca el producto a un sistema farmacológico sin garantizar que la lista manual
permanezca actualizada.

## Referencias de interoperabilidad

- HL7 FHIR R5 MedicationRequest: https://hl7.org/fhir/R5/medicationrequest.html
- HL7 FHIR R5 MedicationStatement: https://hl7.org/fhir/R5/medicationstatement.html
- HL7 FHIR R5 MedicationAdministration:
  https://hl7.org/fhir/R5/medicationadministration.html
