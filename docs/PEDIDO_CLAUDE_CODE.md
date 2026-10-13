# Pedido para Claude Code: lo que falta para la JMP CUP 2026

**De:** Sebastian. **Fecha:** 2026-10-12.

La organización aprobó la app y la va a usar en el torneo 2026. Además, **Rondo reemplaza a Copa Fácil**: resultados, goles, tarjetas, tabla, goleadores y fotos para las familias.

**Leer junto con:**
- `REVISION_RONDO_FASE4.md`: revisión externa, puntos 1 y 2.
- `CONVOCATORIA_2026_PARA_RONDO.md`: cambios de la convocatoria. Los ajustes de abajo mandan sobre ese archivo.
- `PREGUNTAS_JMP_CUP_2026.md`: todas las preguntas para el organizador (P1 a P77) y su valor por defecto. Cópialo a `docs/` y úsalo como fuente de las P.

## Fechas que mandan

| Fecha | Qué pasa |
|---|---|
| Martes 13/10 | La organización prueba la demo: carga de equipos y listas, fixture y programación |
| Miércoles 21/10, 12:00 | Cierre de listas. Esa tarde se arman fixtures y calendario |
| Viernes 23/10 | Se publica la 1.ª fecha |
| Sábado 24/10 al domingo 15/11 | Torneo: 4 fines de semana, viernes, sábado y domingo |

## Cómo trabajar este pedido (autorizado por Sebastian)

- **Preguntas sin respuesta:** no frenan. Cada una queda configurable, con el valor por defecto de `PREGUNTAS_JMP_CUP_2026.md` y un TODO con su P#. Cuando llegue la respuesta, se cambia el valor y no el código.
- **Dependencias aprobadas para este pedido:**
  - `django-storages[s3]` (incluye `boto3`), para las imágenes en Cloudflare R2;
  - `Pillow`, para achicar las fotos y limpiarlas.

  Cualquier otra se pregunta.
- **Durante la prueba del martes 13/10:** cada fusión a `main` reinicia la demo. Fusiona solo cuando Sebastian avise que terminaron. Nunca corras `generar_demo` en la demo: borra lo que cargó la organización.
- **Lo que no cambia:** siguen valiendo los límites de SPEC.md. Datos reales, solo en producción. Producción y nube, con el visto bueno de Sebastian.

---

## Bloque A. Hasta el miércoles 14/10: calendario y carga de listas

**A1. Revisión externa, puntos 1 y 2.**
- La eliminación respeta el turno libre de P17 entre llaves encadenadas: el ganador o perdedor de una llave, como un equipo virtual. También el verificador.
- Los profes pueden tener partidos seguidos en la misma cancha; el margen de P35 se pide solo si cambian de cancha.
- Sumar el objetivo blando de reducir la espera de los profes (PRO-11).
- P57: por defecto, el choque de profes cuenta solo para el **entrenador**, configurable.

**A2. Convocatoria 2026**, según `CONVOCATORIA_2026_PARA_RONDO.md`, con estos ajustes:
- Plantilla del torneo: del 24/10 al 15/11; eliminación desde el 4.º fin de semana; cierre de inscripción el 21/10 a las 12:00.
- Al agregar un día entre semana, proponer el jueves.
- Agregar la modalidad `F6`, con su migración. Sub 5 y Sub 6 pasan a F6 y siguen en C1A y C1B (P63).
- **No ocultes "Posiciones"**: ahora Rondo calcula la tabla (Bloque B).
- **Bronce con 10 equipos (P62):** que sea una regla con interruptor en la pantalla de reglas. Por defecto, apagada: con 10 equipos son 26 partidos.
- **Sub 15 Femenino (P61):** que quede destildada por defecto en el asistente, pero disponible.
- **Sub 10 y Sub 11 Avanzado (P60):** quedan en F8. Si la respuesta es F11, es un cambio de configuración.

**A3. Fecha de nacimiento.** Aceptar solo el año: la regla de edad usa solo el año. En una prueba con las listas reales de 2023, 3 listas (38 chicos) traían solo el año y se rechazaban. Si se carga solo el año, mostrar "fecha incompleta"; no es un error.

