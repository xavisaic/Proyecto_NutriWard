# Fase 10: minutas, raciones y producción alimentaria

## Decisión implementada

La minuta diaria vive dentro de la ficha de cada hospitalización, en una pestaña propia
**Minuta diaria**. No se guarda como un único texto: se estructura en seis tiempos de
comida —desayuno, colación AM, almuerzo, once, cena y colación PM— y cada tiempo admite
varios componentes combinables.

Esta separación permite representar, por ejemplo, pan con agregado, leche con tres medidas
de espesante y jalea en el mismo desayuno; también permite agregar elementos no incluidos
en el catálogo, como medio pan sin agregado y siete galletas de soda.

## Reglas funcionales

- Cada tiempo puede solicitar bandeja, dejarse sin bandeja, marcarse no aplicable o en
  espera.
- Una ración puede contener múltiples elementos del catálogo y elementos libres. Cada
  elemento guarda cantidad, unidad e indicación propia.
- Almuerzo, cena y los demás tiempos disponen de instrucciones especiales para exclusiones,
  textura, alérgenos o cantidades, por ejemplo: sin arroz, sin vacuno, sin gluten o 150 g
  de proteína.
- Las vías oral, enteral (NE) y parenteral (NP) son independientes y combinables.
- NE o NP sin vía oral no generan bandejas. Si existe vía oral simultánea, se producen sólo
  las bandejas oralmente indicadas.
- NE puede incluir bolos de proteína u otras preparaciones modulares que sí prepara
  Alimentación, aunque el paciente no tenga bandeja. La preparación registra producto,
  gramos de polvo, diluyente, volumen en mL, número de vasos y momento de entrega.
- Sólo una minuta finalizada y vigente participa en producción. Los borradores no generan
  raciones ni preparaciones.
- No existen horarios de cierre en esta versión. El consolidado se calcula al consultarlo y
  el Excel registra su momento de generación.

## Catálogo inicial

El seed importa una instantánea normalizada de `regimenes.xlsx`: 175 filas de origen se
consolidan en 143 conceptos únicos, conservando la fila original y la versión de fuente.
Las abreviaturas se interpretan así:

- `s/s`, `s/s+1`, `s/s+2`: sin sal; sin sal con 1 g o 2 g de sal entregados aparte;
- `s/az`: sin azúcar;
- `s/r` y `s/residuos`: sin residuos;
- `NO suple`: no suplementada;
- `INDICADO`: régimen diabético;
- `merme`: mermelada.

Las repeticiones accidentales del Excel no se convierten en conceptos distintos. Jefatura
puede crear o modificar elementos del catálogo sin alterar las minutas históricas.

## Modelo de datos

- `food_regimen_catalog_items`: catálogo normalizado, versionado por fuente y con baja
  lógica.
- `nutritional_meal_plans`: cabecera versionada por hospitalización, vigencia, estado y
  combinación de vías.
- `nutritional_meal_plan_slots`: los seis tiempos, estado de despacho e instrucciones
  especiales.
- `nutritional_meal_plan_items`: componentes de catálogo o libres, con cantidad y unidad.
- `nutritional_modular_preparations`: bolos de proteína y preparaciones modulares separados
  de las bandejas.

La ubicación operacional siempre se resuelve desde la hospitalización activa al generar el
consolidado; un traslado no duplica una ración y la envía al servicio, sala y cama vigentes.

## Permisos

- `nutricionista`: consulta catálogo; crea, modifica y finaliza minutas de hospitalizaciones
  a las que tiene acceso.
- `jefatura`: mismas operaciones clínicas y administración del catálogo.
- `alimentacion`: sólo consulta la proyección operacional y descarga el consolidado; no
  accede a la ficha clínica completa ni modifica indicaciones.
- `administrador`: conserva su alcance administrativo general y no recibe por defecto una
  facultad clínica implícita.

## Consolidado de Alimentación

La pantalla **Producción alimentaria** permite filtrar por fecha y tiempo. Presenta:

- totales estándar y especiales por servicio y tiempo;
- cantidades agregadas por preparación y unidad;
- detalle de raciones especiales con paciente, servicio, sala y cama;
- alertas alimentarias activas;
- bolos y preparaciones NE con todos sus parámetros;
- excepciones que requieren revisión, como una hospitalización sin ubicación o sin minuta
  finalizada.

La descarga `.xlsx` contiene las hojas `Resumen`, `Preparaciones`, `Raciones especiales`,
`Preparaciones_NE` y `Control`.

## API

- `GET/POST/PATCH /api/v1/food-regimen-catalog`
- `GET /api/v1/admissions/{admission_id}/meal-plans/current`
- `POST /api/v1/admissions/{admission_id}/meal-plans`
- `GET/PUT /api/v1/meal-plans/{meal_plan_id}`
- `POST /api/v1/meal-plans/{meal_plan_id}/finalize`
- `POST /api/v1/meal-plans/{meal_plan_id}/cancel`
- `GET /api/v1/food-production/consolidated`
- `GET /api/v1/food-production/consolidated.xlsx`

## Verificación

Las pruebas automatizadas cubren permisos y seed del catálogo, combinaciones oral + NE,
raciones especiales, elementos libres, bolos de 10 g en 80 mL, pacientes sólo con NE sin
bandeja y la estructura de la descarga Excel. La migración `20260829_0017` mantiene una
única cabeza Alembic.
