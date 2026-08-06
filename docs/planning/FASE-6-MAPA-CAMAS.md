# Fase 6 — Mapa visual de camas

## Objetivo

Fase 6 incorpora una vista espacial, operacional y de solo lectura del estado actual de
las camas. Permite reconocer camas libres y ocupadas, la identidad mínima del paciente y
su hospitalización activa, sin convertir el mapa en una ficha clínica ni habilitar cambios
de ubicación.

## Arquitectura

El backend expone `GET /api/v1/bed-map?service_id={uuid}`. El endpoint reutiliza
`services`, `rooms`, `care_units`, `care_unit_layout_positions`,
`patient_location_history`, `admissions` y `patients`; no agrega tablas ni modelos de
persistencia. Las revisiones 0.6.1 y 0.6.2 incorporan migraciones técnicas sobre
`patients.hospital_identifier`: lo convierten en único cuando no es nulo y lo normalizan
a mayúsculas. No agregan tablas ni modelos clínicos al mapa.

La lectura tiene un número fijo de consultas:

1. valida que el servicio exista y esté activo;
2. obtiene sus salas activas, incluso las que no tienen camas;
3. obtiene en un join todas las camas activas, posiciones y ocupaciones vigentes.

El frontend obtiene el catálogo mediante
`GET /api/v1/hospital/structure?include_inactive=false` y filtra salas localmente sobre
el mapa ya recibido. Para un nutricionista consulta además
`GET /api/v1/nutritionist-service-assignments/me`, que sólo expone sus propias
asignaciones activas. Al entrar selecciona el último servicio asignado elegido durante
la sesión; si no existe, el primer servicio asignado activo por `code` y `name`; y como
respaldo, el primer servicio activo. Las asignaciones se señalan visualmente en el selector.

La preferencia se guarda en `sessionStorage` con una clave por UUID de usuario. Así se
restaura al volver desde otro módulo, no se comparte entre cuentas y desaparece al cerrar
la sesión del navegador. Un servicio no asignado puede consultarse si los permisos
generales lo permiten, pero no reemplaza la preferencia asignada del nutricionista.

## Contrato del endpoint

La consulta requiere sesión, no requiere CSRF y exige `service_id` como UUID. Un UUID
desconocido o correspondiente a un servicio inactivo responde `404 Not Found`.

La consulta de asignaciones propias también requiere sesión y rol `nutricionista`, no
requiere CSRF y nunca permite indicar el UUID de otro usuario. `alimentacion` conserva
`403 Forbidden` sobre este catálogo y sobre los endpoints administrativos de asignaciones.

```json
{
  "generated_at": "2026-08-01T15:30:00Z",
  "service": { "id": "uuid", "code": "MED", "name": "Medicina" },
  "rooms": [
    {
      "id": "uuid",
      "code": "SALA-A",
      "name": "Sala A",
      "floor": "2",
      "beds": [
        {
          "id": "uuid",
          "code": "02",
          "label": "Cama 02",
          "status": "occupied",
          "layout": { "grid_x": 2, "grid_y": 0, "width": 1, "height": 1 },
          "occupancy": {
            "patient": {
              "id": "uuid",
              "display_name": "Nombre Apellido",
              "identity_status": "identified",
              "age_years": 26,
              "age_is_estimated": false
            },
            "admission": {
              "id": "uuid",
              "admission_identifier": "ADM-20260801-ABC123",
              "status": "active",
              "admitted_at": "2026-08-01T10:00:00Z"
            }
          }
        }
      ]
    }
  ]
}
```

`status` sólo admite `free` y `occupied`. El paciente no expone RUT, teléfono, fecha de
nacimiento, identificador hospitalario, observaciones, datos clínicos, nutricionales,
historiales ni auditoría. La edad se calcula al consultar y nunca se persiste.

El nombre de presentación usa nombres y apellidos disponibles para personas identificadas
o provisorias. Sin nombre, un paciente provisorio se presenta como
`Paciente provisorio · {temporary_identifier}`. Un paciente NN sin nombre se presenta como
`Paciente NN · {temporary_identifier}`; si tiene un nombre informado aún no confirmado,
se presenta como `{nombre disponible} · {temporary_identifier}` y conserva el estado NN.

