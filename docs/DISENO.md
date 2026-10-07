# Diseño de la interfaz

Contrato de diseño, armado con la skill `frontend-ui-engineering`. Vale para el prototipo y para las pantallas en Django.

## Referencias

| Referencia | Qué se toma | Qué no |
|---|---|---|
| PNG de fixture 2025 de la JMP CUP | La identidad: azul marino, dorado y blanco; títulos condensados en mayúsculas; filas con escudo, equipo y hora | La textura de fondo y los degradados: son para la imagen, no para la app |
| Copa Fácil (la página pública de la JMP CUP 2025) | La estructura: torneo → categoría → pestañas; partidos en listas con escudos; la página pública solo de lectura | Su marca, sus textos y su diseño exacto |
| Prototipo 1 (rechazado el 2026-10-07) | El flujo: asistente, avisos al cargar listas, capacidad y propuestas | Una tarjeta para todo, el verde inventado, sombras y radios grandes |

## Tokens

- **Color:**
  - azul marino `#0d2440` para el encabezado y las acciones principales;
  - dorado `#f2cf3a` para resaltar: pestaña activa, selección y el detalle de marca. Nunca como texto sobre blanco, porque no tiene contraste;
  - blanco y grises con un leve tinte azul para las superficies.
  - El estado (bien, aviso, error, información) usa colores semánticos propios, siempre acompañados de texto o un ícono, nunca solo color.
- **Tipografía:** Bebas Neue para los títulos y los números de marcador (como "FIXTURE" y "JMP CUP"); Figtree para todo lo demás. Los números de tablas y horas van con cifras tabulares.
- **Forma:** radio de 8 px en los controles y de 12 px en las hojas inferiores. Sin sombras, salvo en la hoja inferior y el aviso flotante.
- **Espaciado:** escala de 4 px (4, 8, 12, 16, 24, 32).

## Patrones

- **Listas con divisores, no tarjetas.** Una sección es un título más una lista. Las tarjetas se reservan para lo que de verdad es un objeto aparte (una propuesta de reprogramación).
- **Encabezado azul marino** con la identidad del torneo en las pantallas principales.
- **Pestañas subrayadas,** con la activa marcada en dorado.
- **Chips de estado con texto:** "Faltan 2", "4 sin verificar", "Choque con un profe".
- **Una acción principal por pantalla,** en azul marino. Las demás son enlaces o botones secundarios.
- **Navegación:** en el celular, una barra inferior con Inicio, Torneo, Calendario y Más. Desde 900 px, una barra lateral, con el contenido a un máximo de 960 px.

## Pantallas

| Pantalla | Para qué sirve | Acción principal | Estados |
|---|---|---|---|
| Inicio | Ver cómo va el torneo y qué necesita atención | Ir a lo pendiente | Torneo sin crear (vacío) o en curso |
| Crear torneo | Armar el torneo desde la plantilla del reglamento | Crear el torneo | 4 pasos, con validación en cada uno |
| Torneo | Ver una categoría: equipos, fixture, posiciones y ajustes | Agregar un equipo | Categoría sin equipos; posiciones sin resultados |
| Equipo | Cargar y verificar el plantel | Agregar un jugador | Bajo el mínimo, sin verificar, sin dorsal |
| Agregar jugador | Cargar a una persona con avisos al instante | Guardar | Aviso (se guarda) y error (bloquea) |
| Programar | Ver si entra todo y programar | Programar | Capacidad insuficiente, programando, resultado con partidos sin lugar |
| Calendario | Ver un día por cancha y compartir la imagen | Compartir el día | Día sin partidos |
| Partido de la ACF | Cargar un bloqueo y elegir una propuesta | Aplicar la propuesta | Sin choque; con choque y propuestas |
| Más | Personas y roles, datos de la escuela y torneos | Invitar a alguien | Mesa de control: sin acceso a configurar |
| Página pública | Que familias y clubes vean partidos y posiciones, sin login | Elegir categoría y día | Sin partidos todavía. **Nunca muestra datos personales** |

## Roles

La Mesa de control ve las mismas pantallas, pero sin Crear torneo, Programar, Partido de la ACF ni los ajustes de categoría. Donde no tiene permiso, la pantalla lo dice ("Solo la organización puede…") en lugar de esconder el contenido sin explicación.
