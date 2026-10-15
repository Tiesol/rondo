# Pendientes después de pasar a producción

Lista para Sebastian, al 2026-10-14. Las preguntas se responden en otro chat; los fallos de la prueba en producción se mandan uno por uno.

## 1. Producción: lo que falta

- [ ] **Manual Deploy → Deploy latest commit** en `rondo-produccion`, para que tome las variables de R2. El único deploy es el primero, de antes de cargarlas.
- [x] Probar R2: el logo se subió y se ve (2026-10-14).
- [ ] Revisar en Settings que **Auto-Deploy** esté en *No*.
- [ ] Prueba del flujo completo, sin programar el fixture mientras esté en Free (0,1 CPU).
- [ ] Vaciar la base después de la prueba:
  1. En Neon, proyecto `rondo-produccion`, rama `production`, base `rondo`, en el SQL Editor: `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`
  2. En Render, **Manual Deploy**. Las migraciones vuelven a crear las tablas.
  3. Volver a correr `crear_usuario sebastian --admin` y `cargar_clubes` desde tu máquina.
  4. En R2, borrar la carpeta `rondo/` del bucket.
- [ ] Crear el torneo real con el asistente y los usuarios de la organización (todos con el rol Organización).
- [ ] **Antes del 21/10:** subir Render a **$25/mes (1 CPU, 2 GB)** en Compute, con la cuenta en Hobby ($0). Sin eso, no programar el fixture.
- [ ] Decidir Neon: plan Launch con 7 días de historia, o seguir gratis y crear una rama de respaldo antes de cada cosa delicada.
- [ ] Opcional: dominio propio. Se agrega en Render (Custom Domains) y lleva `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`.

## 1b. Fallos y pedidos de la prueba en producción (para hacer)

- [ ] **El logo de Escuela no se usa en todos lados.** Solo sale en la barra de arriba. Siguen mostrando la sigla "JMP", aunque haya logo:
  - el menú lateral ([navegacion.html:3](../src/torneo/templates/parciales/navegacion.html));
  - el login ([login.html:5](../src/torneo/templates/registration/login.html));
  - la página pública de la categoría ([categoria.html:11](../src/torneo/templates/publico/categoria.html)).

  La ayuda de Escuela promete que aparece en la página pública. Arreglo: logo en los cuatro lugares, y la sigla solo si no hay logo. Agregar un test.
- [ ] **Sin favicon:** la pestaña muestra el globo genérico. Falta `<link rel="icon">` en `base.html`. Usar el logo de Escuela y un ícono fijo si no hay.
- [ ] **El logo se ve muy chico,** sobre todo en el celular: hoy mide 34 px (`.marca` en `frontend/tailwind.css`; 52 px con `.grande`). La marca de la JMP tiene que verse. Hacerlo más grande en la barra, el menú lateral, el login y la página pública (por ejemplo, de 44 a 48 px en la barra y de 72 a 96 px en el login y la cabecera pública), revisado con capturas a 360 px. No pesa más: el archivo es el mismo (400 px en WebP), y se ve nítido hasta unos 200 px.

- [ ] **No se puede borrar un club.** Solo se puede editar o "unir" con otro (para duplicados). Propuesta: "Borrar club", solo si no tiene equipos en ningún torneo (la base ya lo protege con `PROTECT`). Con equipos, la app explica por qué no se puede.
- [ ] **No se puede borrar ni retirar un equipo.** Si se creó por error, en una categoría equivocada o con el club equivocado, o si el equipo se baja del torneo, no hay forma de sacarlo desde la app. Propuesta:
  - **Sin partidos jugados:** "Borrar equipo", con confirmación. Se borran también su plantel y su cuerpo técnico en ese torneo, y el fixture de la categoría queda desactualizado (se rehace).
  - **Con partidos jugados:** "Retirar del torneo". Qué pasa con sus partidos jugados y con los que faltan es una regla del reglamento: pregunta **P87**.
  - Mientras tanto, se puede cambiar la categoría o el club de un equipo mal cargado (revisar si la ficha lo deja).

