# Fase 9.3: evolución nutricional modular

## Problema resuelto

El flujo original obligaba a recorrer diez secciones incluso para registrar un cambio
pequeño, como una nueva ingesta o una modificación de prescripción. Además, una evolución
parcial más reciente podía ocultar en la proyección datos clínicos vigentes documentados
en una atención anterior.

Fase 9.3 conserva el modelo clínico auditable de Fase 9, pero cambia la interacción y la
proyección longitudinal para que el registro cotidiano sea más rápido y seguro.

## Modelo de interacción

La ruta técnica `care` y los contratos de atenciones se mantienen para no romper enlaces
ni integraciones, mientras la interfaz pasa a llamarse **Evolución nutricional**. Al crear
un registro se ofrecen tres modos:

1. **Seguimiento rápido**: parte con contexto, evaluación clínica, ingesta/exámenes y
   seguimiento; el profesional puede agregar o quitar módulos opcionales.
2. **Acción específica**: parte con contexto y síntesis, y permite seleccionar sólo los
   módulos necesarios.
3. **Evaluación nutricional inicial**: conserva el recorrido completo de diez secciones.

Contexto y síntesis permanecen seleccionados en todos los modos. El progreso y la
navegación consideran únicamente las secciones elegidas.

## Acceso directo y línea de tiempo

Evaluación, Prescripción, Minutas e ingesta y Exámenes incluyen acciones directas para
actualizar su módulo. Cada acción sigue generando una evolución clínica con autor, fecha,
estado, versión y síntesis; no crea datos sin trazabilidad.

La línea de tiempo muestra tipo, estado, fecha, profesional, síntesis y etiquetas de los
módulos documentados. Permite abrir el contenido estructurado completo, continuar o
cancelar borradores y corregir registros finalizados mediante una nueva versión enlazada.

## Reglas de finalización

Toda evolución exige motivo, fuente y síntesis clínica. La evaluación inicial exige
además población, tamizaje documentado —o motivo de no aplicación— y al menos un PES. Los
seguimientos, reevaluaciones, altas y acciones específicas pueden finalizar con contenido
modular parcial.

Se mantienen CSRF, control de autor, versión optimista, inmutabilidad de finalizados,
motivo de cancelación/corrección y bloqueo de escritura en episodios históricos. La
confirmación ocurre antes de guardar y finalizar para no generar borradores accidentales
si el profesional cancela la acción.

## Proyección longitudinal por módulo

`nutrition-latest` recorre las evoluciones finalizadas desde la más reciente y resuelve de
forma independiente evaluación, tamizaje, requerimientos, diagnósticos PES, prescripción y
alertas. Por ejemplo, registrar sólo ingesta no elimina de la vista la prescripción vigente
ni el último estado nutricional. Si el módulo más reciente documenta un PES resuelto, una
prescripción discontinuada o una alerta inactiva, la proyección respeta ese cierre y no
reactiva el registro anterior.

Cada resumen incorpora `documented_sections`, calculado desde las filas clínicas existentes,
para representar los módulos de la evolución en la línea de tiempo. El cambio no agrega
tablas ni columnas persistidas y no requiere una nueva migración; la cabeza Alembic sigue
siendo `20260815_0012`.

## Límites conscientes

- El guardado es explícito: no se persiste información clínica sensible en el navegador.
- El editor rápido incorpora un elemento por módulo en cada evolución; la API mantiene
  colecciones estructuradas y permite extender la edición masiva en una fase posterior.
- La edición tabular masiva, la firma electrónica legal y la integración con TrakCare
  permanecen fuera de alcance.
