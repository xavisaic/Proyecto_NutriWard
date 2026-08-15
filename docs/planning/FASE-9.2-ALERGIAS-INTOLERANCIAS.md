# Fase 9.2: alergias, intolerancias y seguridad alimentaria

## Decisión de dominio

Las alergias e intolerancias son registros longitudinales del paciente y no diagnósticos
del episodio. La hospitalización donde se documentaron se conserva como procedencia, pero
el estado actual acompaña al paciente en ingresos futuros. El modelo sigue las dimensiones
principales de HL7 FHIR `AllergyIntolerance`: categoría, tipo, estado clínico, verificación,
criticidad y reacciones repetibles.

Referencias normativas consultadas:

- [HL7 FHIR AllergyIntolerance](https://hl7.org/fhir/allergyintolerance.html)
- [Definiciones de AllergyIntolerance](https://fhir.hl7.org/fhir/allergyintolerance-definitions.html)
- [FHIR R4 y aserciones negadas](https://www.hl7.org/fhir/r4/allergyintolerance.html#negated)

## Ingreso y revisión clínica

La tercera sección de **Diagnósticos y antecedentes** permite pegar hasta 100 sustancias
separadas por línea o punto y coma. Antes de guardar, cada fila puede corregirse y clasificar:

- categoría: alimento, medicamento, ambiental, biológico u otro;
- tipo: alergia, intolerancia o no determinado;
- criticidad: baja, alta o no evaluada;
- verificación: no confirmada, presunta o confirmada;
- manifestación y gravedad inicial opcionales.

Cada registro admite múltiples reacciones posteriores. No se asignan automáticamente
códigos ni se infiere el tipo a partir del nombre pegado.

La revisión se registra incluso sin hallazgos. NutriWard diferencia:

- no consultado;
- información no disponible;
- sin alergias/intolerancias conocidas;
- revisado con hallazgos.

Una declaración “sin conocidas” se rechaza con `409` si existen registros activos en la
categoría revisada. El estado más reciente del ingreso evita que ausencia de datos sea
interpretada como ausencia de riesgo.

## Estado, reacciones y trazabilidad

El estado clínico puede ser `active`, `inactive` o `resolved`; la verificación puede ser
`unconfirmed`, `presumed`, `confirmed`, `refuted` o `entered_in_error`. Cada cambio exige
fuente y motivo, usa versión optimista y agrega historial secuencial. Un registro ingresado
por error conserva trazabilidad, queda sin estado clínico y no se elimina físicamente.

Las reacciones almacenan manifestación, gravedad, fecha, vía y nota. La auditoría técnica
registra sólo acción, entidad, estados y versión; no duplica sustancia, manifestación ni nota.

## Permisos y proyección para Alimentación

`nutricionista` y `jefatura` pueden leer y mutar el módulo completo; las mutaciones exigen
CSRF y una hospitalización terminada es de solo lectura. `administrador` y `alimentacion`
reciben `403` en la ficha clínica.

Por autorización operacional expresa, `alimentacion` puede leer exclusivamente:

`GET /api/v1/admissions/{admission_id}/food-safety-allergies`

La proyección contiene sólo alergias/intolerancias alimentarias activas no refutadas:
sustancia, tipo, criticidad y manifestación/gravedad. No expone medicamentos, otras
categorías, fuentes, notas, códigos, actores, fechas ni historial. El panel vive en el mapa
de camas y advierte si la información no fue revisada o no está disponible.

## Modelo y API

La migración `20260815_0012` parte de `20260813_0011` y crea:

- `patient_allergy_intolerances`;
- `allergy_intolerance_reactions`;
- `allergy_intolerance_status_history`;
- `patient_allergy_review_assertions`.

Además de la proyección operacional, la API clínica expone creación masiva, consulta del
contexto longitudinal, actualización de estado, adición de reacciones y aserciones de
revisión. No existen endpoints `DELETE`.

## Fuera de alcance

Quedan fuera conciliación farmacológica, terminologías SNOMED CT/RxNorm, importación FHIR,
alertas cruzadas con prescripción médica, reglas automáticas de cocina y sustitución de
ingredientes. La proyección actual informa el riesgo; no decide una preparación.
