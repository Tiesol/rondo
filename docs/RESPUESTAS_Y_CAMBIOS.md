# Respuestas del organizador y cambios para Rondo

**De:** Sebastian. **Fecha:** 2026-10-13.

Son las respuestas a `PREGUNTAS_JMP_CUP_2026.md` y los cambios que traen. **Este archivo manda sobre los valores por defecto de ese documento y sobre `PEDIDO_CLAUDE_CODE.md` donde se contradigan.** Las preguntas que el organizador no respondió quedan con su valor por defecto. Las nuevas siguen desde P78; su texto para el organizador está en `PARA_MI_HERMANO.txt`.

## 0. Principio: flexibilidad

El organizador lo repitió en casi todas las respuestas: en la cancha pasan cosas que ninguna regla prevé. Rondo **propone y avisa; el administrador decide.**

- **Se bloquea solo lo físicamente imposible:**
  - dos partidos a la vez en la misma cancha o mitad;
  - un equipo jugando dos partidos a la vez;
  - un dorsal repetido dentro del mismo equipo en el mismo partido.
- **Todo lo demás es un aviso que se confirma:** compatibilidad de cancha, choques de jugadores o profes, descanso del día, horario, orden de fechas, plantel máximo e inscripción fuera de plazo. Ejemplo: "Juan P. también juega en Sub 9 a esa hora. ¿Mover igual?".
- **Editable siempre, con historial:** inscripciones, dorsales, horarios, canchas, resultados y tiempos de un partido terminado. Cada cambio guarda quién lo hizo, cuándo y qué valía antes.
- **Valores de la reglamentación en la configuración del torneo:** minutos, cantidad de penales, toggles de premios. Se pueden cambiar sin código.

## 1. Respuestas y qué cambia

### Fechas, horarios y canchas

| # | Respuesta | Qué cambia |
|---|---|---|
| P48 y 1.1 | **La hora de cierre es la del inicio del último partido.** El viernes, el último puede empezar a las 20:00; sábado y domingo, a las 16:00 | Programador y verificador: `inicio ≤ cierre de la franja`, en lugar de `fin ≤ cierre` |
| 1.1 | Las fechas suspendidas se reprograman el día que elija el administrador, cualquier día de la semana | "Agregar un día" acepta cualquier fecha y horario, no solo entre semana |
| P13 y P63 | Se pueden partir las 3 canchas. De preferencia se parte la cancha 1 para Sub 5 y Sub 6, pero a veces se parten las otras para adelantar partidos. Para torneos futuros, poder agregar canchas | Cada cancha tiene la opción "se puede partir", con sus mitades (C2A, C2B, C3A y C3B). Se pueden agregar canchas desde la app. El programador automático usa la configuración base: solo C1 se parte, para F6. Las otras mitades se usan al mover o reprogramar a mano (P79) |
| P16 y 1.2 | Los minutos por tiempo se editan por categoría. **El partido no empieza solo:** el administrador marca el inicio, el descanso, el segundo tiempo y el final | Ver la sección 3 |
| P56 | **Sub 5 y Sub 6 no juegan los viernes.** De preferencia, los más chicos juegan en los primeros horarios del fin de semana | Configuración por categoría: días permitidos (duro) y "preferir temprano" (blando). Sub 5 y Sub 6: sábado y domingo, temprano |
| P46 | El fin de semana de Todos Santos se juega normal, con la opción de reprogramar esos partidos | Ya está: suspender un día y reprogramar |

### Categorías e inscripción

