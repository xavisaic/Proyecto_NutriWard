# ADR-011: Identificación del paciente y manejo de reingresos

- **Estado**: Aprobado
- **Fecha**: 2026-07-27

## Decisión

El paciente se identificará inequívocamente mediante su RUT. El sistema utilizará
un UUID como identificador técnico interno y mantendrá el RUT normalizado como
identificador único de negocio.

El nutricionista podrá buscar al paciente por RUT o por identificador
hospitalario. El RUT deberá validarse, normalizarse y comprobarse antes de crear
una ficha nueva para evitar duplicados causados por diferencias de formato.

## Ficha personal y episodios hospitalarios

- Si el paciente ya existe, se reutiliza su ficha personal.
- Si el paciente no existe, se crea una nueva ficha personal.
- Cada ingreso o reingreso crea un nuevo episodio hospitalario.
- Un traslado interno no crea un nuevo episodio: se registra como un movimiento
  dentro de la hospitalización vigente.
- Un alta o traslado externo cierra el episodio hospitalario actual.
- Si el paciente regresa después de un alta o traslado externo, se crea un nuevo
  episodio asociado a la misma ficha personal.

## Historial nutricional

Los antecedentes nutricionales de episodios anteriores permanecerán disponibles
como historial y no se sobrescribirán ni eliminarán.

La evaluación, los requerimientos nutricionales, el diagnóstico y el plan
vigente comenzarán dentro del nuevo episodio hospitalario. El sistema no copiará
ni reactivará automáticamente diagnósticos, cálculos, prescripciones o planes
anteriores como si continuaran vigentes.

## Reutilización controlada de antecedentes

El sistema podrá permitir que el nutricionista consulte antecedentes anteriores
o copie información seleccionada a un borrador. La información copiada no tendrá
vigencia clínica hasta que el profesional la revise y confirme explícitamente.

La operación deberá registrar:

- episodio de origen;
- episodio de destino;
- profesional responsable;
- fecha y hora;
- información copiada;
- modificaciones realizadas;
- confirmación profesional.

## Reglas de integridad y trazabilidad

- El RUT normalizado será único.
- El RUT se almacenará sin puntos y con dígito verificador validado; el formato
  de presentación se aplicará únicamente en la interfaz.
- No se permitirá crear una segunda ficha con un RUT ya registrado.
- Las correcciones del RUT y las vinculaciones entre episodios deberán quedar
  auditadas.
- Todos los registros clínicos conservarán su episodio hospitalario de origen.

## Consecuencias

- Se evita duplicar pacientes cuando reingresan.
- Se mantiene una historia longitudinal por paciente y una separación clara
  entre episodios hospitalarios.
- Se previene la reactivación accidental de indicaciones clínicas antiguas.
- La reutilización de antecedentes exige revisión profesional y conserva la
  trazabilidad de su procedencia.
