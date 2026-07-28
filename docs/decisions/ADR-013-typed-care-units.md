# ADR-013: Ubicaciones asistenciales tipadas

- **Estado**: Aprobado
- **Fecha**: 2026-07-28

## Contexto

La estructura real del hospital contiene camas, camillas, puestos y boxes. Aunque todas
estas unidades pueden ubicar temporalmente a una persona, no tienen la misma semántica
clínica ni deben contarse de igual forma en capacidad, ocupación o disponibilidad.

## Decisión

Se reemplaza la entidad específica `beds` por la entidad genérica `care_units`, con un
campo obligatorio `unit_type` limitado al catálogo:

- `bed`: cama.
- `stretcher`: camilla.
- `station`: puesto.
- `box`: box.

Todas comparten sala o sector, código institucional, etiqueta, estado y posición visual.
El código continúa siendo único dentro de su sala.

El tipo describe la infraestructura. No determina por sí mismo si una persona recibe
alimentación; esa decisión dependerá de la hospitalización, permanencia, prescripción y
reglas operacionales que se implementen en fases clínicas.

## Consecuencias

- Los censos futuros podrán distinguir camas hospitalarias de capacidad transitoria.
- La interfaz puede mostrar y filtrar cada tipo correctamente.
- Traslados, ocupación e integraciones dispondrán de una clasificación explícita.
- El Excel institucional puede importarse sin convertir puestos, camillas o boxes en camas.
- Las referencias clínicas futuras deberán apuntar a `care_units`.