| # | Respuesta | Qué cambia |
|---|---|---|
| P60 | **Sub 10 y Sub 11 Avanzado juegan Fútbol 11.** Inicial juega F7 | Configuración. **No entra:** con los equipos de 2023, la cancha 3 necesita el 107 % de su tiempo, aun con el inicio al cierre. Las canchas 1 y 2 quedan al 54 %. Ver P78 |
| P61 y P41 | No hay Sub 15 Femenino | Sacarla de la plantilla 2026 |
| P62 | No hay Copa de Bronce | El interruptor queda apagado: con 10 equipos son 26 partidos |
| P2, P22 y 1.3 | **Cualquier administrador cambia las listas, en cualquier momento.** Los equipos y jugadores pueden inscribirse tarde, incluso con el torneo empezado, sobre todo en la 1.ª y la 2.ª semana | El cierre del 21/10 es solo informativo: muestra el aviso "fuera de plazo" y no bloquea. Nueva regla `altas_tardias_hasta`, por defecto el fin del 2.º fin de semana: después de esa fecha, agregar pide confirmación |
| P44 y P80 | Se puede agregar un equipo durante las primeras fechas, aunque ya haya partidos jugados. Ejemplo: con 7 equipos entra un 8.º y conviene pasar a dos series de 4 | Rehacer el fixture con partidos jugados. Ver la sección 2.5 |
| P9 y 1.3 | **El dorsal es de cada partido, no del jugador.** Un jugador puede usar el 10 en la fecha 1 y el 7 en la 2. Muchos equipos no tienen camisetas numeradas fijas | El dorsal se carga en la planilla de cada partido (sección 3). El del plantel queda como dorsal habitual, opcional, y sirve de sugerencia |
| P39 | Se puede inscribir a un jugador justo antes de su partido. Ahí se presentan todos con su CI y se les saca la foto | Alta rápida desde la planilla del partido, con foto desde la cámara del celular (sección 3) |
| P84 | Hay que poder agregar jugadores en la cancha | Al pasar el máximo, la app avisa y deja agregar si el encargado confirma. Por defecto, mientras el organizador no responda P84 |
| 1.3 | Jugador en dos equipos: el programador evita el choque. Al mover a mano, solo avisa | Ya está como regla dura del programador; al mover a mano, es un aviso |
| P10 | Los clubes los cargan ellos | Pantalla de clubes: crear, editar, alias, escudo y unir dos clubes duplicados. Hoy los clubes solo se editan desde el admin |
| P37 | No se da por las edades | Se deja como está |

### Programación

| # | Respuesta | Qué cambia |
|---|---|---|
| P57 | El choque de profes cuenta **solo para el entrenador** | Los pares de personas salen solo de Profe con rol entrenador, más jugadores compartidos |
| P35 y 1.4 | **Sin margen para cambiar de cancha:** todas las canchas están en el mismo complejo | `profe_minutos_cambio_de_cancha = 0`. El entrenador solo no puede tener partidos que se pisen; puede tener dos seguidos en cualquier cancha |
| P19 y 1.4 | El orden de fechas es una preferencia. Si se reprograma la fecha 2 para después de la 3, la 3 pasa a ser el 2.º partido del equipo | `orden_de_fechas = "blanda"`. Se penaliza en el objetivo, no se exige. La reprogramación puede dejar una fecha después de otra |
| P33 y 1.4 | La eliminación de una categoría puede empezar apenas termina su fase de grupos. A veces semis o finales van antes del último fin de semana | Se saca la restricción dura "desde el 4.º fin de semana". Queda: la eliminación después de los grupos de su categoría, y P17 entre llaves encadenadas (revisión externa, punto 1) |
| P55 | **De preferencia, las finales van en los últimos 2 días** (sábado 14 y domingo 15/11), porque los premios llegan esa semana. Pueden ir antes | Blando: las finales, preferentemente en los 2 últimos días del torneo |
| P17 y P47 | Un turno libre en medio y como máximo 2 partidos por día. **De preferencia, evitar 2 partidos el mismo día** | Lo duro queda igual. Se suma, como blando, penalizar los equipos con 2 partidos en el día |
| P20 y 1.4 | De preferencia, los equipos de un mismo club juegan el mismo día | Blando: minimizar los días distintos en que juega cada club por fin de semana. Reemplaza "seguidos en la misma cancha" |
| 1.4 | No existen partidos fijados a mano. Los jugados no se mueven nunca | Mover un partido a mano no lo fija. Los partidos en juego, terminados o con W.O. no se mueven. Las propuestas automáticas solo se aplican si las aprueba un administrador |
| 1.4 | Al reprogramar, **de preferencia no mover ningún otro partido**; si no se puede, mover los menos posibles | Las propuestas buscan primero mover solo el partido afectado y después el mínimo de movimientos |
| 1.4 (ACF) | Al reprogramar puede convenir dar **W.O.**, porque al equipo no le sirve ninguna fecha propuesta. A veces un equipo reprograma varias veces | En la pantalla de reprogramación: botón "Dar W.O." y el aviso "Este equipo ya reprogramó N veces", sin límite. La cuenta sale del historial de cambios |

