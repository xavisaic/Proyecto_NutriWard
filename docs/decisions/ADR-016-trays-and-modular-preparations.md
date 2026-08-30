# ADR-016: Separar bandejas orales de preparaciones modulares

- **Estado**: Aprobado
- **Fecha**: 2026-08-29

## Contexto

La vía enteral o parenteral por sí sola no requiere una bandeja oral. Sin embargo, un
paciente con nutrición enteral puede necesitar un bolo de proteína preparado por
Alimentación. Además, las vías pueden coexistir: oral + enteral, oral + parenteral o enteral
+ parenteral.

## Decisión

Las bandejas se modelan por tiempo de comida y sólo se consolidan cuando la vía oral está
habilitada y el tiempo se encuentra solicitado. Los bolos y módulos se guardan como
preparaciones operacionales independientes, con producto, gramos de polvo, diluyente,
volumen, unidades y entrega.

Las tres vías se almacenan como indicadores independientes, no como una enumeración
mutuamente excluyente.

## Consecuencias

- Un paciente sólo con NE puede aparecer en `Preparaciones_NE` sin aumentar el total de
  bandejas.
- Una combinación oral + NE produce la bandeja indicada y, separadamente, sus bolos.
- NP por sí sola no genera trabajo para Alimentación; NP + oral sí genera las bandejas
  orales.
- Los borradores no se proyectan y se evita confundir una indicación clínica con una orden
  operacional finalizada.
