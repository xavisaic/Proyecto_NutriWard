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

## Cálculos y reproducibilidad

Los cálculos autoritativos se ejecutan en backend con `Decimal`. El volumen enteral es
velocidad por horas efectivas. La composición se obtiene de una versión inmutable del
catálogo y se suma a los aportes orales, suplementos y agua de lavados. La interfaz sólo
previsualiza el mismo cálculo.

Una meta de volumen puede representar objetivo, mínimo, máximo o rango. Cuando es máximo,
un aporte inferior no se considera déficit. Los porcentajes se clasifican con el valor exacto
y se redondean sólo para presentación.

## API

- `GET /api/v1/admissions/{admission_id}/nutrition-prescription-workspace`
- `POST /api/v1/admissions/{admission_id}/nutrition-prescription-orders`
- `PATCH /api/v1/nutrition-prescription-orders/{order_id}`
- `POST /api/v1/nutrition-prescription-orders/{order_id}/validate|activate|suspend|clone`
- `POST /api/v1/enteral-formula-catalog`
- `PUT /api/v1/nutrition-prescription-settings`

Las lecturas clínicas requieren `nutricionista` o `jefatura`; los cambios exigen CSRF. La
administración del catálogo y los umbrales corresponde a `jefatura` o `administrador`.
Los episodios históricos son de sólo lectura.

## Fuera de alcance

Quedan para una etapa posterior la nutrición parenteral individualizada, GIR y electrolitos,
aportes no nutricionales automáticos, integración con laboratorio/farmacia, firma electrónica,
envío directo a cocina/enfermería y registro de administración real.