- [ ] **Escudo por equipo, no por club (requerimiento confirmado por la organización el 2026-10-14; responde P68).**
  - **Qué pidieron:** el club no tiene escudo. Un club tiene equipos, y **cada equipo tiene su escudo, obligatorio**. Un club puede tener **cualquier cantidad de equipos**, con nombres distintos, cada uno con su propio escudo. No hay límite.
  - **Lo que hay hoy:** `Club.escudo` (uno por club, migración 0018) y lo comparten todos sus equipos. En el código, `Equipo` es "un club en una categoría-nivel" y tiene `nombre`. Un mismo equipo (mismo club y mismo nombre) aparece una vez por cada categoría en la que juega.
  - **Cómo hacerlo (propuesta):**
    1. **El escudo va con el equipo del club (club + nombre), no con cada fila de `Equipo` por categoría.** Si no, habría que subir el mismo escudo una vez por categoría. Opción recomendada: un modelo nuevo, por ejemplo `EquipoDeClub` (club, nombre, escudo; único por club y nombre, sin límite de equipos por club), y `Equipo` (por categoría) apunta a él. El nombre visible sale de ahí.
    2. **Sacar `Club.escudo`.** Migración que pase el escudo de cada club a sus equipos (en producción no hay datos reales todavía; en la demo, se copia). Preguntar antes si ya hay datos reales.
    3. **Todas las pantallas que hoy muestran el escudo del club pasan a usar el del equipo:** la ficha del equipo, el fixture, la ficha del partido, Hoy, la página pública, el PNG del fixture y la caché de escudos (`olvidar_escudos`). Archivos que lo usan hoy: `presentacion.py`, `servicios/publico.py`, `servicios/imagenes.py`, `servicios/clubes.py`, `servicios/hoy.py` y las vistas `imagenes`, `publico`, `fixture`, `ficha_partido`, `equipos`, `clubes`, `png` y `diagnostico`.
    4. **Dónde se sube:** en la ficha del equipo ("Escudo de <equipo>") y en la pantalla del club, con la lista de sus equipos y el escudo de cada uno. La ruta pública `/imagen/escudo/<id>/` pasa a ser por equipo.
    5. **Unir clubes** (`unir_clubes`): ahora tiene que mover también los equipos del club y sus escudos, y avisar si quedan dos con el mismo nombre.
    6. **"Obligatorio" (respuesta a P88):** el escudo se puede poner en cualquier momento; no bloquea nada. Mientras falte alguno, **Inicio siempre muestra el pendiente "N equipos sin escudo"**, y al tocarlo se ve la lista de los equipos que no lo tienen, cada uno con su enlace para subirlo. El PNG y la página pública muestran la sigla mientras falte.
    7. Tests: escudo distinto para varios equipos del mismo club, el mismo escudo en todas las categorías de un equipo, el pendiente de Inicio y su lista, unir clubes y el PNG con el escudo del equipo.
  - **P89, respondida:** dos inscritos del mismo club en una categoría son siempre dos equipos distintos, con nombre distinto y su propio escudo. No existe el caso "<equipo> A" y "<equipo> B" con el mismo escudo. Por eso el escudo va por club + nombre: el nombre identifica al equipo en todas sus categorías.

### Crear torneo y Reglas (prueba del 2026-10-15)

