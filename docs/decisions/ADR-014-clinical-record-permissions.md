# ADR-014: permisos y privacidad de la ficha nutricional clínica

## Decisión

La ficha nutricional de Fase 9 es un recurso clínico distinto del resumen administrativo.
Sólo `nutricionista` y `jefatura` pueden leer endpoints `nutrition-*`; ambos pueden crear y
finalizar, el autor controla su borrador y jefatura puede administrarlo. Administrador y
Alimentación reciben `403` y su frontend no inicia solicitudes clínicas.

Los borradores de otros nutricionistas no aparecen en el listado habitual. Los registros
finalizados del equipo sí son legibles. Un episodio terminado bloquea cualquier mutación.
Las correcciones crean una nueva versión enlazada y nunca reemplazan silenciosamente el
documento original.

La auditoría técnica sólo registra acción, actor, entidad, estado, versión y
`admission_id`; no conserva el cuerpo clínico. `chart-summary` no incorpora datos
nutricionales porque administrador puede consultarlo. `nutrition-latest` es la proyección
clínica autorizada.

## Consecuencias

- Ocultar controles en React no es una frontera de seguridad; el backend valida cada ruta.
- Alimentación conserva acceso operacional al mapa/bandeja, pero no recibe diagnósticos,
  alergias, exámenes, prescripciones ni observaciones.
- Un futuro rol clínico de sólo lectura puede incorporarse ampliando `CLINICAL_ROLES` sin
  concederlo a las dependencias de mutación.

## Extensión Fase 9.1

La misma frontera protege diagnósticos médicos y antecedentes mórbidos. `nutricionista` y
`jefatura` pueden crear registros y cambiar libremente su estado clínico o verificación,
siempre con fuente, motivo, actor, fecha y versión. No existe borrado: los errores se
marcan `entered_in_error`. La auditoría técnica no duplica nombres ni notas clínicas.
