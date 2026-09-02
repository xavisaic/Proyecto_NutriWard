# Fase 9.8 · Exámenes masivos y tendencias

## Alcance implementado

La pestaña Exámenes permite pegar tablas tabuladas o separadas por punto y coma. Los
encabezados `Examen`, `Resultado`, `Unidad`, `Rango` y `Flag` se reconocen aunque sus
columnas estén en distinto orden. Antes de guardar se presenta una revisión por fila.

Cada lote crea una evolución específica finalizada e inmutable, un lote auditable y sus
resultados. No se conserva el portapapeles completo: sólo las filas estructuradas y la
trazabilidad clínica necesaria.

## Catálogo y exámenes nuevos

Los nombres se normalizan sin depender de mayúsculas, tildes o puntuación. Una coincidencia
exacta con el nombre canónico o un alias conocido se asocia automáticamente. Un nombre
nuevo puede:

- crear un examen canónico y aprender el alias;
- asociarse manualmente a un examen existente;
- guardarse pendiente sin perder el resultado.

Los pendientes pueden clasificarse posteriormente. La clasificación modifica únicamente
el vínculo de catálogo, conserva el nombre original y registra auditoría.

## Valores y rangos

Se conserva el valor textual original y, cuando corresponde, se extraen por separado el
comparador, valor numérico, límites inferior y superior y unidad normalizada. El rango
original queda congelado con cada resultado. La ausencia de rango no impide guardar ni
graficar y no genera una interpretación clínica automática.

## Proyecciones

`GET /api/v1/admissions/{admission_id}/nutrition-lab-trends` entrega series numéricas por
examen canónico o por nombre pendiente. Exámenes muestra una curva seleccionable y Resumen
presenta minigráficos de las tres series con resultados más recientes.

La migración `20260831_0018` agrega catálogo, alias, lotes y campos numéricos sin alterar
los resultados históricos existentes.