- [ ] **Paso "Canchas y horarios" del asistente:** de canchas solo muestra un texto, no deja ver, agregar ni partir canchas. Hoy eso está en Más → Canchas, después de crear el torneo. Opciones: sumar al paso la lista de canchas con "Agregar" y "Partir", igual que Más → Canchas, o llamar al paso "Horarios" y decir dónde se cambian las canchas. Recomendado: lo primero.
- [ ] **Sacar las etiquetas P6, P42, P9, etc.** de Reglas y del asistente. Son para nosotros, no para la organización. En Inicio, "Reglas del torneo" dice "con su pregunta al organizador": cambiar también ese texto.
- [ ] **Sacar la regla "Jugador en dos equipos" (P7)** de Reglas y del asistente. Sebastian ya había pedido quitarla porque no tiene sentido. Revisar qué valida hoy antes de sacarla, y dejar el comportamiento que corresponda por defecto.
- [ ] **Explicar mejor "Cierre de la inscripción":** "fuera de plazo" no se entiende. Texto propuesto: "Después de esta fecha se puede seguir inscribiendo, pero la app marca esos equipos y jugadores como tardíos."
- [ ] **"Fin de semana sugerido para la eliminación" no se entiende.** Texto propuesto: "En qué fin de semana van las semis y finales (1 = el primero del torneo). Si los grupos terminan antes, se pueden jugar antes." Mejor como lista desplegable con las fechas reales ("4.º: 14 y 15/11"), no como número.
- [ ] **Reprogramar no se encuentra.** Las propuestas solo aparecen desde Inicio → "Cargar un partido de la ACF" (bloqueos) y al suspender un día. No hay un botón claro "Reprogramar" con el motivo. Propuesta: un "Reprogramar" en la ficha del partido y en el calendario del día, que pida el motivo (el equipo no puede, lluvia, cancha, ACF, otro) y lleve a las propuestas. Revisar también el nombre "ACF" en Inicio.
- [ ] **"Día para reprogramar" (jueves) se confunde.** Hoy solo sirve como día que la app sugiere al agregar un día después de suspender uno (lluvia); igual se puede elegir cualquier día. Texto propuesto: "Día que la app sugiere primero al reprogramar un día suspendido. Se puede elegir otro." O sacar la regla y sugerir siempre el próximo día libre.
- [ ] **"Desempate en la tabla": acortar la descripción.** Propuesta: "Reglamento 2025: puntos entre los empatados, goles a favor, goles en contra, fair play y sorteo. Excel 2023: diferencia de gol y goles a favor."
- [ ] **"Doble amarilla es roja desde Sub" con número + y −:** cambiar por una lista desplegable con las categorías del torneo ("Sub 10", "Sub 11"…), para que solo se pueda elegir una que existe. Hacer lo mismo en cualquier otra regla que pida un "Sub" con número.
- [ ] **El pendiente "28 reglas esperan la respuesta del organizador" no se va nunca.** `servicios/pendientes.py` cuenta todas las reglas que tienen una P, sin mirar si el torneo ya las definió. Se definen al crear el torneo, así que no debería aparecer. Propuesta: sacar el pendiente; si se quiere algo, que sea "Revisa las reglas" una sola vez, hasta que alguien guarde la pantalla de Reglas.
- [ ] **Después de armar el fixture no queda claro que falta programarlo.** El calendario aparece vacío hasta usar "Programar partidos". Propuesta: en la pestaña Fixture, y como pendiente en Inicio, "N partidos sin día ni hora → Programar".
- [ ] **Posiciones muestra "Falta sorteo" en todos los equipos antes de jugar.** Con todos en 0 puntos, la tabla los ve empatados y pide sorteo. No debería pedirlo hasta que la serie termine (o al menos hasta que haya partidos jugados). Además, "Registrar el sorteo (P28)" muestra la P: sacarla.
- [ ] **Series cruzadas (6 y 7 equipos) no se entienden en pantalla.** Fixture y Posiciones muestran "Serie A" y "Serie B", pero cada equipo de A juega contra los de B, no contra los de su serie. Propuesta: un texto en el fixture ("Series cruzadas: cada equipo de A juega con todos los de B. Las semis de Oro son 1.º A vs 2.º A y 1.º B vs 2.º B"). Además, con series cruzadas, "separar clubes" hace que los dos equipos del mismo club **sí** se enfrenten en grupos. Pero ponerlos en la misma serie los puede cruzar en la semi de Oro (1.º A vs 2.º A): ver P90.
- [ ] **Editar el fixture a mano (pedido de Sebastian, 2026-10-15).** Hoy se pueden cambiar las series (y el fixture se rehace), y mover o intercambiar partidos ya programados, pero no cambiar **quién juega contra quién en cada fecha**. Lo que piden:
  - En la pestaña Fixture, cambiar los cruces de una fecha a mano. Por ejemplo, si la fecha 1 tiene A vs B y C vs D, y la fecha 2 tiene A vs D y B vs C, poder adelantar A vs D a la fecha 1 (intercambiando cruces entre fechas) o armar un cruce eligiendo los dos equipos.
  - **Bloquea:** un equipo con dos partidos en la misma fecha, y un cruce entre equipos que no corresponde al formato (por ejemplo, en series cruzadas, dos de la misma serie).
  - **Avisa, sin bloquear:** a qué equipo le falta jugar contra cuál y qué cruce quedó repetido, hasta que el fixture vuelva a estar completo.
  - **Lo editado a mano se respeta:** al volver a programar o rehacer, la app no lo deshace. Después de editar, la organización elige entre "Reprogramar lo demás" (la app ubica lo que cambió y respeta lo demás) o "Dejarlo así".
  - El día y la hora siguen con Mover e Intercambiar, que ya bloquean lo físico (la misma cancha a la misma hora, un equipo en dos partidos a la vez) y avisan de lo demás (un profe con otro equipo jugando a esa hora, descanso, cancha, orden de fechas), con "Mover igual". Sumar en Mover **"Horarios libres sugeridos"** (se puede hacer, sin solver): recorrer los inicios posibles (franjas de los días del torneo × canchas compatibles con la categoría), pasar cada uno por el verificador que ya usan Mover e Intercambiar, y mostrar primero los que no tienen ningún choque ni aviso, ordenados por cercanía al horario actual (mismo día, mismo fin de semana, después el resto), unos 5 a 10 con "Mover aquí". Debajo, los que solo tienen avisos, con el motivo. El verificador ya es rápido (el listado de Intercambiar tarda 0,x s con 223 partidos). Si se quiere mover también otros partidos para hacer lugar, ya existe la reprogramación con solver (`dominio/programador/reprogramar.py`).
  - **Opción "Fijar" por partido (pedido de Sebastian, 2026-10-15).** Un interruptor "Fijar este partido" en Mover, en la ficha y en el calendario, con un ícono de candado. Un partido fijado no lo mueve nada automático: ni programar (todo o lo que falta), ni rehacer el fixture, ni las propuestas de reprogramar. Se mueve solo a mano, y "Desfijar" lo libera. Es **opcional**: mover no fija solo. T11.2 sacó `Partido.fijado` porque mover lo fijaba sin preguntar; ahora vuelve como una decisión explícita. Si un fijado choca con algo nuevo (por ejemplo, se suspende el día), la app avisa y propone, pero no lo mueve sin confirmación.
