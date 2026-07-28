# ADR-012: Mantenimiento de la estructura hospitalaria

- **Estado**: Aprobado
- **Fecha**: 2026-07-27

## Decisión

La información de servicios, salas, ubicaciones asistenciales y posiciones visuales podrá modificarse
después de su creación. Jefatura y administrador podrán editarla; la eliminación
física excepcional quedará restringida al administrador.

Toda creación, modificación, cambio de estado o eliminación deberá exigir una
sesión válida, protección CSRF y registro de auditoría con actor, fecha y estados
anterior y posterior.

## Edición

- Servicio: código, nombre y descripción.
- Sala: servicio al que pertenece, código, nombre y piso o sector.
- Ubicación asistencial: sala a la que pertenece, código, etiqueta y tipo.
- Posición visual: fila, columna, ancho y alto.

Los cambios deberán respetar la unicidad de códigos, los padres activos y las
dependencias existentes.

## Código de ubicación

El sistema sugerirá automáticamente el siguiente código disponible dentro de la
sala o sector y permitirá reemplazarlo antes de guardar cuando exista una codificación
institucional.

- Si la sala utiliza códigos numéricos (`01`, `02`), se sugerirá el número
  consecutivo (`03`).
- Si utiliza el formato `C01`, `C02`, se sugerirá `C03`.
- Si todavía no tiene ubicaciones, se sugerirá `C01`.
- Los códigos de ubicaciones inactivas se consideran ocupados y no se reutilizan.
- El UUID continúa siendo el identificador técnico interno.

## Inactivación y eliminación

La inactivación es el mecanismo operacional normal. Un elemento inactivo deja de
estar disponible para nuevas operaciones, conserva su historial y puede
reactivarse.

La eliminación física:

- solo estará disponible para administrador;
- exigirá que el elemento esté inactivo;
- exigirá un motivo de al menos diez caracteres;
- se bloqueará si existen hijos, asignaciones u otras dependencias;
- conservará en auditoría una instantánea previa y el motivo;
- se utilizará únicamente para corregir registros creados por error.

Cuando se incorporen pacientes, hospitalizaciones y movimientos, sus referencias
deberán añadirse a las validaciones de dependencia antes de habilitar la
eliminación de cualquier elemento utilizado clínicamente.

## Consecuencias

- La estructura puede adaptarse a cambios reales del hospital.
- Se reduce la carga manual mediante códigos sugeridos.
- No se reutilizan identidades operativas históricas.
- La eliminación destructiva queda limitada, justificada y trazable.
