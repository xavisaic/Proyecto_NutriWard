# Fase 7.5: fundamentos de experiencia visual y sistema de diseño

## Objetivo

Fase 7.5 establece una base visual profesional, consistente y reutilizable antes de la
ficha clínica de Fase 8. La intervención conserva autenticación, permisos, navegación
funcional, contratos API, movimientos, traslados y actualización del mapa. No incorpora
dominio clínico nuevo.

La dirección es **calma clínica cálida**: verde petróleo como identidad, neutros cálidos
para fondos y superficies, azul grisáceo como apoyo y una densidad adecuada para jornadas
hospitalarias. El movimiento es breve y funcional.

## Auditoría y plan de intervención

El frontend se concentra en `apps/frontend/src`, con React, TypeScript, Vite, MUI,
Lucide y Wouter. Antes de intervenir se verificó un worktree limpio, 47 pruebas de
frontend exitosas y un build de producción correcto. La auditoría encontró:

- un tema mínimo declarado dentro de `main.tsx`;
- navegación superior por pestañas concentrada en `HomePage`;
- colores operacionales literales principalmente en el mapa de camas;
- patrones de encabezado, panel, feedback y carga repetidos o resueltos localmente;
- pruebas de autorización por roles ya existentes y una cobertura amplia del mapa.

La migración se ejecuta por capas: tema, componentes compartidos, AppShell, login, mapa,
pruebas y verificación visual. Las vistas de hospital, pacientes y administración se
integran en el shell sin rediseño profundo.

## Decisiones visuales y tokens principales

Los tokens viven en `apps/frontend/src/app/theme/tokens.ts`; el tema y los overrides MUI
en `apps/frontend/src/app/theme/theme.ts`.

| Uso | Token principal | Valor |
| --- | --- | --- |
| Identidad | `primary.main` | `#155E54` |
| Identidad oscura | `primary.dark` | `#0E463F` |
| Apoyo azul grisáceo | `secondary.main` | `#48657A` |
| Fondo de aplicación | `background.default` | `#F5F4EF` |
| Superficie | `background.paper` | `#FFFEFB` |
| Texto principal | `text.primary` | `#24312E` |
| Borde estándar | `border.default` | `#D6DAD5` |
| Éxito / cama libre | `success.main` | `#397557` |
| Advertencia / cama ocupada | `warning.main` | `#9A6700` |
| Error | `error.main` | `#B54747` |
| Información | `info.main` | `#47728A` |
| Traslado | `transfer.main` | `#68549A` |

La escala base de espaciado usa múltiplos de 8 px y añade nombres de 4 a 48 px. Los
radios se concentran entre 6 y 18 px; las sombras tienen niveles `low`, `medium` y
`high`; las transiciones usan 150, 180 y 200 ms. Los breakpoints permanecen alineados
con MUI (`600 / 900 / 1200 / 1536`). La navegación mide 248 px y el AppBar 64 px.

El tema incluye overrides para `Button`, `IconButton`, `Paper`, `Card`, `TextField`,
`Select`, `Tabs`, `Chip`, `Alert`, `Dialog`, `Drawer`, `Tooltip`, `Table`, `AppBar` y
`Snackbar`. Hover, foco, active y disabled se resuelven de manera consistente. Una media
query global reduce animaciones y transiciones cuando el sistema indica
`prefers-reduced-motion: reduce`.

## Componentes compartidos creados

- `AppShell`: estructura responsive, salto a contenido, cabecera persistente y usuario.
- `MainNavigation`: navegación por módulos, módulo activo y activación por teclado.
- `PageHeader`: título, contexto descriptivo y acciones.
- `SectionCard`: panel de sección con encabezado opcional.
- `StatCard`: resumen numérico compacto.
- `StatusBadge`: estado semántico con texto, icono y borde.
- `EmptyState`, `LoadingState` y `ErrorState`: estados de contenido accesibles.
- `FeedbackSnackbar`: feedback no bloqueante unificado.
- `ConfirmDialog`: confirmación reusable para acciones sensibles futuras o existentes.

Las abstracciones son intencionalmente pequeñas. No intentan modelar formularios ni
dominio clínico y pueden reutilizarse en la ficha de paciente.

## Vistas intervenidas

### Estructura general