### PNG del día (Compartir el día)

- [ ] **La imagen descargada sale mal: recortada y agrandada.** En la app se ve entera, pero el archivo descargado (en la PC, 2026-10-15) muestra solo la esquina de arriba a la izquierda, ampliada: "CANCHA 3" cortado y una sola fila a medias. Parece un problema de escala al capturar (el `devicePixelRatio` o el tamaño del contenedor contra los 1920 × 1080). Revisar en la PC y en el celular, con un test si se puede.
- [ ] **Todo se ve chico, sobre todo con pocos partidos.** Las filas tienen un tamaño fijo, pensado para un día lleno. Propuesta: que el tamaño de las filas, la letra y los escudos dependa de cuántos partidos tiene la cancha ese día. Con pocos, filas más altas y escudos grandes; con muchos, como ahora, y si no entran, sigue partiendo en "1/2". Con un tamaño mínimo que se lea en el celular.
- [ ] **Escudos diminutos y con fondo blanco.** La app conserva la transparencia si el archivo la tiene (PNG o WebP), pero **no quita el fondo**: un JPG, o un PNG con fondo blanco, sale con su recuadro blanco. Opciones:
  - avisar al subir: "Este escudo tiene fondo; para que se vea mejor, sube un PNG sin fondo";
  - quitar el fondo automáticamente cuando es un color liso en los bordes (blanco o casi blanco). Es simple y sin dependencias nuevas, pero puede comerse partes blancas del escudo que tocan el borde: mostrar la vista previa antes de guardar, con "Usar el original".

  Quitar fondos complejos (fotos) necesitaría una librería nueva: hay que aprobarla.
- [ ] **Sacar el sello "BORRADOR" del centro del PNG.** Hoy sale mientras la página pública está apagada y tapa el fondo. Sacarlo, o como mucho dejar un texto chico en una esquina.

### Programar y "¿Entra todo?"

