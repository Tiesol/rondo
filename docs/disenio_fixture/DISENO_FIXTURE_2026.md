# Diseño del fixture 2026 (T8.12)

**Fuente:** `Cancha_1.psd`, el diseño que pasó la organización. **Referencia visual:** `diseno_referencia.jpg`.

Es **una imagen por cancha y por día**, como hasta ahora. Todas las medidas están en píxeles del PSD, de 3840 × 2160 (16:9). Para generar el PNG a 1920 × 1080, se divide todo por 2.

## Archivos

| Archivo | Va en | Qué es |
|---|---|---|
| `fondo_fixture_3840.jpg` y `fondo_fixture_1920.jpg` | `src/torneo/static/png/` | El fondo con todo lo fijo ya aplicado: mármol, borde griego, "PROGRAMACIÓN" de fondo, la copa al 20 %, la franja azul y el logo de la JMP CUP abajo a la izquierda. **Es el fondo que se usa** |
| `copa_marca_de_agua.png` y `logo_jmp_cup.png` | `src/torneo/static/png/` | Las mismas piezas sueltas, con transparencia. Por si hace falta armar el fondo de otra forma; hoy no se usan |
| `fondo_marmol_solo_3840.jpg` | `src/torneo/static/png/` | El mármol sin nada encima. Hoy no se usa |
| `patrocinador_gree_blanco.png` | **No va al repo** | Se sube desde la app como patrocinador del torneo |

**Por qué el fondo trae todo aplicado:** la franja azul usa el modo de fusión "luz lineal" sobre el mármol, y la copa y "PROGRAMACIÓN" tienen opacidad. Copiarlo en HTML no queda igual. La app solo dibuja encima lo que cambia.

## Lo que dibuja la app

### Título

- **Texto:** `CANCHA 1 ~ SÁBADO 24`, en mayúsculas. En la fuente del diseño, el guion se ve como "~".
- **Posición:** centrado horizontalmente, con la línea base en y = 211. Ocupa de y = 76 a y = 217.
- **Tamaño:** 183 px.
- **Color:** `#072236`.
- **Más de una imagen por cancha:** si los partidos se reparten en varias imágenes, se agrega "1/2" al final.

### Filas de partidos

- **Columna:** de x = 1002 a x = 2889 (1887 px de ancho). Está un poco corrida a la derecha del centro, a propósito, como en el PSD.
- **Altura de cada fila:** 122 px. La primera empieza en y = 419; las siguientes, cada 120 px.
- **Bloques:** los partidos se agrupan por categoría. Entre un bloque y el siguiente queda un espacio de unos 90 a 110 px.
- **Colores:** las filas alternan, y cada bloque empieza con dorado.
  - Dorado: `#DFD07C` al 39 % de opacidad.
  - Blanco: `#F7F7F7` al 40 % de opacidad.
- **Límite:** las filas no pueden pasar de y = 1800, porque la franja azul empieza en 1823. Con espacios entre bloques **entran unas 10 filas**; si hay más, se arma otra imagen de la misma cancha ("1/2", "2/2").

Medidas dentro de una fila, contadas desde su borde superior:

| Elemento | Posición | Tamaño | Color |
|---|---|---|---|
| Equipo local | Centrado entre x = 1002 y x = 1829; línea base a +79 px | 60 px | `#072236` |
| Categoría ("SUB 5") | Centrada en x ≈ 1915; línea base a +43 px | 51 px | `#072236` |
| Hora ("15:30") | Centrada en x ≈ 1917, debajo de la categoría; línea base a +110 px | 72 px | `#B9A951` (dorado) |
| Equipo visitante | Centrado entre x = 2005 y x = 2889; línea base a +79 px | 60 px | `#072236` |

- **Mayúsculas:** todo el texto va en mayúsculas.
- **Nombres largos:** si un nombre no entra en su mitad, se achica la letra hasta un mínimo de 46 px; si igual no entra, se corta con "…".
- **Categoría:** se muestra solo la categoría ("SUB 7"). Si en esa cancha y ese día juegan Inicial y Avanzado de la misma categoría, se agrega la inicial del nivel: "SUB 7 A" y "SUB 7 I".

### Patrocinadores

- **Zona:** la franja azul, a la derecha del logo de la JMP CUP. Va de x ≈ 588 hasta el borde derecho, con el centro vertical en y ≈ 1984.
- **Tamaño:** cada logo, hasta 108 px de alto, en el orden del torneo y separados por unos 80 px.
- **Color:** en el PSD, el logo de GREE está pintado de blanco. Los logos se suben en blanco con fondo transparente. Si alguno viene en color, la app lo pasa a blanco: en CSS, `filter: brightness(0) invert(1)`.
- **Sin patrocinadores:** la franja queda solo con el logo.

## Fuente

- **El diseño usa RomanSD.** El PSD no trae el archivo de la fuente, solo el nombre.
- **Licencia:** no está clara. El aviso dice "Copyright (c) 1999 by Steve Deffeyes. All rights reserved". La app la usaría como fuente web, así que necesita el archivo (.ttf u .otf) y confirmar que se puede usar.
- **Mientras tanto:** usar **Cinzel** (Google Fonts, licencia OFL), servida desde la app como las otras fuentes. Es la que más se parece: mayúsculas romanas clásicas. Si llega el archivo de RomanSD con una licencia que lo permita, se cambia.

## Detalles

- **Datos de ejemplo:** el PSD tiene todas las horas en 15:30 y los equipos repetidos. Es la plantilla, no hay que copiarlos.
- **Escudos:** este diseño no tiene escudos. Para el PNG no hacen falta; para la página pública, sí.
- **Repo:** el fondo pesa 0,7 MB a 3840 px y 0,3 MB a 1920 px. Si el PNG se arma a 1920 × 1080, alcanza con `fondo_fixture_1920.jpg`.
