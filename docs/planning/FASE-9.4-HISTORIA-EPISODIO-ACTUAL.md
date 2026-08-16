# Fase 9.4: historia del episodio actual

## Propósito y alcance

La pestaña **Diagnósticos y antecedentes** incorpora un relato clínico de los sucesos que
precedieron y condujeron a la hospitalización. Esta historia —equivalente funcional a una
anamnesis próxima— pertenece exclusivamente al episodio seleccionado; no se copia a nuevas
hospitalizaciones ni se confunde con antecedentes mórbidos longitudinales.

La narrativa complementa la estructura clínica, pero no reemplaza diagnósticos médicos,
antecedentes, alergias ni evoluciones nutricionales. NutriWard no extrae ni crea
diagnósticos automáticamente desde el texto.

## Interfaz

La tarjeta **Historia del episodio actual** aparece antes de los diagnósticos del ingreso.
Permite:

- escribir o pegar hasta 10.000 caracteres conservando párrafos;
- indicar la fuente de información;
- registrar opcionalmente la fecha de inicio de los acontecimientos;
- consultar autor, fecha y número de la versión vigente;
- revisar el contenido íntegro de todas las versiones;
- actualizar mediante una nueva versión y un motivo obligatorio.

El guardado es explícito. El editor advierte al cerrar o abandonar la página con cambios
sin guardar y nunca usa almacenamiento del navegador para persistir información clínica.
En hospitalizaciones históricas la tarjeta es de sólo lectura.

## Persistencia e integridad clínica

La migración `20260816_0013` crea `admission_clinical_history_versions`. Cada fila contiene:

- `admission_id` y número de versión único dentro del episodio;
- narrativa, fuente y fecha de inicio opcional;
- motivo de actualización, salvo en el registro inicial;
- autor y fecha de registro.

Las versiones son inmutables: actualizar la historia inserta una nueva fila. El cliente
envía la versión vigente y recibe `409` si otro profesional actualizó el registro primero.
No existe borrado clínico.

## API, permisos y privacidad

- `GET /api/v1/admissions/{admission_id}/clinical-context` entrega la versión vigente y el
  historial completo junto a diagnósticos y antecedentes;
- `POST /api/v1/admissions/{admission_id}/clinical-history` crea la primera versión;
- `PATCH /api/v1/admissions/{admission_id}/clinical-history` agrega una versión nueva.

Sólo `nutricionista` y `jefatura` pueden leer o modificar la historia. Toda mutación exige
CSRF y un episodio activo. `administrador` y `alimentacion` reciben `403`; la proyección
alimentaria no incluye esta narrativa.

La auditoría técnica registra acción, actor, episodio, entidad y número de versión, pero
nunca la narrativa ni el motivo clínico. El contenido permanece únicamente en la tabla
clínica versionada.
