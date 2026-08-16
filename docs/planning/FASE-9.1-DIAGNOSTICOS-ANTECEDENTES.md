# Fase 9.1: diagnósticos médicos y antecedentes mórbidos

## Decisión de dominio

NutriWard separa dos alcances que no deben persistirse como un único texto narrativo:

- `patient_conditions`: antecedentes mórbidos longitudinales del paciente, reutilizados en
  hospitalizaciones futuras;
- `admission_diagnoses`: diagnósticos médicos del episodio seleccionado, sin copia
  automática a otros ingresos.

Los diagnósticos médicos son independientes de los diagnósticos nutricionales PES. El
campo narrativo de una evaluación nutricional puede resumir contexto, pero no es la fuente
de verdad para estados, fechas ni historial.

Desde Fase 9.4 existe además una **Historia del episodio actual** vinculada a la
hospitalización. Conserva el relato cronológico como narrativa versionada, pero no sustituye
ni genera automáticamente diagnósticos o antecedentes estructurados.

## Ingreso rápido sin perder estructura

La pestaña **Diagnósticos y antecedentes** permite escribir o pegar hasta 100 elementos
separados por saltos de línea o punto y coma. También limpia viñetas y numeración. El texto
se transforma primero en filas revisables; nunca se almacena como bloque clínico opaco.

Antes de confirmar, el profesional puede:

- corregir o quitar filas;
- aplicar fuente y verificación comunes;
- indicar CIE-10 opcional por fila;
- clasificar cada diagnóstico como principal, secundario o complicación;
- indicar por fila si estaba presente al ingreso;
- revisar duplicados dentro del lote y contra registros vigentes.

La operación masiva es transaccional: se guarda el lote completo o no se guarda nada. El
catálogo CIE-10 oficial con autocompletado queda pendiente; la aplicación no inventa ni
asigna automáticamente códigos.

## Estados e historial

El estado clínico y la verificación son dimensiones distintas:

| Recurso | Estado clínico | Verificación |
|---|---|---|
| Diagnóstico del episodio | `active`, `resolved`, `entered_in_error` | `provisional`, `confirmed`, `ruled_out` |
| Antecedente longitudinal | `active`, `inactive`, `remission`, `resolved`, `entered_in_error` | `unconfirmed`, `confirmed`, `refuted` |

`nutricionista` y `jefatura` pueden cambiar libremente ambos estados. Cada cambio exige
fuente y motivo, conserva actor y fecha, incrementa `version` y agrega una fila secuencial
en la tabla de historial. Un registro resuelto puede reactivarse. No existen endpoints
`DELETE`; un registro incorrecto se marca `entered_in_error`.

La concurrencia es optimista. Un `PATCH` con versión obsoleta responde `409`. Los
diagnósticos de una hospitalización terminada son de solo lectura. Al revisar un episodio
histórico, los antecedentes se identifican explícitamente como longitudinales y muestran
su estado actual.

## Fuente y permisos

Las fuentes admitidas son transcripción manual desde TrakCare, ficha clínica, equipo
tratante, paciente, familiar/cuidador u otra. NutriWard registra la procedencia; no afirma
una integración automática con TrakCare.

Sólo `nutricionista` y `jefatura` pueden leer o mutar este módulo. Las mutaciones exigen
CSRF. `administrador` y `alimentacion` reciben `403`, no ven la pestaña ni la tarjeta
clínica de Resumen. La auditoría técnica guarda únicamente estados, versión y metadatos;
los nombres clínicos permanecen en las tablas clínicas.

## Modelo y API

La migración `20260813_0011` parte de `20260813_0010` y crea:

- `patient_conditions`;
- `patient_condition_status_history`;
- `admission_diagnoses`;
- `admission_diagnosis_status_history`.

Endpoints:

- `GET /api/v1/admissions/{admission_id}/clinical-context`;
- `POST /api/v1/patients/{patient_id}/conditions`;
- `POST /api/v1/admissions/{admission_id}/diagnoses`;
- `PATCH /api/v1/patient-conditions/{condition_id}/status`;
- `PATCH /api/v1/admission-diagnoses/{diagnosis_id}/status`.

## Fuera de alcance

Esta fase no implementa conciliación de medicamentos, cirugías, antecedentes
familiares, importación HL7/FHIR, autocompletado CIE-10, validación por rol médico ni
inferencia automática de diagnósticos a partir de texto. Las alergias e intolerancias se
incorporan separadamente en la Fase 9.2.