**Orden de los objetivos blandos**, de mayor a menor peso:
1. ubicar partidos;
2. evitar 2 partidos por día;
3. finales en los últimos 2 días;
4. Sub 5 y Sub 6 temprano;
5. orden de fechas;
6. clubes el mismo día;
7. repartir entre fines de semana;
8. espera del entrenador.

Medir que siga resolviendo bien con 1 CPU.

### Resultados, premios y fotos

| # | Respuesta | Qué cambia |
|---|---|---|
| P64 | Por ahora, **un solo rol: cualquier administrador hace todo**. Los roles se separan más adelante | Sección 4 |
| P73 | En vivo. La página pública se actualiza sola | HTMX con `every 30s` y caché corta |
| P70 y P71 | Mejor jugador del partido y tabla de goleadores: **se eligen al crear el torneo** | Dos interruptores del torneo, en el asistente y en Reglas |
| P72 | El gol en contra se anota a nombre del jugador que lo hizo | Evento "gol en contra" con jugador. Suma al rival y no cuenta para goleadores |
| P23 | W.O.: 3 a 0 | Ya está |
| P74 | Un administrador anota si se pagó la multa de Bs 30. Si no se pagó, el jugador figura **suspendido en el próximo partido** | Sección 3.6 |
| 1.6 | **Desempate:** en la fase de grupos, el orden del reglamento. En semis y finales, penales. Rara vez se juega un partido extra | Penales en la planilla (sección 3.5). El partido extra es un partido de desempate que un administrador crea a mano |
| 1.6 | **Penales:** 3 por equipo, ampliables. Si siguen empatados, uno más por equipo hasta que se defina | `penales_por_equipo = 3`, configurable, con muerte súbita después |
| 1.6 | Se registran las amonestaciones verbales (Sub 5 a Sub 7). En Sub 5 a Sub 9, con 2 amarillas el jugador sale 5 minutos | Evento "amonestación", interno: no es público y no cuenta para fair play. Con 2 amarillas en esas categorías, la planilla muestra "afuera 5 min" con la hora de vuelta. Es informativo, no suspende |
| 1.6 | Premios: alcanza con Oro y Plata | Sin medallas en la app |
| P76 y P49 | Las fotos y los datos se guardan **hasta que un administrador decida borrarlos** | Sin borrado automático. `anonimizar_torneo` sigue siendo manual |
| P68 | El escudo lo carga la organización | Ya estaba |
| P69 | Los patrocinadores cambian según el torneo. El diseño del PNG va a cambiar por uno más elaborado | La lista de patrocinadores va por torneo. **El PNG tiene que poder cambiar de diseño sin tocar la lógica:** plantilla aparte |
| P45 | Las series se arman por sorteo, separando a los equipos del mismo club | Ya está |
| P27 y P54 | **Más de 10 equipos:** grupos A y B. Oro: 1.º y 2.º de cada grupo. Plata: 3.º y 4.º de cada grupo | Formato para N > 10 en `formatos.json`: dos grupos lo más parejos posible, todos contra todos dentro de cada grupo. Oro y Plata, como el formato de 8 equipos, con semis cruzadas y final |

Sin respuesta, y quedan como están: P5, P6, P7, P8, P26, P28, P29, P34, P36, P42, P43, P50, P65, P66, P67 y P77. **P24 y P30** quedan para más adelante.

## 2. Cambios de lógica

### 2.1 Programador

- **Franjas:** el inicio tiene que ser menor o igual al cierre.
- **Pares de personas:** solo entrenadores y jugadores compartidos, con margen 0.
- **Días permitidos por categoría:** regla dura. Sub 5 y Sub 6, sin viernes.
- **Eliminación:** sin el límite del fin de semana. Después de los grupos de su categoría, con P17 entre llaves encadenadas.
- **Objetivos blandos:** en el orden de la sección 1.
- **Canchas:** la configuración base para el automático. Las demás mitades quedan disponibles para lo manual.