- [ ] **"16 de 88 h" no se entiende.** Son las horas que usan los partidos de esa cancha contra las horas que tiene la cancha en todo el torneo: 14 partidos de Sub 14 Avanzado, de unos 70 minutos, dan unas 16 h. Propuesta: decirlo en palabras, por ejemplo "Cancha 3: 14 partidos (16 h) de 88 h disponibles en el torneo. Entran unos 60 partidos más de 70 min.", y listar qué categorías juegan en esa cancha.

### Partido de la ACF, bloqueos y propuestas

- [ ] **La pantalla se llama "Partido de la ACF", pero sirve para cualquier bloqueo** (un equipo que no puede jugar un día y horario). El campo "Motivo" solo es un texto que queda en la lista y en el historial; con "ACF" en el título parece redundante. Propuesta: llamarla "Un equipo no puede jugar" (o "Reprogramar"), con el motivo como lista (ACF, viaje, exámenes, otro) y la ACF como la primera opción. Va junto con el botón "Reprogramar" de la ficha y el calendario.
- [ ] **Desde un bloqueo no se puede mover a mano.** Solo se ven las propuestas automáticas. Propuesta: en cada partido que choca, "Mover a mano" (lleva a Mover, con los horarios libres sugeridos) e "Intercambiar".
- [ ] **Las propuestas 2 y 3 mueven un partido que no hace falta mover.** Prueba: bloqueo de JMP Academy, sábado 24 de 8 a 12. La propuesta 1 (recomendada) mueve el partido que choca a las 12:00 del mismo día: bien. Las propuestas 2 y 3 hacen lo mismo y además mueven otro partido del domingo 1 al viernes 30, sin motivo visible. La app pide 3 propuestas distintas (regla "Propuestas al reprogramar") y, si solo hay una forma de mover un partido, completa las otras moviendo de más. Propuesta: que las alternativas sean otras formas de mover **solo lo que choca** (otro horario u otro día), y si no hay más, mostrar solo las que hay. Cada propuesta tiene que decir **por qué** mueve cada partido ("choca con el bloqueo", "para que X no juegue dos veces el mismo día").
- [ ] **"Aflojar reglas solo esta vez" aparece dos veces** (en el bloqueo y en las propuestas) y con campos vacíos que no se entienden. Propuesta: dejarlo solo en Propuestas, plegado y con un texto de cuándo usarlo ("Si ninguna propuesta te sirve"). Cada campo tiene que mostrar el valor actual del torneo ("hoy: 1 turno libre", "hoy: 2 por día") y no aparecer vacío. "Usar mitades de cancha" solo sirve para F6 y F7: decirlo, o esconderlo cuando los partidos que chocan son de F11.
- [ ] **Un bloqueo con choques no se ve fuera de su pantalla.** Ni Inicio, ni el calendario, ni la ficha del partido dicen que hay un partido que choca con un bloqueo. Propuesta: un pendiente en Inicio ("1 partido choca con un bloqueo → Resolver"), una marca en el partido en el calendario y en el fixture, y desde ahí las dos salidas: "Mover a mano" (con horarios sugeridos) o "Ver propuestas".
- [ ] **"Usar mitades de cancha" cuando chocan partidos de F11:** no mostrar la opción (no sirve de nada). Si chocan partidos de varias modalidades, mostrarla con el aviso "Solo para F6 y F7".
- [ ] **El selector de equipos del bloqueo no escala.** Es una lista con todos los equipos del torneo (con 93 equipos es inmanejable). Propuesta: primero elegir el club (o buscar escribiendo) y después marcar sus equipos, con la categoría al lado. Un partido de la ACF suele afectar a varios equipos de un mismo club.
- [ ] Sebastian puede pedir más cambios a Reglas: anotarlos aquí.

## 1c. Respuestas del organizador (recibidas el 2026-10-15)

Copiadas del mensaje de la organización. Hay audios que Sebastian todavía no escuchó: pueden cambiar algo. Falta el reglamento 2026 (Sebastian va a pasar la convocatoria actualizada en PDF).

