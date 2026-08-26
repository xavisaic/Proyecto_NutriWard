# ADR-015: conciliación terapéutica para análisis nutricional

- **Estado**: Aprobado
- **Fecha**: 2026-08-19

## Decisión

La pestaña **Tratamientos activos** registra una conciliación manual de indicaciones
relevantes para nutrición, vinculada a `admission_id`. No es una receta electrónica ni una
fuente oficial de administración.

Cada tratamiento tiene una identidad estable y versiones clínicas inmutables. Actualizar
dosis, velocidad, estado, fuente o verificación inserta una versión nueva mediante
concurrencia optimista; no existe `DELETE`. La lista diferencia el estado de la orden de la
verificación de la transcripción y distingue una lista no revisada de una conciliación sin
hallazgos.

Los aportes energéticos informados desde la receta se muestran como
**prescritos/potenciales**. Sólo una futura integración con registros de administración u
Hoja horaria podrá producir un aporte efectivamente recibido.

Las reglas de impacto nutricional son informativas, explicables y no pueden indicar por sí
solas iniciar, suspender o modificar un tratamiento.

La captura de medicamentos se vincula a una instantánea versionada del arsenal
institucional. Se conserva tanto el código canónico como el texto pegado por el usuario.
La búsqueda puede filtrar disponibilidad hospitalizada/ambulatoria; el pegado selecciona
automáticamente sólo coincidencias exactas y obliga a resolver ambigüedades. Velocidad,
duración, volumen estimado y volumen informado son campos distintos; la estimación no se
presenta como administración oficial.

## Consecuencias

- los tratamientos no pertenecen a una evolución nutricional particular, aunque ésta pueda
  referenciarlos en una fase posterior;
- `nutricionista` y `jefatura` conservan la frontera clínica vigente;
- administrador y Alimentación no reciben tratamientos ni impactos farmacológicos;
- dispositivos, accesos y directivas de cuidado requieren entidades separadas;
- una futura integración debe mapear orden, declaración conciliada y administración como
  conceptos distintos.
