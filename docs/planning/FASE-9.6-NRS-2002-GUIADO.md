# Fase 9.6: NRS-2002 guiado y cálculo en tiempo real

## Objetivo

Reemplazar la digitación directa de puntajes NRS-2002 por un formulario progresivo que
conserve las respuestas clínicas, explique el origen de cada componente y muestre el
resultado mientras el profesional completa el tamizaje.

## Flujo clínico

### Tamizaje inicial

La interfaz pregunta si existe IMC menor de 20,5 kg/m², pérdida de peso en tres meses,
reducción de ingesta en la última semana o enfermedad grave/tratamiento intensivo. El IMC
se calcula desde el peso y talla de la evolución cuando ambos están disponibles; si no,
puede registrarse un IMC externo o responderse la pregunta explícitamente.

Cuatro respuestas negativas producen total 0, clasificación `initial_screen_negative` y
la indicación visible de repetir semanalmente. Una respuesta positiva despliega los pasos
finales.

### Deterioro nutricional

El algoritmo asigna puntajes separados:

- pérdida de peso: 0, más de 5% en tres meses: 1, más de 5% en dos meses: 2, y más de 5%
  en un mes o más de 15% en tres meses: 3;
- ingesta: más de 75%: 0, 50–75%: 1, 25–50%: 2 y menos de 25%: 3;
- IMC con deterioro general: 18,5–20,5: 2 y menor de 18,5: 3.

El componente nutricional es el máximo de esos criterios, nunca su suma. La respuesta que
determinó el puntaje queda disponible junto con los demás criterios.

### Gravedad y edad

La gravedad 0–3 se selecciona mediante tarjetas con ejemplos orientativos. NutriWard no la
infiere desde los diagnósticos porque representa estrés metabólico y aumento de
requerimientos en la situación actual.

Cuando la fecha de nacimiento es exacta, el backend calcula la edad en la fecha del
tamizaje y ese resultado prevalece sobre el cliente. Una edad estimada o ausente exige
confirmación profesional en la interfaz y registra la fuente utilizada.

## Resultado y seguridad

El frontend muestra en tiempo real deterioro nutricional, gravedad, edad y total. Un total
mayor o igual a 3 se presenta como **con riesgo nutricional**; no se crean categorías
adicionales de riesgo bajo, moderado o alto que no pertenezcan al instrumento.

El backend `espen-nrs2002-v2` recalcula cada componente y el total. No acepta el puntaje
total del frontend como autoridad. Las respuestas parciales pueden guardarse con
clasificación `incomplete`, pero la evolución no puede finalizar hasta completarlas. Los
registros `espen-nrs2002-v1` permanecen inmutables y no se recalculan.

## Referencias

- ESPEN Guidelines for Nutrition Screening 2002:
  https://www.espen.org/documents/Screening.pdf
- Kondrup J, Rasmussen HH, Hamberg O, Stanga Z. *Nutritional risk screening (NRS 2002): a
  new method based on an analysis of controlled clinical trials*. Clinical Nutrition
  2003;22(3):321–336. https://doi.org/10.1016/S0261-5614(02)00214-5