**A4. Pegar listas** en la ficha del equipo. Los clubes mandan sus listas en formatos distintos: en 2023 hubo cinco, entre Excel, Word y PDF pasado a Excel (CONTEXTO 6.5). La organización abre el archivo que mandó el club, copia las filas de jugadores y las pega en Rondo. Una tabla de Word también se pega así.
- **Columnas:** después de pegar, se muestran las primeras filas y la organización elige qué es cada columna: nombres, apellidos, nombre completo, fecha o año de nacimiento, documento, dorsal o ignorar. Si viene el nombre completo en una columna, se propone separarlo (las dos últimas palabras como apellidos) y se puede corregir.
- **Fechas:** se aceptan dd/mm/aaaa, fecha de Excel, "12 de marzo 2014" y solo el año. Si una lista entera viene en mm/dd/aaaa (se nota porque el segundo número pasa de 12), se avisa y se corrige toda la lista.
- **Vista previa:** con los errores y avisos de cada fila, los mismos que la carga a mano. Se guardan las filas sin errores; las que tienen error quedan marcadas para corregirlas.
- **Cuerpo técnico:** lo mismo, con el rol. El rol se reconoce aunque venga escrito de distintas formas ("D.T", "DT", "Director técnico").
- **Para 2027:** subir el archivo de la planilla oficial. No va ahora: las listas de 2026 ya están llegando en el formato de cada club.

Son unos 1.300 jugadores: a mano serían más de 10 horas de tipeo.

**A5. Producción (T6.5).** Prepáralo todo y deja en `docs/DESPLIEGUE.md` los pasos que hace Sebastian.
- Un servicio aparte en Render Standard (1 CPU), **sin despliegue automático**.
- Neon de producción en **N. Virginia**, la misma región que Render, en plan Launch con 7 días de historia. Viene en 1: hay que cambiarlo.
- `RONDO_PROGRAMADOR_SEGUNDOS` en 120.
- Usuarios reales.

**A6. Borrador del calendario antes del cierre.** La organización va a armar fixture y calendario varias veces mientras llegan las listas, para ver si entra todo y revisarlo a mano. El definitivo se arma el 21/10, después del cierre.
- Mientras la página pública esté apagada, el calendario interno y el PNG dicen **"Borrador"**.
- Si se agrega o se saca un equipo de una categoría que ya tiene fixture, avisar "El fixture de esta categoría está desactualizado" y ofrecer rehacerlo. Hoy no hay ningún aviso.
- Rehacer y volver a programar se puede todas las veces que haga falta, mientras no haya partidos jugados.

**A7. Medir.** Con la plantilla 2026 y la demo, programar con 1 CPU y reportar en PROGRESO.md:
- partidos ubicados;
- tiempo;
- estado del solver;
- espera de los profes;
- llaves encadenadas.

---

## Bloque B. Antes del viernes 23/10: reemplazar a Copa Fácil

Si algo de esto no llega, la 1.ª fecha va en Copa Fácil (P77). Prioridad dentro del bloque: B1 → B2 → B3 → B4 → B6 → B5 → B7 → B8.

**B1. Almacenamiento de imágenes, conectable.**
- **Backend:** `django-storages` con S3, apuntando a Cloudflare R2. El bucket es **privado**; las imágenes se sirven con URL firmadas que vencen. No hace falta un dominio propio.
- **Variables de entorno:** `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` y `R2_BUCKET`.
- **Sin esas variables:**
  - en desarrollo y tests se usa el disco local;
  - en producción o en la demo, los botones de subir imagen se ven desactivados, con el mensaje "Falta conectar el almacenamiento de imágenes".

  Así la app funciona antes de que Sebastian conecte R2.
- **Al subir una imagen:**
  - se achica, a unos 800 px para fotos y 400 px para escudos;
  - se guarda en WebP o JPEG;
  - **se borran los metadatos (EXIF, incluida la ubicación GPS)**.
- **Validaciones:** solo imágenes, con un tamaño máximo.

**B2. Qué imágenes se suben.**