Las pestañas superiores se sustituyen por navegación lateral persistente en escritorio y
drawer en pantallas pequeñas. El AppBar conserva identidad, usuario, roles y cierre de
sesión. El módulo activo usa texto, icono, fondo y `aria-current="page"`. La lista visible
continúa derivándose de las reglas de roles existentes; no se alteran permisos.

### Login

El login introduce la identidad NutriWard con una composición sobria de marca y formulario.
Mantiene el flujo de autenticación, autocomplete, error de API y estado de envío, y evita
elementos decorativos en movimiento.

### Mapa de camas

El mapa funciona como vista piloto. Incorpora encabezado, resumen de camas, leyenda textual,
filtros agrupados, skeleton inicial y feedback unificado. Las camas libres, ocupadas, con
traslado y seleccionadas combinan color, borde, texto e icono. La selección expone
`aria-pressed`; el panel conserva retorno de foco. Los refrescos en segundo plano mantienen
el mapa anterior y muestran un indicador discreto, sin modificar la lógica de concurrencia,
intervalos, movimientos o traslados.

## Accesibilidad y responsive

- foco visible global de alto contraste y controles principales de al menos 40 px;
- enlace para saltar al contenido y navegación principal etiquetada;
- navegación activable con teclado y módulo activo mediante `aria-current`;
- estados operacionales expresados por texto, icono y borde además de color;
- carga mediante `role="status"`, feedback mediante alertas y `Snackbar`;
- cama seleccionada mediante `aria-pressed` y restauración de foco al cerrar el drawer;
- títulos y descripciones accesibles en diálogos compartidos;
- navegación lateral desde `md`, drawer móvil bajo `md` y grids que se compactan sin
  scroll horizontal global;
- geometría espacial de salas mantiene su scroll horizontal local cuando es necesario;
- reduced motion elimina transiciones perceptibles sin alterar funcionalidad.

## Decisiones abiertas para Fase 8

- definir la arquitectura de rutas profundas y breadcrumbs para la ficha clínica;
- validar la densidad final de tablas, formularios largos y paneles de evolución;
- completar tokens específicos para riesgos nutricionales y estados clínicos reales;
- decidir si la navegación futura requiere grupos colapsables al crecer los módulos;
- evaluar separación de bundles por ruta cuando existan vistas clínicas independientes;
- validar con usuarios clínicos vocabulario, jerarquía y contraste en puestos reales.

No se reservan rutas ni se muestran módulos ficticios de evaluaciones, diagnósticos,
requerimientos, prescripciones, regímenes o raciones en esta fase.

## Criterios de aceptación

- el tema centraliza identidad, semántica, geometría, bordes, sombras y movimiento;
- AppShell y navegación son responsive, accesibles y respetan roles existentes;
- login y mapa usan el nuevo lenguaje visual;
- el mapa conserva selección de servicio/sala, refresco, drawer, diálogos y traslados;
- estados de cama y traslado no dependen sólo del color;
- las vistas intervenidas consumen tokens en lugar de colores operacionales dispersos;
- pruebas de navegación por rol y componentes críticos permanecen verdes;
- frontend compila para producción y el verificador general sigue pasando;
- no hay backend, permisos, contratos API ni funcionalidades de Fase 8 modificados.

## Procedimiento de verificación

1. En `apps/frontend`, ejecutar `npm test -- --run`.
2. En `apps/frontend`, ejecutar `npm run build`.
3. Desde la raíz, ejecutar `powershell -ExecutionPolicy Bypass -File scripts_verify_phase7.ps1`.
4. Iniciar la aplicación con la infraestructura habitual o, para revisión aislada del
   frontend, con `npm run dev` y un backend disponible.
5. Comprobar login correcto y error de credenciales.
6. Para cada rol, comprobar módulos visibles, módulo inicial, navegación con teclado,
   usuario y cierre de sesión.
7. En mapa de camas, comprobar filtros, leyenda, resumen, selección por click y teclado,
   cierre/retorno de foco, refresco manual, refresco en segundo plano y error no bloqueante.
8. Comprobar drawer de ocupación y diálogos de movimiento/traslado.
9. Repetir en escritorio, tablet y móvil; revisar overflow horizontal y menú móvil.
10. Activar `prefers-reduced-motion` y confirmar que la interfaz permanece operativa.