### 2.2 Verificador

- **Dos niveles:** **bloqueo** (cancha física doble y equipo doble) y **aviso** (todo lo demás).
- **Se aplica igual en los tres lugares:** cambios manuales, reprogramaciones y asignación de llaves.
- **Mismas reglas que el programador:** franja por inicio, entrenador con margen 0, sin margen de cancha y orden de fechas como aviso.

### 2.3 Reprogramación

- **Cualquier día y horario** que elija el administrador.
- **Propuestas:** primero las que mueven solo el partido afectado.
- **Botón "Dar W.O.".**
- **Contador:** cuántas veces reprogramó cada equipo.
- **Cancha partida:** se puede elegir una mitad de cualquier cancha que "se pueda partir". Cuenta como reprogramación y queda en el historial.

### 2.4 Inscripción

- **Cierre informativo:** el cierre de inscripción no bloquea; las altas después de `altas_tardias_hasta` piden confirmación.
- **Dorsal:** opcional en el plantel y obligatorio en la planilla de cada partido.
- **Plantel máximo:** aviso con confirmación (P84).
- **Cualquier administrador** edita listas, equipos y clubes.

### 2.5 Rehacer el fixture con partidos jugados (P44 y P80)

- **Cuándo:** se puede agregar o sacar un equipo de una categoría empezada.
- **Qué hace la app:** arma el fixture nuevo y muestra, antes de confirmar:
  - qué partidos jugados se conservan, porque el cruce sigue existiendo en el formato nuevo;
  - cuáles se descartan;
  - qué partidos nuevos hay que programar.
- **Al confirmar:** los partidos nuevos se programan con propuestas, sin tocar los jugados.
- **Por defecto** se conservan los cruces que siguen existiendo, hasta que el organizador responda P80.

## 3. Día de partido (reemplaza B3 y B5 del pedido)

La pantalla más importante del torneo. La usa un administrador **en la cancha, con el celular, apurado.**

- **Botones:** grandes.
- **Pocos toques.**
- **Sin escribir números para identificar jugadores:** se tocan tarjetas con foto, nombre y dorsal.

### 3.1 Partidos de hoy

- **Lista por cancha y hora**, con el estado: por jugar, en juego (1T o 2T), descanso, penales, terminado o W.O.
- **Atraso:** si un partido empezó tarde, se ve el atraso estimado de los siguientes de esa cancha. Es solo informativo y sirve también para la página pública.

### 3.2 Previa: planilla del partido, antes de empezar

Para cada equipo:

- **Quiénes juegan:** se tocan los jugadores del plantel; se pueden marcar titulares y suplentes.
- **Dorsal de este partido:** se propone el dorsal habitual o el del partido anterior.
- **Dorsal repetido: imposible.** La base no lo permite y la pantalla avisa al instante: "El 7 ya lo tiene Juan P.".
- **Jugador suspendido:** aparece marcado, y no se lo puede convocar sin confirmar.
- **Agregar jugador ahí mismo:**
  - nombres, apellidos, CI y fecha o año de nacimiento;
  - **foto con la cámara** (`<input type="file" accept="image/*" capture="environment">`);
  - corren las mismas validaciones de inscripción, con avisos.
- **Cambiar o sacar la foto** de un jugador desde ahí.
- **Entrenador presente:** opcional.
- **Botón W.O.:** se elige qué equipo no se presentó y se carga el resultado de P23.

### 3.3 Control del partido

- **Botones en orden:** Iniciar → Fin del 1.er tiempo → Iniciar 2.º tiempo → Terminar. Cada uno guarda la hora real.
- **Reloj:** muestra el minuto de juego del tiempo actual; el partido no empieza solo.
- **Eventos:** Gol, Gol en contra, Amarilla, Roja, Amonestación y Lesión.
  1. Se elige el equipo.
  2. Aparece la grilla de sus jugadores **de este partido**, con foto, dorsal y nombre. Se puede ver el plantel entero si hace falta.
  3. El minuto se completa solo desde el reloj y se puede corregir.