| Tema | Respuesta | Qué hay que hacer en la app |
|---|---|---|
| **P79** (F11 no entra en la cancha 3) | No hay otra cancha. Hay 14 días de torneo entre viernes, sábado y domingo. Entre semana solo por suspensión. Sebastian les propuso empezar antes o terminar después, y otro día si no alcanza; no lo contestaron | Sacar los jueves como solución para F11 (quedan solo para suspensiones, como dice la convocatoria). Para que entre F11: ampliar el horario de la cancha 3 (antes de las 8 o después de las 16) con "Agregar tiempo" solo para C3. Confirmar con la organización cuánto se puede ampliar |
| **P86** (formatos 2026) | a) "Modifican el formato a más corto". b) Con 6 y 7, series cruzadas ("si no mal recuerdo"). c) Con 2 equipos la categoría no se abre; con 3, posiblemente un triangular | **Falta saber cuál es el formato más corto:** sin eso, `formatos.json` sigue con el de 2025. Pedir el reglamento 2026. Con 2 equipos: la app avisa que la categoría no se abre (hoy, ¿qué hace?). Con 3: confirmar "triangular" (¿una vuelta en lugar de ida y vuelta?) |
| **Mitades** (P13 y P63) | La cancha 3 se puede dividir en dos canchas de F7, pero no saben si interfiere "con la B" | Confirmar qué es "la B" (¿la mitad B de C3?). Si se confirma: F7 puede ir en C3A y C3B, cuando C3 no tiene F11 |
| **P81** (otra sanción por W.O.) | No hay respuesta clara; el texto dice "en el reglamento" | Esperar el reglamento 2026. Sigue: sin otra sanción |
| **P82** (cierre automático) | **"No se cierra sola"** | **Cambio:** hoy la app cierra sola a los 15 min (T11.12) y la regla no se puede apagar (mínimo 1). Hacer que la regla tenga "Nunca" y ponerlo por defecto en la plantilla 2026. Revisar Hoy, que debería avisar de un partido que sigue abierto pasado su final, en vez de cerrarlo |
| **P83** (penales) | Tiro por tiro | Ya está (T11.13) |
| **P84** (pasar del plantel máximo en la cancha) | Por reglamento se puede agregar jugadores **hasta antes del inicio del 2.º tiempo**, y piden que la app lo haga así | **Cambio:** en la ficha, el alta rápida se permite hasta que la mesa marca "Empieza el 2.º tiempo"; después se bloquea, con el motivo. Confirmar si eso vale también pasando el máximo del plantel (hoy: aviso y confirmar) |

### Audio del organizador (resumen de Sebastian, 2026-10-15)

| Tema | Lo que dijeron | Qué hay que hacer en la app |
|---|---|---|
| **P79** | 14 fechas entre viernes, sábado y domingo. Entre semana, solo los días que se suspenden | Igual que la convocatoria (ver arriba) |
| **P85** (roles) | La app la van a usar los profes de JMP. Dos permisos: **organizadores** (modifican todo) y otro para **subir listas, cargar resultados, etc.** (la mesa de control). Algo de "ver listas" (Sebastian supone que es para que los padres vean, y que los profes no anden tocando todo) | **Cambio:** volver a separar los roles. El código ya tiene el grupo Mesa de control (TU.2); hoy todos se crean como Organización (P64, T10.7). Definir qué puede la mesa: cargar y corregir listas, la ficha del partido (resultados, tarjetas, dorsales, alta rápida), ver todo; no: reglas, fixture, programar, mover, borrar ni publicar. **Confirmar con la organización** la lista exacta y si "ver listas" es un tercer rol de solo lectura o es la página pública para los padres |
| **P24** (dos equipos del mismo club) | **Evitar que se crucen hasta las instancias finales, para que no se eliminen entre ellos** | **Corregido el 2026-10-15:** no se pueden evitar a la vez el cruce en grupos y en semis. Con 6 y 7 (semis 1.º A vs 2.º A), en series distintas se enfrentan en grupos y como mucho en la final; en la misma serie no se enfrentan en grupos, pero sí pueden en la semi. Con 8 o más (semis 1.º A vs 2.º B) es al revés. Pregunta **P90** con ejemplos en PREGUNTAS, Parte 5. Por defecto: como mucho se cruzan en la final. Con un solo grupo (3 a 5) siguen en la fecha 1, para que no arreglen un resultado al final. No se implementa hasta la respuesta |
| **Copa Rotativa** (P30) | Ya no existe como premio, pero quieren que la app **cuente qué copas ganó cada club** | **Nuevo:** pantalla "Copas por club" (en Más y quizá en la página pública): por club, cuántas Copas de Oro y de Plata ganó (campeón y subcampeón), con las categorías. Sale solo de las finales jugadas |