Al crear un paciente NN se puede ingresar una edad estimada entre 0 y 130 años. La edad no
se persiste: el backend la convierte en una fecha de nacimiento estimada usando la fecha de
creación como referencia y mantiene `date_of_birth_is_estimated = true`.

El número de ficha hospitalaria es opcional pero único entre todos los pacientes. La
migración falla de forma explícita si encuentra duplicados preexistentes, incluyendo
valores que sólo difieren por mayúsculas, evitando decidir automáticamente qué registro
debe conservar el número.

## Reglas de ocupación

Una cama se considera ocupada únicamente cuando existe una fila vigente de
`patient_location_history` (`ended_at IS NULL`) y su hospitalización asociada tiene
`status = active`. Una ubicación histórica o una ubicación vinculada a una
hospitalización terminada no ocupa la cama para este mapa.

Sólo se incluyen servicios, salas y camas activas, y únicamente `care_units` de tipo
`bed`. Las salas se ordenan por `code`, `name`; las camas posicionadas por `grid_y`,
`grid_x`, `code`; y las no posicionadas se ubican al final por `code`.

## Representación espacial

Cada sala es un contexto espacial independiente. CSS Grid convierte `grid_x` y `grid_y`
de base cero a filas y columnas de base uno, y aplica `width` y `height` como spans. En
pantallas estrechas se conserva la geometría mediante desplazamiento horizontal.

Los estados incluyen texto, icono y borde además del color. Las camas se pueden enfocar y
activar con teclado. Una cama ocupada abre un panel lateral de solo lectura que usa
exclusivamente el payload del mapa; cerrarlo restaura el foco en la cama. Una cama libre
no abre panel ni genera consultas.

## Camas sin posición

Ninguna cama activa se oculta por carecer de layout. Cada sala muestra después de su grid
la sección **Sin posición configurada**, ordenada por código y con las mismas reglas de
estado y apertura de panel.

## Superposiciones

El frontend compara los rectángulos definidos por `grid_x`, `grid_y`, `width` y `height`
dentro de cada sala. Todas las camas involucradas en una intersección salen del grid y se
muestran en **Posición conflictiva**. La advertencia dirige a Estructura hospitalaria; el
mapa no corrige ni persiste coordenadas automáticamente.

## Actualización periódica

El botón **Actualizar** permite refresco manual. Además, el módulo refresca cada 45
segundos, pausa las consultas cuando la pestaña no es visible y actualiza inmediatamente
al recuperar visibilidad. Durante una consulta en segundo plano conserva el último mapa,
muestra un indicador sutil y, ante error, presenta una advertencia con reintento.

Cada cambio rápido de servicio aborta la solicitud anterior y usa una secuencia para
descartar respuestas obsoletas. Si una actualización libera la cama cuyo panel está
abierto, el panel se cierra y se muestra un aviso no bloqueante.

## Permisos y exposición operacional limitada

Pueden consultar el mapa `administrador`, `jefatura`, `nutricionista` y `alimentacion`.
La estructura mínima es idéntica para todos. El acceso de `alimentacion` responde a una
necesidad operacional futura de raciones, pero no amplía sus permisos generales:

- `GET /api/v1/patients` continúa en `403`;
- `GET /api/v1/patients/{patient_id}` continúa en `403`;
- `GET /api/v1/admissions/active` continúa en `403`;
- `GET /api/v1/admissions/{admission_id}` continúa en `403`.

El módulo Pacientes permanece oculto para ese rol.

## Régimen y etiquetas

`Régimen: No disponible en esta fase` es únicamente texto de interfaz. No existe un campo
de régimen en el contrato, tabla, modelo o schema. La fase no genera raciones ni etiquetas
y no se acopla a Zebra Designer; ese dominio tendrá su propio modelo y endpoint.

## Alcance y fuera de alcance

Incluye lectura espacial, estados libre/ocupada, panel operacional mínimo, filtros,
refresco periódico, tratamiento visible de layouts ausentes o conflictivos, privacidad y
RBAC.

Quedan fuera drag and drop, asignación y traslado, edición de posiciones, término de
hospitalizaciones, estados adicionales de cama, WebSockets, notificaciones push,
prescripciones, evaluaciones, diagnósticos, requerimientos, raciones, etiquetas y toda
información clínica adicional.
