# Fase 7.6: apariencia clara, oscura y según el sistema

## Objetivo

Extender el sistema visual de Fase 7.5 con una apariencia oscura apropiada para turnos
nocturnos y ambientes de baja luminancia, sin sustituir el modo claro como experiencia
clínica predeterminada y sin modificar flujos, permisos, contratos API ni dominio clínico.

La preferencia ofrece tres alternativas:

1. **Claro**, selección predeterminada para uso hospitalario habitual.
2. **Oscuro**, con superficies verde carbón y contraste semántico específico.
3. **Según el sistema**, que sigue `prefers-color-scheme` y responde a sus cambios.

## Arquitectura y persistencia

`createNutriwardTokens(mode)` genera tokens claros u oscuros manteniendo la misma interfaz.
`createNutriwardTheme(mode)` construye el tema MUI y conserva todos los overrides de Fase
7.5. `AppearanceProvider` resuelve la preferencia, aplica `color-scheme` al documento y
envuelve la aplicación con el tema correspondiente.

La composición raíz queda centralizada en `AppProviders`: autenticación se restaura primero
y la apariencia utiliza el UUID del usuario activo como ámbito de persistencia. Cada cuenta
guarda su elección en `localStorage` bajo `nutriward:appearance:{user_id}`. El login usa el
ámbito `guest`; si una cuenta no tiene preferencia previa, hereda la elección realizada antes
de autenticarse. Al cerrar sesión vuelve al ámbito invitado, evitando compartir preferencias
entre cuentas.

No se almacena información clínica ni identificatoria adicional: el UUID ya disponible en
la sesión sólo forma parte del nombre local de la preferencia.

## Decisiones visuales

- No se usa negro puro: el fondo base oscuro es `#111816` y las superficies usan verdes
  carbón diferenciados.
- El verde petróleo se aclara en modo oscuro para conservar contraste sobre superficies
  profundas.
- Éxito, advertencia, error, información y traslado tienen fondos, bordes y primeros planos
  oscuros propios; no se calculan mediante inversión automática.
- Cama libre, ocupada, seleccionada y con traslado conservan texto, icono y borde además de
  color.
- Sombras oscuras aumentan opacidad sin producir halos claros.
- Inputs, tablas, drawers, diálogos, alertas, AppBar y navegación consumen los mismos tokens
  dinámicos.
- El panel de marca del login mantiene contraste de texto mediante `contrastText` específico
  para cada esquema.

## Interfaz

`AppearanceMenu` muestra un botón accesible en login y AppBar. El menú usa opciones de tipo
`menuitemradio`, iconos y marca textual de selección. El tooltip informa la preferencia
actual y el icono principal refleja el esquema resuelto.

El cambio se aplica inmediatamente y no recarga la página, no reinicia formularios ni
interrumpe actualizaciones de datos.

## Accesibilidad

- El modo claro continúa como valor por defecto.
- Los textos principales y secundarios mantienen contraste sobre fondo y superficie.
- Los estados operacionales usan bordes, iconos y etiquetas además de color.
- La selección del menú expone `aria-checked`.
- El control puede operarse completamente por teclado.
- `color-scheme` permite que controles nativos adopten el esquema correcto.
- `prefers-reduced-motion` continúa aplicándose en ambos modos.
- `Según el sistema` escucha cambios de preferencia sin requerir recarga.

## Criterios de aceptación

- existen opciones Claro, Oscuro y Según el sistema en login y aplicación autenticada;
- el modo claro permanece predeterminado;
- la preferencia se guarda de forma independiente por usuario;
- el esquema del sistema se resuelve y actualiza correctamente;
- login, navegación, estructura hospitalaria y mapa no contienen superficies claras
  literales incompatibles con el tema oscuro;
- camas, traslados, alertas, inputs, drawers y diálogos conservan legibilidad;
- cambiar de apariencia no altera estado funcional ni llamadas API;
- no existe scroll horizontal global nuevo en escritorio o móvil;
- pruebas, build y verificador integral terminan correctamente.

## Procedimiento de verificación

1. Ejecutar `npm test -- --run` dentro de `apps/frontend`.
2. Ejecutar `npm run build` dentro de `apps/frontend`.
3. Ejecutar `powershell -ExecutionPolicy Bypass -File scripts_verify_phase7.ps1`.
4. En login, alternar Claro, Oscuro y Según el sistema; verificar foco, labels y error.
5. Autenticar dos usuarios y comprobar que sus preferencias son independientes.
6. Revisar AppShell, estructura hospitalaria y mapa en ambos esquemas.
7. En el mapa, comprobar cama libre, ocupada, traslado, selección, drawer y diálogo.
8. Cambiar la preferencia del sistema con la opción automática activa.
9. Repetir en escritorio y móvil, verificando ausencia de overflow horizontal.
10. Revisar consola y confirmar que no existen errores o advertencias nuevas relevantes.

## Decisiones pendientes

La Fase 8 deberá definir tokens adicionales para estados nutricionales reales y revisar
tablas y formularios clínicos largos en ambos esquemas. Un modo de alto contraste continúa
siendo una mejora independiente; no se simula mediante el modo oscuro.