| Imagen | Dónde | Quién la sube | Pregunta |
|---|---|---|---|
| Escudo del club | Club | La organización | P68 |
| Foto de la persona | Persona: sirve para jugador y profe | La organización o la mesa | P67 |
| Logo del organizador | Datos de la escuela | La organización | — |
| Patrocinadores | Por torneo: imagen, nombre y orden | La organización | P69 |

La foto de cada jugador es como en Copa Fácil: el jugador manda una foto suya con el uniforme y la organización la sube (P75). No hay galería de fotos de partidos.

**Autorización de foto (P66):** una casilla por jugador, "autoriza foto y nombre", apagada por defecto. Al subir la foto, el formulario pregunta si la familia la mandó para publicarla. Sin autorización, la foto no se muestra en ningún lado público, aunque esté cargada.

**B3. Ficha del partido**, para cargarla desde el celular durante el partido.
- **Estado:** por jugar, en juego o terminado.
- **Botones grandes:** "Gol", "Amarilla" y "Roja". Cada uno abre la lista del equipo, con dorsal y nombre.
- **Además:** gol en contra (P72), deshacer el último, mejor jugador (P70), W.O. con el marcador de P23 y penales en la eliminación.
- **Permisos:** organización y mesa (P64). Cada evento queda con quién y cuándo.
- **Aviso:** si un jugador suspendido figura en el partido, se ve el aviso.

**B4. Tabla de posiciones automática** por categoría y serie.
- **Puntos:** 3, 1 y 0.
- **Desempate:** en el orden de la sección 4.6 del contexto. Es configurable.
  - Con equipos que no jugaron entre sí, P34.
  - Mejor perdedor y mejor 3.º, P26.
  - Si llega a sorteo, lo registra la organización (P28).
- **Fair play:** sale de las tarjetas.

**B5. Suspensiones.**
- Doble amarilla en Sub 10 a Sub 17: roja. Hay una casilla "pagó Bs 30" (P74); si no pagó, el jugador queda suspendido para el próximo partido.
- Roja directa y acumuladas: configurable, por defecto sin suspensión automática (P29). La organización puede marcar una suspensión a mano.

**B6. Eliminación automática (P50).** Al terminar la fase de grupos, la app propone los cruces desde la tabla. Se pueden corregir a mano y se verifican antes de guardar.

**B7. Página pública como la de Copa Fácil**, con datos en vivo que se actualizan cada minuto.

| Página | Qué muestra |
|---|---|
| Partidos | Resultados del día, en vivo |
| Posiciones | La tabla de cada categoría y serie |
| Goleadores | Por categoría (P71) |
| Ficha del partido | Goles, tarjetas y mejor jugador |
| Equipo | Escudo y plantel, con foto solo si hay autorización |
| Patrocinadores | Al pie de la página |

- **Privacidad (P65):** "Nombre I." y dorsal. Nunca el CI ni la fecha de nacimiento. Un test lo comprueba, como el que ya existe.
- **Caché:** cachear las páginas públicas unos 30 a 60 segundos, para aguantar más de 100 visitas a la vez con 1 CPU.

**B8. PNG del fixture con el diseño 2026.** Sebastian va a pasar las imágenes sacadas del PSD.
- **Fijas del diseño** (fondo, copa, adornos): van en el repo, en `src/torneo/static/png/`.
- **Escudos:** salen del club.
- **Patrocinadores:** salen del torneo.
- **Textos** (equipos, hora, cancha): los pone la app, no van dentro de la imagen.

---

## Bloque C. Durante el torneo

- **Retención (P49 y P76):** `anonimizar_torneo` también borra las fotos de las personas del bucket.
- **Pantalla de suspendidos:** la lista para la mesa en cada fecha.

## Conexiones que quedan libres (las conecta Sebastian)

La app tiene que funcionar sin ellas y decir qué falta. Todo va por variables de entorno.

- **Cloudflare R2:** bucket, claves y cuenta.
- **Render de producción y Neon de producción.**
- **Dominio propio:** opcional. Si se agrega, va en `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` por variable.

## Al terminar cada bloque

- Verde.
- Revisión de cierre.
- Actualizar PROGRESO.md con las decisiones y las P que quedaron como TODO.
- Avisar a Sebastian qué tiene que probar.