- **"Deshacer"** el último evento.
- **Lesión:** queda interna. **Nunca se publica**: es un dato de salud de un menor.
- **Cambios de jugador:** no hace falta registrarlos por ahora.

### 3.4 Cierre automático y edición

- **Partido olvidado:** si sigue en juego pasado su final previsto más `cierre_automatico_min` (por defecto, 15; P82), se cierra solo.
  - El final previsto es el inicio real + 2 tiempos + descanso.
  - Se guarda con el marcador que tenía y la marca "cerrado automáticamente", para revisar.
- **Sin cron:** el chequeo corre perezoso, al cargar páginas del torneo o en el pedido periódico de la página pública. Además hay un comando para un cron, si lo hay.
- **Partido sin iniciar:** si pasó su hora + 30 minutos, figura "sin iniciar" en Partidos de hoy. No se cierra solo.
- **Partido terminado:** sigue editable: eventos, dorsales, marcador, horas reales y W.O. Todo con historial, quién y cuándo.

### 3.5 Penales y partido extra

- **Si una llave de eliminación termina empatada,** aparece "Penales".
- **Tiro por tiro:** se toca "Convirtió" o "Falló" por equipo. La app lleva la cuenta: con 3 por equipo y luego uno más hasta definir, dice quién ganó.
- **Atajo:** cargar solo el resultado final de penales (P83).
- **Partido extra:** un administrador lo crea a mano como desempate entre los dos equipos.

### 3.6 Suspensiones

- **Sub 10 a Sub 17:** la segunda amarilla genera la roja automáticamente y una suspensión pendiente, con la casilla "Pagó Bs 30". Si no pagó, figura suspendido en el próximo partido de su equipo; al pasar ese partido, se cumple.
- **Roja directa:** sin suspensión automática (P29). Un administrador puede marcar una suspensión a mano.
- **Pantalla de suspendidos:** la lista para la mesa (era T9.2). Sube de prioridad.

### 3.7 Página pública

- **Ficha en vivo:** resultado, minuto o estado ("2T 12'"), goles con "Juan P." y minuto, y mejor jugador si el interruptor está encendido.
- **Tarjetas:** se ven amarillas y rojas; amonestaciones y lesiones, nunca.
- **Tabla y goleadores:** si el interruptor está encendido.

## 4. Roles

**Ahora:** un solo rol, **Administrador**, que hace todo: inscribir, programar, reprogramar, planillas y W.O. Todos los usuarios de JMP lo tienen. Sebastian queda además como superusuario técnico. Los grupos que ya existen (Organización y Mesa) se mantienen internamente para separar más adelante, pero hoy todos los usuarios nuevos van a Organización.

**El historial es obligatorio desde ya**, porque con un solo rol es la única forma de saber quién se equivocó:
- cada evento, dorsal, cambio de horario, W.O. y corrección guarda usuario, fecha y valor anterior;
- se ve en la ficha del partido y en "Más".

**Propuesta para después**, cuando el organizador responda P85:

| Rol | Puede |
|---|---|
| Organizador | Todo, incluidas reglas, usuarios y borrar |
| Programación | Fixtures, calendario, reprogramaciones y W.O. |
| Mesa o planillero | Las planillas de sus partidos: convocados, dorsales, eventos, inicio y fin, y alta rápida de jugadores. No toca el calendario ni las reglas |
| Inscripción | Equipos, listas, profes, fotos y clubes |
| Solo lectura | Ver todo |
| Delegado de club (futuro, externo) | Mandar desde su celular quiénes juegan y con qué dorsal antes del partido. La mesa solo confirma. Ataca de raíz los errores de dorsal que tenían en Copa Fácil |

## 5. Prioridades nuevas

Cambian por las respuestas. La foto se saca en la cancha, así que el almacenamiento de fotos pasa a ser necesario para la 1.ª fecha.

