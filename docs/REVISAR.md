# Para que Sebastian revise

El 2026-10-07, Sebastian autorizó seguir con el desarrollo completo, fase tras fase, sin esperar su visto bueno entre fases (solo esta vez). Cada duda se resolvió con un supuesto, que queda anotado acá para revisarlo a la vuelta.

Los límites de SPEC.md siguen valiendo: sin dependencias nuevas fuera de las ya aprobadas, sin producción, sin nada que tenga costo y sin datos reales.

**Cómo leerlo:** cada fila tiene un número (R1, R2…), la tarea donde surgió, qué hay que revisar y el supuesto que se tomó mientras tanto. Si el supuesto está bien, alcanza con borrar la fila. Si no, se cambia y se anota en PROGRESO.md.

## Pendientes de revisión

| # | Tarea | Qué revisar | Supuesto tomado |
|---|---|---|---|
| R1 | TU.1 | Navegar con el teclado y mirar la interfaz en tu celular. Yo lo revisé con capturas de Firefox a 360 y 1024 px, en claro y en oscuro, no en un teléfono real | Los controles son nativos (enlaces, botones, campos y `<dialog>`), así que el teclado funciona sin código extra. El muestrario está en `/diagnostico/componentes/` (solo staff) |
| R2 | TU.1 | El modo oscuro sigue al del sistema. No hay un botón para cambiarlo a mano | Alcanza con seguir al sistema |
| R3 | TU.1 | "Salir" quedó en la barra superior. El prototipo no lo mostraba | Es el lugar más fácil de encontrar en el celular |
| R4 | TU.1, TU.7 | Los colores del organizador pintan toda la interfaz (Más → Datos de la escuela). El verde viejo se cambió por el azul marino con una migración | Principal = azul marino, acento = dorado, por defecto. El principal tiene que dejar leer texto blanco encima |
| R5 | TU.2 | Los usuarios de la organización ya no son staff: no entran al admin de Django. Solo entra quien se crea con `--admin` (tú) | Con las pantallas propias, el admin queda como herramienta técnica |
| R6 | TU.2, T6.2 | Desde T6.2, la organización agrega personas y cambia roles en Más. La contraseña temporal se ve una sola vez y se entrega en persona (no hay correo configurado para mandarla) | Sin correo, es lo más simple y seguro; `crear_usuario` sigue sirviendo desde la terminal |
| R7 | TU.2 | Los usuarios que ya existían en la demo sin grupo pasaron a Organización con la migración 0005 | Hasta ahora, `crear_usuario` creaba solo usuarios de la organización |
| R8 | TU.3 | Los títulos y las ayudas de las 17 reglas (pantalla de reglas). Los escribí a partir del catálogo de SPEC.md y de las preguntas P | Textos cortos en español, con "tú". Si uno no se entiende, se cambia en `src/dominio/config.py` y la pantalla lo toma sola |
| R9 | TU.3 | La pantalla de reglas está en `/torneos/<id>/reglas/`. Todavía no hay un enlace desde Inicio: llega en TU.5 | — |
| R10 | TU.4 | El asistente no tiene la opción "desde cero" del prototipo: siempre parte de la plantilla del reglamento 2026 | Para la demo alcanza la plantilla. Desde cero hace falta cargar categorías a mano, y eso es más trabajo que destildar |
| R11 | TU.4 | En el asistente, las canchas no se editan (se muestran como vienen) | Cambiar la división de C1 o C2 rompe la compatibilidad de Sub 5 y Sub 6. Queda para cuando se responda P13 |
| R12 | TU.4 | El asistente no deja crear un torneo con el mismo nombre y año que otro | Así no se pisa uno existente por error |
| R13 | TU.4 | En el celular angosto (menos de 420 px), la barra superior esconde el rol y deja solo el ícono de "Salir" | El título de la pantalla entra entero; el rol se ve en "Más" |
| R14 | TU.5 | El "torneo activo" es el más reciente (por año y fecha de inicio). No hay forma de elegir otro | Hay un torneo por año |
| R15 | TU.5 | Pendientes de Inicio: "N categorías sin equipos" y "16 reglas esperan la respuesta del organizador" (todas las que tienen una P) | No hay registro de qué preguntas ya se respondieron. Cuando lleguen las respuestas, se puede marcar cada regla como confirmada |
| R16 | TU.5 | Los ajustes de una categoría se editan en Torneo → Ajustes: plantel mínimo y máximo, minutos por tiempo, convocados y canchas. La modalidad y la edad no se editan ahí | Cambiar la modalidad o la edad es cambiar de categoría; eso va en el asistente o en el JSON |
| R17 | TU.6 | La página pública está en `/t/<número>/`, no en una dirección con nombre (como `/jmp-cup-2026`) | Alcanza para la demo. Una dirección con nombre se agrega antes de la fase 6 si hace falta |
| R18 | TU.6 | Un torneo nuevo nace sin página pública; la organización la enciende en "Más" | Así nada se publica por accidente |
| R19 | T2.1 | El complemento del CI se reconoce solo con guion (`1234567-1E`). Sin guion (`12345671E`) da error | Sin guion no se distingue el complemento de los dígitos del número |
| R20 | T2.1 | Una "E" seguida solo de dígitos (`E1234567`) se toma como CI de extranjero, no como pasaporte | Es la forma más común en Bolivia. Un pasaporte empieza con letras y sigue con dígitos (`AB123456`) |
| R21 | T2.2 | Los dorsales válidos van del 1 al 99 | Es lo habitual en camisetas de fútbol; no está en el reglamento |
| R22 | T2.2 | "Misma categoría" para INS-05 compara la categoría sin nivel: Sub 9 Inicial y Sub 9 Avanzado son la misma categoría, así que un jugador no puede estar en los dos | El reglamento habla de "otra categoría" |
| R23 | T2.2 | Sin fecha de nacimiento no se puede cargar a un jugador (es la única forma de validar la edad) | A diferencia del CI, que puede quedar pendiente (P39) |
| R24 | T2.2 | Se agregó la validación del cierre de inscripción (INS-11): después de esa fecha, solo la organización cambia listas | El checkpoint de la fase 2 pide un test por regla INS, e INS-11 no estaba en ninguna tarea |
| R25 | T2.3 | En el catálogo de clubes, los nombres dudosos de 6.2 quedaron como alias: Petrolero y Oriente Petrolero 2 → Oriente Petrolero; Juniors → Atlético Juniors; Leones PFC → Leones. JMP Soccer y JMP Academy son alias del club JMP | Es lo que sugiere el contexto. Si alguno es otro club, se separa en el admin de Club |
| R26 | T2.3 | El catálogo de clubes se carga en la demo con `manage.py cargar_clubes` (como `cargar_config`, lo corres tú contra la rama `demo`) | — |
| R27 | T2.4 | Si se carga un documento que ya existe con otro nombre o fecha de nacimiento, valen los datos guardados y se muestra un aviso con el nombre guardado | Lo más probable es un error de tipeo en la segunda carga. Corregir los datos de una persona queda para la ficha del jugador |
| R28 | T2.4 | A dos personas sin documento no se las puede reconocer como la misma: un jugador sin CI podría quedar en dos equipos sin aviso | El CI es obligatorio antes del primer partido (P39), y ahí se detecta |
| R29 | T2.5 | El escudo de cada equipo es provisorio: la sigla (las 3 primeras letras) en el color de la camiseta. Los escudos reales llegan con las imágenes | Decisión del 2026-10-07: imágenes para después |
| R30 | T2.5 | Todavía no se puede editar ni borrar un equipo desde las pantallas (solo crearlo); hoy se hace en el admin | Se suma cuando haga falta; cargar bien es lo primero |
| R31 | T2.5 | La mesa de control también crea equipos (no solo listas) | Los roles acordados dicen "cargar equipos y listas" |
| R32 | T2.6 | Después de guardar a un jugador, los avisos de edad, documento y otros equipos quedan en pantalla hasta cerrarlos. Los de "faltan N", "sin dorsal" y "documento pendiente" no se repiten, porque ya se ven en la ficha | Menos ruido al cargar una lista entera |
| R33 | T2.6 | Verificar a un jugador es tocar su estado ("Verificar" → "Verificado"); tocarlo de nuevo lo desmarca. No queda registro de quién verificó | Para la demo alcanza. Quién y cuándo se puede sumar antes de la fase 6 |
| R34 | T2.6 | Todavía no se pueden editar ni sacar jugadores o profes desde las pantallas | Llega después; hoy se hace en el admin |
| R35 | T2.7 | En la demo, Crack FC tiene 3 profes compartidos entre Sub 7, Sub 8 Avanzado y Sub 12, pero no el cuarto de 6.4 ({Sub 7, Sub 8 Av} × 1): con él, Sub 7 tendría 4 profes y el máximo es 3 | En 2023 pasaba, pero el reglamento dice 3 (P11, P40) |
| R36 | T2.7 | Los equipos de 2023 se pasaron a las categorías de 2026 así: Sub 7 → Sub 7 Avanzado; Sub 12, 13 y 15 (que jugaban en F11) → Avanzado. Las categorías nuevas (Sub 14 y Sub 17 Avanzado, Sub 15 Femenino) tienen 3 equipos inventados cada una. Quedan vacías 6 categorías Inicial | Total de 93 equipos, cerca del tamaño de 2023 que pide la tarea |
| R37 | T2.7 | `generar_demo` deja el torneo de demo con la página pública encendida | Para mostrarla en la demo |
| R38 | T3.3 | Editar las series a mano es cambiar equipos de serie, pero los tamaños tienen que seguir siendo los del formato (por ejemplo, 4 y 4 con 8 equipos) | El formato de 4.5 depende de esos tamaños |
| R39 | T3.7 | La capacidad es una cota optimista: si una categoría puede jugar en mitades de una cancha y entera en otra, se cuenta como media cancha en todas, y no mira choques de equipos ni de profes. Si dice "no entra", seguro no entra; si dice "entra", el programador puede igual dejar partidos afuera | Es la forma rápida de verlo antes de programar (ARQUITECTURA 8) |
| R40 | T4.1 | Alguien que juega en un equipo y dirige otro cuenta como "profe" para programar: necesita el margen para cambiar de cancha (P35) | Es lo más prudente: tiene que llegar a tiempo a la otra cancha |
| R41 | T4.3 | El programador pide el margen del profe (10 min, P35) también cuando sus dos partidos son en la misma cancha. El verificador sí acepta seguidos en la misma cancha | Más simple y más seguro; puede dejar algo menos de lugar |
| R42 | T4.3 | Si el orden de las fechas se configura como "blando" (P19), el programador simplemente no lo exige (todavía no lo usa como preferencia) | La regla viene "dura" por defecto |
| R43 | T4.3 | Para repartir la carga, cada fecha de grupos busca "su" fin de semana: la fecha k de F cae, si se puede, en el fin de semana k × S / F, entre los S fines de semana antes de la eliminación | Es una preferencia: ubicar todos los partidos manda |
| R44 | T4.6 | En local, la demo (223 partidos) se programa entera en 30 s. En Render gratis (0,1 CPU) va a tardar mucho más, o puede no llegar a ubicar todo dentro del límite de 60 s (H6). Si pasa, se sube `RONDO_PROGRAMADOR_SEGUNDOS` (gunicorn corta a los 300) o se programa desde tu máquina contra Neon | Para la demo con el organizador, conviene programar antes y mostrar el resultado |
| R45 | T5.6 | Probar "Compartir el día" desde tu Android (Calendario → un día → Compartir el día) y desde la PC. Es la prueba pendiente de T0.7, ahora con el diseño de 2025 | La Web Share API comparte varias imágenes juntas en Android; si no, se descargan |
| R46 | T5.6 | El PNG muestra hasta 5 partidos por imagen. Una cancha con más partidos ese día sale en varias imágenes ("Cancha 1 · 1/2") | Con filas del tamaño de 2025 no entran más |
| R47 | T5.6 | La copa, los escudos y los patrocinadores del PNG son marcadores hasta que haya imágenes reales | Decisión del 2026-10-07: imágenes para después |
| R48 | T6.1 | Los cruces de la eliminación se asignan a mano (P50, por defecto): la app no calcula la tabla de posiciones, porque puntos y desempate no están especificados (P28, P34) | No se inventan reglas |
| R49 | T6.3 | Límite de intentos de login: 10 fallidos por IP o por usuario cada 15 minutos (después, hay que esperar). Se cuenta en la memoria del proceso: alcanza con una sola instancia; con varias haría falta una caché común | Es un cambio de autenticación que la guía de seguridad pide consultar; lo dejé por defecto porque el login no tenía ningún límite |
| R50 | T6.3 | La CSP permite estilos en línea (`style-src 'unsafe-inline'`), por los colores de los escudos y del organizador. Los scripts, no | El riesgo de los estilos en línea es mucho menor que el de los scripts |
| R51 | T6.3 | Se sacaron las rutas de "olvidé mi contraseña" (no hay correo). Si alguien la olvida, la organización le crea otra con `crear_usuario` o le cambia la clave desde el admin | Sin correo, esas rutas no servían |
| R52 | T6.4 | Los datos personales de un torneo se borran a mano, con `anonimizar_torneo <id> --confirmo` (DESPLIEGUE.md, 3d). No hay una tarea programada que lo haga sola a fin de año | Es irreversible: mejor que alguien lo decida. Los backups de Neon también guardan esos datos hasta que vencen (T6.5) |