- **P77, respondida (2026-10-15):** si la app está lista, la 1.ª fecha y el resto van en Rondo; si no, en Copa Fácil. La idea es dejarla lo más completa posible para usar Rondo desde el 24/10.

### Convocatoria 2026 (PDF en `docs/`, fuera de git por `*.pdf`), comparada con la plantilla el 2026-10-15

**Coincide con la plantilla `datos/config/jmp_cup_2026.json`:** fechas (24/10 al 15/11); categorías de Sub 5 a Sub 15 y Sub 17 (2010 y 2009), sin Sub 15 Femenino; niveles (Sub 5 y Sub 6 nivel único en F6, Sub 7 a Sub 9 Inicial y Avanzado en F7, Sub 10 a Sub 17 Inicial en F7 y Avanzado en F11); mínimos y máximos de cada categoría y nivel (Sub 10 y Sub 11 Avanzado de 12 a 16, **lo que confirma P78**); 22 en la lista de F11 y 18 convocados por partido; horarios (viernes de 16 a 20, sábado y domingo de 8 a 16); cierre de la planilla el miércoles 21/10 a las 12:00; CI o pasaporte; cuerpo técnico de 3 (entrenador, asistente y delegado) y solo el entrenador entra a la cancha (P57); Copa de Oro y de Plata; mejor jugador elegido por el árbitro y el asistente de mesa (P70).

**Para tener en cuenta:**
- **Suspensión → jueves.** La convocatoria dice que la fecha suspendida se reprograma entre semana, el jueves. Coincide con la respuesta a P79 ("entre semana solo por suspensión") y con la regla "Día para reprogramar" (jueves): esa regla se queda. Lo que se saca es usar jueves para que entre F11.
- **"Se respetará la programación del torneo ACF y no se atenderán requerimientos particulares."** Los bloqueos son para la ACF; los pedidos de un equipo no se atienden por reglamento. El botón "Reprogramar" no debería invitar a pedidos particulares: motivos ACF, suspensión (lluvia u otro) y "decisión de la organización".
- **Resultados por WhatsApp y Copa Fácil:** la convocatoria todavía nombra a Copa Fácil. Confirmar P77 (¿la 1.ª fecha va en Rondo?).
- **Inscripción:** Bs 1.200 (Sub 8 a Sub 17) y Bs 1.100 (Sub 5 a Sub 7), del 21/09 al 21/10. La app solo marca "pagado"; el monto no se usa. No hace falta más.
- **Medalla de participación de Sub 5 a Sub 12**, limitada al máximo de inscritos por categoría. Fuera del alcance de la app, salvo que pidan un conteo.
- **La convocatoria no trae formatos ni sanciones:** el "formato más corto" de P86 y la sanción por W.O. de P81 siguen sin respuesta. Hace falta el reglamento 2026.

- [x] Pasar estas respuestas a `docs/PREGUNTAS_JMP_CUP_2026.md` (Parte 5) y `docs/PROGRESO.md`, y decidir los cambios: fase 13 en `tasks/todo.md` (2026-10-15).
- [ ] Cuando llegue el reglamento 2026: P86 ("formato más corto") y P81.

## 2. Preguntas al organizador sin respuesta

Mientras no se respondan, la app usa el valor por defecto.