**Antes del 21/10 (cierre de listas):**
1. T7.10, producción.
2. T7.4 y T7.5, configuración 2026 con lo de arriba:
   - Sub 10 y Sub 11 Avanzado en F11;
   - sin Sub 15 Femenino;
   - sin Bronce;
   - franja por inicio;
   - días permitidos;
   - canchas partibles y agregar canchas.
3. T7.6 a T7.9: pegar listas, solo el año, dorsal opcional en el plantel y altas tardías.
4. T7.1 a T7.3, rehechas con la sección 2.1.
5. T7.11: borrador y fixture desactualizado.
6. La pantalla "¿Entra todo?" tiene que mostrar claro el faltante de F11 (P78).

**Antes del 24/10 (1.ª fecha):**
1. T8.1 a T8.4: R2 y fotos, para sacarlas en la cancha.
2. Sección 3, día de partido: 3.1 a 3.4 son el mínimo.
3. Tabla de posiciones.
4. Página pública en vivo.

Si no llega, la 1.ª fecha va en Copa Fácil (P77).

**Durante el torneo:**
- 3.5 penales, para las semis;
- 3.6 suspensiones y su pantalla;
- 2.5 rehacer con partidos jugados;
- pantalla de clubes;
- cruces automáticos de la eliminación;
- PNG con el diseño 2026 (`docs/diseno-fixture-2026/`);
- reprogramación con W.O. y contador.

Si no entra todo esto en el tiempo, avísame qué se corre antes de empezar, no al final.

## 6. Preguntas nuevas (en `PARA_MI_HERMANO.txt`)

| # | Pregunta | Por defecto |
|---|---|---|
| P78 | Sub 10 y Sub 11 Avanzado en F11 no entran solo en la cancha 3. ¿Otra cancha para F11, jueves u otros días, o partidos más cortos? ¿Cuántos minutos por tiempo juegan en F11? | 20 minutos por tiempo. Lo que no entra queda sin ubicar, con su motivo, y se puede mover a mano con aviso |
| P79 | Al partir la cancha 2 o la 3, ¿qué categorías juegan en cada mitad? | F6 en cualquier mitad; F7 en mitad de C3. Solo para lo manual |
| P80 | Equipo nuevo con partidos ya jugados: ¿cuentan esos resultados? | Cuentan los cruces que siguen existiendo |
| P81 | ¿Hay otra sanción por W.O., además del 3 a 0? | No |
| P82 | ¿A cuántos minutos del final previsto se cierra solo un partido olvidado? | 15 |
| P83 | Penales: ¿tiro por tiro o solo el resultado? | Tiro por tiro, con el atajo del resultado |
| P84 | ¿Se puede pasar del plantel máximo al agregar a alguien en la cancha? | Sí, con aviso y confirmación |
| P85 | Roles: quiénes usan la app, quién está en cada mesa, qué pasaba con los dorsales en Copa Fácil, delegados que mandan la convocatoria, alguien de solo lectura, y quién puede borrar o dar W.O. | Un solo rol, Administrador |
| P86 | Formatos 2026: ¿siguen los del reglamento 2025? Con 6 y 7 equipos, ¿series cruzadas o todos contra todos? Con 2 equipos, ¿ida y vuelta? | Los de 2025, como están en `formatos.json` |

## 7. Respuestas del 2026-10-13 (de Sebastian, después de leer las preguntas)

| # | Respuesta | Qué cambia |
|---|---|---|
| P78 | **Flexibilidad.** Si los partidos no entran, la organización los pone a mano en días u horarios fuera de los establecidos: un partido más después del último (por ejemplo, el sábado después de las 16:00) o uno antes de la hora de inicio. Todas las canchas se pueden partir. Los minutos de F11 siguen sin respuesta (20) | T11.2 y T11.3: mover a mano a cualquier día, hora, cancha o mitad, con aviso y confirmación |
| P80 | **Los resultados jugados cuentan** | T11.15: al rehacer, las series nuevas se arman para que los partidos jugados sigan existiendo |
| P82 | El cierre automático cuenta **desde el inicio real del 2.º tiempo**: inicio del 2.º tiempo + minutos del tiempo + 15 | T11.12 |

Siguen sin respuesta: P79, P81, P83, P84, P85 y P86, con su valor por defecto.
