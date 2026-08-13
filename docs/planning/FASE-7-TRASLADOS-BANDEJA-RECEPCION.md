# Fase 7: traslados y bandeja de recepción

## Objetivo y modalidades

Fase 7 mueve una hospitalización sin cambiar su `admission_id` y conserva íntegro
`patient_location_history`.

1. Un cambio de cama dentro del mismo servicio reutiliza
   `POST /api/v1/admissions/{admission_id}/location` y no crea solicitud.
2. Un traslado directo entre servicios crea la solicitud y completa los hitos
   `requested → pending_reception → accepted → assigned_to_bed` en una transacción.
3. Un envío a bandeja termina inicialmente en `pending_reception`. El destino puede
   rechazar, aceptar pendiente de cama o aceptar y asignar inmediatamente.

## Ubicación e integridad

Mientras una solicitud está en `pending_reception` o `pending_bed`, el paciente sigue
en la cama vigente del origen. `origin_care_unit_id` es una fotografía de la cama al
solicitar; la ubicación efectiva siempre se resuelve desde `patient_location_history`.
Por eso un cambio interno de cama en origen mantiene la solicitud abierta y la bandeja
muestra la cama nueva.

La asignación destino bloquea hospitalización, solicitud, ubicación vigente y cama;
revalida estado y disponibilidad; cierra la ubicación de origen y crea la nueva antes
del commit. Los índices parciales impiden dos ubicaciones vigentes, dos ocupantes en
una cama y dos traslados abiertos por hospitalización. Conflictos concurrentes se
traducen a HTTP 409 sin cambios parciales.

Terminar como `discharged`, `deceased` o `closed` cancela cualquier traslado abierto
en la misma transacción, incluida la conciliación administrativa de duplicados.

## API y estados

La API ofrece creación, bandeja por servicio, detalle con historial, historial por
hospitalización y comandos explícitos `accept`, `assign-bed`, `reject`, `return` y
`cancel`. No existe actualización genérica de estado. Las secuencias automáticas se
ordenan por `sequence_number`, aun con timestamps iguales.

El motivo de la solicitud es opcional tanto en traslados directos como en envíos a
bandeja. Si se informa, se normaliza y conserva en la solicitud y su primer evento.

Los estados terminales son `assigned_to_bed`, `rejected`, `returned` y `cancelled`.
Rechazar requiere `pending_reception`; devolver requiere `pending_bed`; cancelar admite
ambos estados pendientes. Todos los motivos terminales son obligatorios.

## Permisos, cobertura y privacidad

`administrador`, `jefatura`, `nutricionista` y `alimentacion` leen bandeja, detalle e
historial operacional. Sólo `jefatura` y `nutricionista` mutan, con sesión, CSRF, actor
y auditoría. `administrador` y `alimentacion` tienen interfaz de sólo lectura.

Un nutricionista sin jefatura puede apoyar fuera de sus servicios habituales; el
evento conserva el servicio de actuación y marca `is_coverage`. La bandeja sólo expone
UUID, nombre de presentación, estado de identidad, edad e indicador de edad estimada,
además de resúmenes operacionales. No expone RUT, teléfono, fecha de nacimiento,
historia clínica, nutrición ni auditoría interna.

## Interfaz y sincronización

La bandeja está dentro de Mapa de camas y sigue el servicio seleccionado. Separa
pendientes de recepción de aceptados pendientes de cama, muestra contador y acciones
según rol. “Mover paciente” es compartido entre Pacientes y el panel de una cama.

En el mapa de origen, una cama cuyo paciente tiene un traslado abierto muestra una
franja violeta y un distintivo textual con el servicio destino. El texto diferencia
`Traslado solicitado` (`pending_reception`) de `Aceptado · espera cama`
(`pending_bed`) e indica el tiempo transcurrido. El distintivo desaparece cuando se
asigna la cama destino o la solicitud termina sin traslado.

Mapa y bandeja refrescan cada 45 segundos sólo con la pestaña visible, actualizan al
recuperar visibilidad y después de mutaciones, conservan el último dato válido ante
errores y descartan respuestas obsoletas al cambiar de servicio. No hay WebSockets.

## Estructura, seeds y fuera de alcance

No puede inactivarse una cama ocupada ni un servicio con traslados abiertos. Servicios
y camas referenciados por historial no se purgan. Los seeds ficticios e idempotentes
incluyen los seis resultados operacionales requeridos.

Si una hospitalización usada por un seed abierto fue terminada entre ejecuciones, el
seed conserva y cancela esa solicitud con historial y auditoría, cierra cualquier
ubicación vigente inconsistente y crea un reemplazo ficticio exclusivo con
hospitalización activa y cama. Nunca reactiva ni sobrescribe hospitalizaciones o
fichas modificadas por el usuario.

Quedan fuera: tránsito físico sin cama, retornos físicos, traslados externos, reservas,
drag and drop, aseo/mantenimiento, WebSockets, raciones, prescripciones, regímenes,
evaluaciones, diagnósticos, etiquetas y Zebra.
