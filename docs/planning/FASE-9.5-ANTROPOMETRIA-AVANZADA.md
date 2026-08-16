# Fase 9.5: antropometría avanzada, composición corporal y función muscular

## Objetivo

Ampliar el módulo Antropometría de una evolución nutricional sin mezclar mediciones de
protocolos distintos ni convertir datos del equipo en conclusiones clínicas automáticas.
Cada conjunto se registra como una sesión vinculada a la hospitalización y a la evolución.

## Configuración institucional inicial

### Circunferencias

- pantorrilla izquierda o derecha;
- braquial izquierda o derecha;
- cintura sin lateralidad;
- una lectura por sitio, en centímetros;
- la posición puede documentarse en cada sesión.

### Dinamometría de mano

- protocolo `hospital-handgrip`, versión `v1`;
- dispositivo identificado por fabricante y modelo;
- posición documentada por el profesional;
- tres intentos en kgf para cada mano;
- algoritmo `maximum-of-three-bilateral-v1`: conserva los seis intentos y calcula el máximo
  izquierdo, máximo derecho y máximo bilateral;
- no aplica puntos de corte ni diagnostica sarcopenia automáticamente.

La configuración sigue los elementos con mayor acuerdo del protocolo Delphi internacional:
dinamómetro hidráulico, paciente sentado y uso del máximo bilateral. El número de intentos
queda fijado institucionalmente en tres para asegurar una serie reproducible.

### Cuatro pliegues

- protocolo `durnin-womersley-4`, versión `v1`;
- plicómetro identificado por fabricante y modelo;
- bíceps, tríceps, subescapular y suprailiaco del lado derecho;
- tres intentos en milímetros para cada sitio;
- algoritmo `mean-of-three-per-site-sum-v1`: calcula la media de cada sitio, redondeada a
  0,1 mm, y suma las cuatro medias;
- no estima densidad corporal ni porcentaje de grasa, porque esas conversiones requieren
  edad, sexo y una decisión clínica/metodológica adicional.

### Bioimpedancia clínica

- protocolo `device-reported-bia`, versión `v1`;
- fabricante, modelo y tecnología son obligatorios cuando se registran resultados;
- admite serie, frecuencias, posición, preparación, ayuno, ejercicio reciente, vaciamiento
  vesical, hidratación y edema;
- conserva resistencia, reactancia, ángulo de fase y las estimaciones de agua, masa grasa,
  masa libre de grasa y masa muscular que entregue el equipo;
- todos esos resultados se marcan `device_reported`: NutriWard no aplica ecuaciones propias,
  no armoniza resultados entre fabricantes y no realiza interpretación automática.

## Trazabilidad y edición

Las tablas `nutritional_measurement_sessions` y `nutritional_measurement_values` separan
metadatos de sesión y mediciones. Guardan protocolo, versión del algoritmo, autor, fecha,
dispositivo, unidad, lateralidad, intento y naturaleza del valor (`measured`, `calculated`
o `device_reported`). Un borrador puede reemplazar su contenido; al finalizar, conserva la
misma inmutabilidad y mecanismo de corrección que las demás evoluciones clínicas.

La API rechaza intentos duplicados, unidades incompatibles, series incompletas y protocolos
que no correspondan al tipo de sesión. La interfaz realiza la misma comprobación antes de
enviar para que el profesional pueda corregir el bloque específico.

## Referencias de configuración

- Durnin JVGA, Womersley J. *Body fat assessed from total body density and its estimation
  from skinfold thickness*. British Journal of Nutrition, 1974. Descripción histórica y
  sitios: https://www.cambridge.org/core/journals/british-journal-of-nutrition/article/making-of-a-classic-the-1974-durninwomersley-body-composition-paper/E8EA87847D7481F0CF6800090F9FB130
- Vaishya R et al. *International consensus on a standardised test protocol for handgrip
  strength assessment*. BMJ Open Sport & Exercise Medicine, 2025:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC12214977/
- ESPEN. *Bioelectrical impedance analysis—part II: utilization in clinical practice*:
  https://www.espen.org/documents/BIA2.pdf

Estas referencias sustentan la configuración técnica inicial; los puntos de corte y la
interpretación clínica deben aprobarse por la institución antes de automatizarse.