| P | Pregunta | Si no se responde |
|---|---|---|
| P79 | Con F11 en Sub 10 y Sub 11 Avanzado, la cancha 3 no alcanza. ¿Se agregan jueves de 16 a 20, se amplía el horario del sábado y el domingo, o se juega F11 en otra cancha? | Sin cambios: la app avisa lo que no entra. Con tres jueves (29/10, 5/11 y 12/11) entra todo (ver 1c: hay respuesta parcial o completa del 2026-10-15) |
| P81 | ¿Hay otra sanción por W.O., además del 3 a 0? | No (ver 1c: hay respuesta parcial o completa del 2026-10-15) |
| P83 | Penales: ¿tiro por tiro o solo el resultado? | Tiro por tiro, con el atajo de cargar solo el resultado (ver 1c: hay respuesta parcial o completa del 2026-10-15) |
| P84 | ¿Se puede pasar del plantel máximo al agregar a alguien en la cancha? | Sí, con aviso y confirmación (ver 1c: hay respuesta parcial o completa del 2026-10-15) |
| P85 | Roles: quiénes usan la app, quién está en cada mesa, qué pasaba con los dorsales en Copa Fácil, delegados que mandan la convocatoria, alguien de solo lectura y quién puede borrar o dar W.O. | Un solo rol, Organización, que hace todo |
| P86 | Formatos 2026: ¿siguen los del reglamento 2025? Con 6 y 7 equipos, ¿series cruzadas o todos contra todos? Con 2 equipos, ¿ida y vuelta? | Los de 2025, como están en `formatos.json` (ver 1c: hay respuesta parcial o completa del 2026-10-15) |

| P87 | Si un equipo se retira con el torneo empezado, ¿sus partidos jugados cuentan para los rivales? ¿Los que faltan se dan por W.O. (3 a 0) o se borran? | Nueva (2026-10-14). Por defecto: los jugados cuentan y los que faltan se dan por W.O., como un partido no presentado |

Además: P78 (plantel de F11 en Sub 10 y Sub 11 Avanzado) se tomó como 12 a 16, como dice la convocatoria. Conviene confirmarlo.

## 3. Proyecto: lo que queda abierto

- [ ] Tu prueba de la fase 12 en la demo, sobre todo B1, B2, B5 y C1 a C3 desde el celular.
- [ ] Revisión de cierre (`code-review-and-quality`) de las fases 11 y 12, y tu visto bueno.
- [ ] Prueba local de R2: la línea 13 del `.env` tiene una clave con un espacio, y el nombre correcto es `R2_ACCESS_KEY_ID`.
- [ ] `entrega_fixture.zip` está suelto en la raíz del repo: guardarlo fuera o borrarlo.
- [ ] La guía de despliegue usa `RONDO_ENV_FILE=` en los comandos, pero el código no lee esa variable. Sacarla.

## 4. Cosas a mejorar (opinión de Claude, para decidir)

Ordenadas por cuánto pueden doler durante el torneo.

1. **Programar corre dentro del pedido web.** Con un solo proceso de gunicorn y un corte a los 300 s, mientras programa la app anda lenta para todos, y si se pasa del corte se reinicia y no guarda nada. Lo sólido sería una tarea en segundo plano con un "Programando…" que se actualiza solo.
2. **Nadie se entera de un error 500.** No hay aviso de errores; solo quedan en los logs de Render. Un servicio como Sentry (tiene plan gratis) o un mail a la organización con cada error ayudaría a ver fallos antes de que alguien se queje. Agregarlo es una dependencia nueva: hay que aprobarla.
3. **Un solo proceso de gunicorn.** Si se cuelga, se cae todo hasta que Render lo reinicie. Con 1 CPU se podrían usar 2 procesos, midiendo antes la memoria.
4. **Respaldos.** En Neon gratis la historia para restaurar es corta. Además de Launch o de las ramas de respaldo, conviene un `pg_dump` a mano al cerrar cada fin de semana.
5. **Sin ruta de salud.** Render revisa `/cuentas/login/`. Una ruta `/salud/` que pruebe la base sería más clara.
6. **La distancia.** El servidor está en Virginia y los usuarios en Bolivia: cada clic suma unos 150 ms de ida y vuelta. Se nota en el celular con datos móviles. Cloud Run en São Paulo lo bajaría, para 2027.
7. **El cierre automático de partidos olvidados es perezoso:** corre solo cuando alguien abre Hoy, la ficha o la página pública. En la práctica siempre hay alguien mirando, pero un partido puede quedar "en juego" hasta que alguien entre.
8. **Para mirar en tu prueba (intuitivo o no):** si se entiende sin explicación el camino completo, desde el asistente hasta inscribir (pegar la lista desde Excel), armar el fixture, "¿Entra todo?", programar, mover o intercambiar, publicar, la ficha del partido desde el celular y la página pública. Anota dónde dudaste o tuviste que volver atrás: eso vale tanto como un fallo.
