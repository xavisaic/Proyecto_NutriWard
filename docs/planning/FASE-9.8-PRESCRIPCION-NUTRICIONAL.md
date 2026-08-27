# Fase 9.8: prescripción nutricional operativa

## Objetivo

Transformar la pestaña Prescripción en la fuente clínica versionada que define cómo se
entregarán los requerimientos nutricionales del episodio. La evaluación calcula lo que el
paciente necesita; esta fase prescribe las vías, productos, volúmenes e indicaciones.

## Alcance del MVP

- Metas de energía, proteínas, carbohidratos, lípidos y volumen importables desde el último
  requerimiento finalizado y congeladas en cada versión.
- Cobertura en tiempo real con umbrales institucionales configurables. Los colores son
  informativos y nunca bloquean por sí solos una validación.
- Estrategias oral, enteral, suplementos/módulos, combinaciones y régimen cero exclusivo.
- Régimen oral, niveles IDDSI separados para alimentos y líquidos, tiempos de comida,
  restricciones, asistencia e instrucciones para cocina y enfermería.
- Catálogo enteral institucional versionado, administración, lavados, pausas y progresión.
- Suplementos y módulos con aporte nutricional explícito.
- Monitoreo básico con parámetro, frecuencia, responsable e instrucción.
- Receta regenerable desde datos estructurados, impresión y copia para ficha clínica.
- Estados `draft`, `validated`, `active`, `suspended`, `superseded` y `cancelled`.
- Modificar una versión crea un nuevo borrador; activar reemplaza atómicamente la activa.
- Historial clínico con diferencias respecto de la versión anterior y auditoría técnica sin
  duplicar el cuerpo clínico.

## Segunda etapa implementada

- Nutrición parenteral estandarizada o individualizada, por acceso central o periférico.
- Peso de cálculo, volumen, horas de infusión, velocidad, aminoácidos, dextrosa, lípidos,
  osmolaridad, vitaminas, oligoelementos, insulina, fecha de inicio y duración estimada.
- Electrolitos estructurados con código, cantidad, unidad e instrucción.
- Cálculo reproducible de energía parenteral, velocidad de infusión y GIR.
- Alertas de osmolaridad periférica, GIR, lípidos por kg, volumen, realimentación y contexto
  de triglicéridos, potasio, fósforo y magnesio.
- Aportes no nutricionales estructurados: propofol, soluciones glucosadas, citrato,
  vehículos, agua de lavado, sueros y otras fuentes.
- Separación visible y persistida entre aporte nutricional, aporte no nutricional confirmado
  y aporte total real. La cobertura clínica usa el total real.
- Sugerencias desde tratamientos activos. Una sugerencia no se suma ni permite validar la
  orden hasta que el profesional la confirme.
- Contexto de los últimos laboratorios nutricionalmente relevantes ya registrados en
  NutriWard; no se inventan resultados ni se consulta un LIS externo.
- Atestación clínica interna al validar, con usuario, fecha y huella SHA-256 del contenido.
- Cola interna auditable de envíos a farmacia, cocina y enfermería, con acuse explícito.

## Cálculos y reproducibilidad

Los cálculos autoritativos se ejecutan en backend con `Decimal`. El volumen enteral es
velocidad por horas efectivas. La composición se obtiene de una versión inmutable del
catálogo y se suma a los aportes orales, suplementos y agua de lavados. La interfaz sólo
previsualiza el mismo cálculo.

Una meta de volumen puede representar objetivo, mínimo, máximo o rango. Cuando es máximo,
un aporte inferior no se considera déficit. Los porcentajes se clasifican con el valor exacto
y se redondean sólo para presentación.

Para parenteral se calcula:

- `velocidad (mL/h) = volumen total / horas de infusión`
- `GIR (mg/kg/min) = dextrosa (g) × 1000 / (peso (kg) × horas × 60)`
- energía = aminoácidos × factor + dextrosa × factor + lípidos × factor

Los factores energéticos y límites de apoyo son configurables. Los valores iniciales
(`4 kcal/g`, `3,4 kcal/g`, `10 kcal/g`, `900 mOsm/L`, GIR `5 mg/kg/min` y lípidos
`2,5 g/kg/día`) son parámetros de arranque y deben ser revisados y aprobados por cada
institución antes de uso clínico.

## API

- `GET /api/v1/admissions/{admission_id}/nutrition-prescription-workspace`
- `POST /api/v1/admissions/{admission_id}/nutrition-prescription-orders`
- `PATCH /api/v1/nutrition-prescription-orders/{order_id}`
- `POST /api/v1/nutrition-prescription-orders/{order_id}/validate|activate|suspend|clone`
- `POST /api/v1/nutrition-prescription-orders/{order_id}/dispatch`
- `POST /api/v1/nutrition-prescription-dispatches/{dispatch_id}/acknowledge`
- `POST /api/v1/enteral-formula-catalog`
- `PUT /api/v1/nutrition-prescription-settings`

Las lecturas clínicas requieren `nutricionista` o `jefatura`; los cambios exigen CSRF. La
administración del catálogo y los umbrales corresponde a `jefatura` o `administrador`.
Los episodios históricos son de sólo lectura.

## Límites de integración

La firma implementada es una atestación clínica interna y no se presenta como firma electrónica
avanzada o legal. Los envíos se registran en una cola interna: `queued` no significa que un
sistema externo los haya recibido. Conectar un LIS, farmacia, cocina o enfermería requiere
proveedor, credenciales, protocolo institucional, transformación de mensajes y confirmación
de entrega. También queda fuera de alcance el registro de administración real, que corresponde
al módulo de Seguimiento.

Como referencias de seguridad y flujo se revisaron los recursos de ASPEN sobre nutrición
parenteral, su care pathway y la lista de revisión de órdenes. La implementación mantiene
separadas la prescripción, la revisión farmacéutica, la preparación, la administración y el
monitoreo.
