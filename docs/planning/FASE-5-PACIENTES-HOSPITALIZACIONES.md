# Fase 5: pacientes, hospitalizaciones y ubicación actual

## Resultado

La fase incorpora una ficha longitudinal de paciente separada de sus episodios
hospitalarios. Admite pacientes identificados, provisorios y NN sin inventar RUT,
mantiene una única hospitalización activa por paciente y conserva cada cambio de
estado y ubicación como historial inmutable.

Quedan fuera de esta fase las evaluaciones nutricionales, diagnósticos,
requerimientos, prescripciones, raciones y demás registros clínico-nutricionales.

## Modelo de datos

Tablas nuevas:

- `patients`: identidad, identificador temporal, datos administrativos y estado de fusión.
- `admissions`: episodios hospitalarios independientes y reingresos.
- `admission_status_history`: transición inicial y cambios terminales.
- `patient_location_history`: asignaciones y traslados de cama no destructivos.

Las camas siguen siendo registros activos de `care_units` con `unit_type = 'bed'`.
La ubicación enlaza la hospitalización con la cama; servicio y sala se resuelven
mediante `care_units -> rooms -> services`.

## Integridad y concurrencia

La migración `20260731_0006` está encadenada a `20260728_0005` y agrega índices
únicos parciales PostgreSQL para:

- RUT no nulo único;
- una hospitalización `active` por paciente;
- una ubicación con `ended_at IS NULL` por hospitalización;
- una ocupación con `ended_at IS NULL` por cama.

Los servicios validan las mismas reglas, bloquean las filas relevantes durante
mutaciones y traducen conflictos de integridad concurrentes a `409 Conflict`.
Crear una hospitalización con cama, trasladar, terminar y conciliar se ejecutan
como transacciones únicas.

Las revisiones técnicas `20260805_0007` y `20260805_0008` hacen único el número
de ficha hospitalaria no nulo, normalizan sus valores a mayúsculas y agregan una
restricción que impide almacenar valores sin normalizar. La segunda revisión se
detiene si detecta registros históricos que sólo difieren por mayúsculas y
minúsculas, para no fusionarlos automáticamente.

## Identidad y conciliación

El RUT se recibe con o sin puntos, se normaliza a `XXXXXXXX-D`, se valida mediante
módulo 11 y sólo puede existir una vez. El formato con separadores de miles se
aplica en React.

Los pacientes NN y provisorios reciben `NN-YYYYMMDD-XXXX`. El identificador queda
reservado permanentemente incluso después de identificar o fusionar la ficha.
La identificación posterior actualiza la misma ficha cuando el RUT no existe.

Antes de crear una ficha, la interfaz consulta coincidencias potenciales por RUT,
número de ficha, nombres y apellido. Una coincidencia exacta por RUT o número de
ficha bloquea el duplicado y permite abrir la ficha existente. Una coincidencia
sólo nominal se muestra como advertencia y exige confirmar que corresponde a otra
persona. Esta ayuda no sustituye las restricciones únicas de la base de datos.

Si el RUT ya pertenece a otro paciente, la conciliación es explícita. La ficha
identificada es canónica, las hospitalizaciones se relocalizan conservando sus
UUID e historiales y la provisoria queda inactiva con paciente canónico, usuario,
fecha y motivo. Si ambas fichas tienen ingresos activos, toda la transacción se
rechaza en el flujo habitual.

La interfaz no interpreta automáticamente la coincidencia de RUT como identidad
confirmada. Antes de conciliar muestra en paralelo la ficha NN actual y la ficha
histórica principal, incluyendo nombre disponible, RUT, número de ficha, edad,
hospitalización activa, ubicación y cantidad de hospitalizaciones registradas.
El operador debe ingresar un motivo de al menos diez caracteres y confirmar
expresamente que ambas fichas corresponden a la misma persona.

Cuando ambas fichas tienen una hospitalización activa, únicamente `jefatura`
puede usar el flujo de resolución administrativa. Debe seleccionar cuál ingreso
es el duplicado; éste termina como `closed` con motivo de duplicidad, libera su
cama y conserva sus historiales. El otro ingreso permanece `active` y luego ambas
fichas se concilian en la misma transacción. Este cierre no equivale a un alta
médica (`discharged`) y queda identificado mediante eventos de auditoría propios.

La ficha identificada preexistente siempre permanece como principal. Se trasladan
las hospitalizaciones de la ficha NN —incluida su ubicación actual— sin cambiar sus
UUID ni historiales. La ficha NN no se elimina: queda inactiva, vinculada a la
principal y disponible para auditoría. Nombres informados y números de ficha
distintos no sobrescriben automáticamente los datos canónicos.

## Hospitalizaciones y ubicaciones

Toda hospitalización comienza en `active` y registra el evento inicial. Puede
terminar como `discharged`, `deceased` o `closed`; no puede reactivarse en esta
fase. El término cierra y libera automáticamente la cama vigente.

Una hospitalización puede comenzar sin cama. La misma operación de ubicación
asigna la cama inicial o traslada: cierra el registro vigente y crea uno nuevo.
Nunca se actualiza ni elimina un movimiento histórico.

## Autorización y auditoría

`administrador` conserva lectura para soporte, mientras que `jefatura` y
`nutricionista` pueden leer y realizar mutaciones clínicas. `alimentacion` no
puede acceder a las rutas ni ve el módulo. Todas las rutas requieren sesión y
toda mutación exige CSRF y actor autenticado.

Se auditan creación e identificación de pacientes, conciliación, creación y
término de hospitalizaciones, asignación, traslado y cierre de ubicación. Los
eventos incluyen actor, entidad, estado anterior/posterior y `admission_id`.

## API

Pacientes:

- `POST /api/v1/patients`
- `POST /api/v1/patients/unidentified`
- `GET /api/v1/patients`
- `GET /api/v1/patients/potential-matches`
- `GET /api/v1/patients/{patient_id}`
- `PATCH /api/v1/patients/{patient_id}/identity`
- `POST /api/v1/patients/{patient_id}/reconcile`
- `POST /api/v1/patients/{patient_id}/reconcile-active-conflict` (sólo `jefatura`)

Hospitalizaciones y ubicación:

- `POST /api/v1/admissions`
- `GET /api/v1/admissions/active`
- `GET /api/v1/admissions/{admission_id}`
- `PATCH /api/v1/admissions/{admission_id}/status`
- `GET /api/v1/patients/{patient_id}/admissions`
- `POST /api/v1/admissions/{admission_id}/location`
- `GET /api/v1/admissions/{admission_id}/location`
- `GET /api/v1/admissions/{admission_id}/location-history`

El listado acepta `q`, `identity_status`, `page` y `page_size`, con orden estable.

## Seeds y verificación

Los seeds agregan dos pacientes identificados ficticios con RUT de prueba, dos
pacientes NN, tres ingresos activos (uno sin cama) y un ingreso terminado:

```bash
cd apps/backend
python -m app.db.seed
python -m app.db.seed
```

PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts_verify_phase5.ps1
```

Linux/macOS:

```bash
./scripts_verify_phase5.sh
```
