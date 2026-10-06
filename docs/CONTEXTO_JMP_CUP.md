# JMP CUP — Contexto para desarrollar la app del torneo

> Documento para Claude Code. Reúne lo analizado hasta el 6 de octubre de 2026: el reglamento de la JMP CUP 2025, los Excel con los que se organizó el torneo 2023, las listas de buena fe de 2023 y las decisiones tomadas con el organizador. Léelo entero antes de proponer nada.

## 0. Qué te pido primero

1. Propón **arquitectura, stack y plan por fases** para una demo en unos 5 días, y discútelo con Sebastian antes de escribir código.
2. Todas las reglas de la sección 4 y los valores por defecto de la sección 9 van como **configuración** (en la base de datos o en archivos de configuración), nunca escritos en el código: el reglamento 2026 puede cambiar y hay 32 preguntas sin responder.
3. **Nunca uses datos reales de jugadores.** Son menores: nombres, CI y fechas de nacimiento. La demo usa jugadores inventados, y las listas reales no entran al repositorio.
4. Mantén `docs/PROGRESO.md` al día (hecho, pendiente, decisiones y supuestos). Las sesiones de trabajo pueden cortarse y hay que poder retomar sin perder contexto.
5. Si algo no está en este documento, no inventes la regla: déjala configurable con un valor por defecto razonable y anótala en `PROGRESO.md` como pregunta para el organizador.

## 1. Contexto

**Quién.** Sebastian desarrolla la app para su hermano, entrenador y organizador en **JMP Soccer School** (Santa Cruz de la Sierra, Bolivia). JMP organiza la **JMP CUP**, un torneo de fútbol infantil y juvenil entre escuelas de fútbol. La 4.ª edición se jugó del 17 de octubre al 16 de noviembre de 2025; la de 2026 empieza a fines de octubre.

**Problema.** El fixture y el calendario se arman a mano en Excel, y solo el organizador sabe hacerlo. Los cruces fallan:

- profes que dirigen varios equipos y quedan con partidos que se pisan;
- partidos de la ACF que chocan con los del torneo;
- cambios de último momento;
- equipos que se inscriben tarde y obligan a rehacer una categoría entera.

Antes usaban Copa Fácil, que arma los cruces y la tabla pero no asigna día, hora y cancha según esas restricciones.

**Qué se busca.** Una app para la organización que:

- inscriba equipos con sus listas;
- arme el fixture según el reglamento;
- programe los partidos en canchas y horarios sin choques;
- proponga reprogramaciones cuando algo cambia;
- publique el calendario como imagen para compartir por WhatsApp.

**Usuarios.** Solo la organización de JMP: el organizador y la mesa de control.

- Los clubes **no** usan la app. Mandan su lista de buena fe por WhatsApp en cualquier formato (Excel, Word, foto o papel), y la organización la carga a mano con un formulario interno.
- Más adelante podría sumarse un formulario público para los clubes y una página pública del calendario. No es parte de la demo.

**Interfaz.** No hace falta un frontend separado (SPA), pero la organización sí necesita pantallas:

- formulario de inscripción;
- fixture y calendario;
- propuestas de reprogramación;
- vista exportable como imagen.

Pueden ser páginas renderizadas por el backend. Tienen que funcionar bien en el celular.

### Glosario

| Término | Significado |
|---|---|
| Categoría | Sub N, por año de nacimiento (en 2025, Sub 9 = nacidos en 2016) |
| Nivel | Inicial o Avanzado (de Sub 7 a Sub 17). Sub 5, Sub 6 y Sub 15 Femenino tienen nivel único |
| Serie o grupo | División de una categoría en la fase de grupos |
| Fecha | Ronda o jornada del fixture (fecha 1, fecha 2…) |
| Fixture | Quién juega contra quién en cada fecha |
| Programación | Día, hora y cancha de cada partido |
| Lista de buena fe | Lista de jugadores y cuerpo técnico de un equipo |
| Profe | Integrante del cuerpo técnico: entrenador, asistente o delegado |
| W.O. | Walkover: un equipo no se presentó |
| ACF | Asociación Cruceña de Fútbol. Sus partidos tienen prioridad sobre el torneo |
| ACEFI | Asociación de escuelas de fútbol infantil a la que pertenecen los clubes |
| Mesa de control | Quien registra cada partido en la cancha (planillero) |
| Copa de Oro, Plata y Bronce | Las tres copas que se juegan en cada categoría |

## 2. Alcance de la demo

Objetivo: mostrársela al organizador para que dé el visto bueno, diga qué falta y responda las preguntas de la sección 9. Tiene que verse real con datos de prueba.

**Entra en la demo:**

1. **Configuración del torneo:** categorías, niveles, topes de jugadores, duraciones, formatos, canchas y franjas horarias (sección 4).
2. **Inscripción interna:** clubes, equipos (club + categoría + nivel), jugadores y cuerpo técnico, con las validaciones de 4.2.
3. **Fixture:** generador por categoría según la cantidad de equipos (formatos de 3 a 10 equipos, sección 4.5).
4. **Programación automática:** día, hora y cancha de cada partido, con las restricciones de la sección 5.
5. **Reprogramación:** cargar un partido de la ACF de un equipo, o suspender una fecha, y recibir 2 o 3 propuestas que muevan lo mínimo.
6. **Calendario:** vista por día y cancha (también por categoría y por club), exportable como imagen PNG.

**Queda para después:** resultados y tabla de posiciones, goleadores, tarjetas, multas y suspensiones, Copa Rotativa, importación de Excel, formulario público para clubes, planilla de partido imprimible y roles de usuario más finos.

Orden sugerido: 1 → 2 → 3 → 4 → 5 → 6. El paso 4 es el más riesgoso; conviene llegar a él con el fixture ya probado.

## 3. Restricciones técnicas

- **Base de datos:** PostgreSQL en la nube con plan gratuito (Neon, Supabase u otro).
- **Hosting:** gratuito (Vercel, Render u otro). Antes de elegir, revisa los límites actuales del plan gratuito:
  - tiempo máximo por request;
  - si el servicio se duerme por inactividad;
  - si la base de datos se pausa.
- **Solver:** programar el calendario puede tardar de segundos a minutos.
  - Necesita un límite de tiempo y tiene que devolver la mejor solución encontrada.
  - Si el hosting corta los requests largos, hay que correrlo en segundo plano.
- **Sugerencia para discutir:** OR-Tools CP-SAT para la programación, que es nativo en Python. Si el backend termina en Node/NestJS, conviene evaluar un servicio aparte en Python solo para el solver.
- **Desarrollador:** Sebastian maneja JS/NestJS, Docker y PostgreSQL, y quiere practicar Python (tipado y tests). Trabaja en Arch Linux con 16 GB de RAM.
- **Zona horaria:** `America/La_Paz`. La interfaz va en español.
- **Datos personales:** la base guarda nombres, CI y fechas de nacimiento de menores.
  - Acceso solo con login.
  - Esos datos no aparecen en vistas públicas ni en logs.
  - El calendario exportado muestra solo equipos, canchas y horarios.

## 4. Reglas del negocio (reglamento JMP CUP 2025)

Todo esto va como configuración. Entre paréntesis, la parte del reglamento de donde sale.

### 4.1 Categorías (Convocatoria y Reglamento deportivo)

| Categoría | Nacidos en (2025) | Nivel | Modalidad Ini / Av | Jugadores Ini / Av | Minutos por tiempo Ini / Av |
|---|---|---|---|---|---|
| Sub 5 | 2020 | Único | F5 o F7 (ver P14) | 8–10 | 15 |
| Sub 6 | 2019 | Único | F7 | 8–12 | 15 |
| Sub 7 | 2018 | Ini y Av | F7 / F7 | 10–14 / 10–14 | 20 / 20 |
| Sub 8 | 2017 | Ini y Av | F7 / F7 | 10–14 / 10–14 | 20 / 20 |
| Sub 9 | 2016 | Ini y Av | F7 / F7 | 12–14 / 12–14 | 20 / 20 |
| Sub 10 | 2015 | Ini y Av | F7 / F8 | 12–14 / 12–16 | 20 / 20 |
| Sub 11 | 2014 | Ini y Av | F7 / F8 | 12–14 / 12–16 | 20 / 20 |
| Sub 12 | 2013 | Ini y Av | F7 / F11 | 12–14 / 18–22 | 20 / 25 |
| Sub 13 | 2012 | Ini y Av | F7 / F11 | 12–14 / 18–22 | 20 / 25 |
| Sub 14 | 2011 | Ini y Av | F7 / F11 | 12–14 / 18–22 | 20 / 30 |
| Sub 15 | 2010 | Ini y Av | F7 / F11 | 12–14 / 18–22 | 20 / 30 |
| Sub 17 | 2009 y 2008 | Ini y Av | F7 / F11 | 12–14 / 18–22 | 20 / 30 |
| Sub 15 Femenino | 2010 | Único | F7 | 10–14 | 20 |

- **Año de nacimiento** = año del torneo − N. Sub 17 abarca dos años (año − 17 y año − 16). En 2026, Sub 9 son los nacidos en 2017.
- **Partido:** dos tiempos más 5 minutos de descanso.
- **Modalidad por nivel:** que Inicial juegue F7 y Avanzado F8 u F11 es una lectura de "Fútbol 7/8" y "Fútbol 7-11" en el reglamento; falta confirmarla (P15).
- **Convocados:** en F11 la lista admite 22 jugadores, pero a cada partido van 18.
- **Balón** (solo informativo): de iniciación en Sub 5, N.º 4 de Sub 6 a Sub 9, N.º 5 desde Sub 10.

Configuración inicial sugerida (año 2026, con los valores por defecto de la sección 9):

```json
{
  "torneo": {"nombre": "JMP CUP 2026", "edicion": 5, "anio": 2026, "inicio": "2026-10-23", "fin": "2026-11-22", "zona_horaria": "America/La_Paz"},
  "partido": {"descanso_min": 5, "cambio_entre_partidos_min": 5},
  "categorias": [
    {"nombre": "Sub 5",  "edad": 5,  "anios_nacimiento": 1, "niveles": {"unico":    {"modalidad": "F5",  "min": 8,  "max": 10, "min_por_tiempo": 15}}},
    {"nombre": "Sub 6",  "edad": 6,  "anios_nacimiento": 1, "niveles": {"unico":    {"modalidad": "F7",  "min": 8,  "max": 12, "min_por_tiempo": 15}}},
    {"nombre": "Sub 7",  "edad": 7,  "anios_nacimiento": 1, "niveles": {"inicial":  {"modalidad": "F7",  "min": 10, "max": 14, "min_por_tiempo": 20},
                                                                         "avanzado": {"modalidad": "F7",  "min": 10, "max": 14, "min_por_tiempo": 20}}},
    {"nombre": "Sub 8",  "edad": 8,  "anios_nacimiento": 1, "niveles": {"inicial":  {"modalidad": "F7",  "min": 10, "max": 14, "min_por_tiempo": 20},
                                                                         "avanzado": {"modalidad": "F7",  "min": 10, "max": 14, "min_por_tiempo": 20}}},
    {"nombre": "Sub 9",  "edad": 9,  "anios_nacimiento": 1, "niveles": {"inicial":  {"modalidad": "F7",  "min": 12, "max": 14, "min_por_tiempo": 20},
                                                                         "avanzado": {"modalidad": "F7",  "min": 12, "max": 14, "min_por_tiempo": 20}}},
    {"nombre": "Sub 10", "edad": 10, "anios_nacimiento": 1, "niveles": {"inicial":  {"modalidad": "F7",  "min": 12, "max": 14, "min_por_tiempo": 20},
                                                                         "avanzado": {"modalidad": "F8",  "min": 12, "max": 16, "min_por_tiempo": 20}}},
    {"nombre": "Sub 11", "edad": 11, "anios_nacimiento": 1, "niveles": {"inicial":  {"modalidad": "F7",  "min": 12, "max": 14, "min_por_tiempo": 20},
                                                                         "avanzado": {"modalidad": "F8",  "min": 12, "max": 16, "min_por_tiempo": 20}}},
    {"nombre": "Sub 12", "edad": 12, "anios_nacimiento": 1, "niveles": {"inicial":  {"modalidad": "F7",  "min": 12, "max": 14, "min_por_tiempo": 20},
                                                                         "avanzado": {"modalidad": "F11", "min": 18, "max": 22, "min_por_tiempo": 25, "convocados_por_partido": 18}}},
    {"nombre": "Sub 13", "edad": 13, "anios_nacimiento": 1, "niveles": {"inicial":  {"modalidad": "F7",  "min": 12, "max": 14, "min_por_tiempo": 20},
                                                                         "avanzado": {"modalidad": "F11", "min": 18, "max": 22, "min_por_tiempo": 25, "convocados_por_partido": 18}}},
    {"nombre": "Sub 14", "edad": 14, "anios_nacimiento": 1, "niveles": {"inicial":  {"modalidad": "F7",  "min": 12, "max": 14, "min_por_tiempo": 20},
                                                                         "avanzado": {"modalidad": "F11", "min": 18, "max": 22, "min_por_tiempo": 30, "convocados_por_partido": 18}}},
    {"nombre": "Sub 15", "edad": 15, "anios_nacimiento": 1, "niveles": {"inicial":  {"modalidad": "F7",  "min": 12, "max": 14, "min_por_tiempo": 20},
                                                                         "avanzado": {"modalidad": "F11", "min": 18, "max": 22, "min_por_tiempo": 30, "convocados_por_partido": 18}}},
    {"nombre": "Sub 17", "edad": 17, "anios_nacimiento": 2, "niveles": {"inicial":  {"modalidad": "F7",  "min": 12, "max": 14, "min_por_tiempo": 20},
                                                                         "avanzado": {"modalidad": "F11", "min": 18, "max": 22, "min_por_tiempo": 30, "convocados_por_partido": 18}}},
    {"nombre": "Sub 15 Femenino", "edad": 15, "anios_nacimiento": 1, "genero": "F", "niveles": {"unico": {"modalidad": "F7", "min": 10, "max": 14, "min_por_tiempo": 20}}}
  ],
  "canchas": [
    {"codigo": "C1", "nombre": "Cancha 1", "mitades": ["C1A", "C1B"]},
    {"codigo": "C2", "nombre": "Cancha 2", "mitades": []},
    {"codigo": "C3", "nombre": "Cancha 3", "mitades": []}
  ],
  "compatibilidad_canchas": {
    "por_categoria": {"Sub 5": ["C1A", "C1B"], "Sub 6": ["C1A", "C1B"]},
    "por_modalidad": {"F7": ["C1", "C2"], "F8": ["C1"], "F11": ["C3"]}
  },
  "franjas": {"viernes": ["16:00", "20:00"], "sabado": ["08:00", "16:00"], "domingo": ["08:00", "16:00"]},
  "cuerpo_tecnico": {"max_por_equipo": 3, "roles": ["entrenador", "asistente", "delegado"]}
}
```

Las canchas y su compatibilidad copian lo que se usó en 2023 (sección 6.1). Hay que poder editarlas, porque la configuración de 2026 no se conoce (P13).

### 4.2 Inscripción (Inscripción, Cuerpos técnicos y Documentación)

**Reglas:**

- Un equipo = club + categoría + nivel. Topes de jugadores según 4.1.
- Cuerpo técnico: máximo 3 personas por equipo, cada una con un rol fijo (entrenador, asistente o delegado). Solo el entrenador dirige desde la cancha.
- Documentación: la lista de buena fe más el CI original o el pasaporte de cada jugador. La mesa marca a cada jugador como "verificado" cuando ve el documento.
- Plazos 2025: inscripción del 15 de septiembre al 13 de octubre. El reglamento dice que la lista se entrega hasta el "lunes 15 de octubre", pero ese día fue miércoles (P4). Los plazos son configurables.
- Costo 2025: 1000 Bs de Sub 5 a Sub 7 y 1200 Bs de Sub 8 a Sub 17. En la demo basta con un campo opcional "pagado".

**Validaciones al cargar:**

- **Edad:** el año de nacimiento tiene que corresponder a la categoría. Por defecto se puede jugar en una categoría mayor, nunca en una menor (P6).
- **Cantidad:** jugadores entre el mínimo y el máximo. Avisa si faltan y no deja pasar del máximo.
- **CI:** dígitos con sigla de departamento opcional (SC, LP, CB, CH, OR, PT, TJ, BN, PA), prefijo "E-" para extranjeros o complemento ("-1E"); también puede ser un pasaporte. Hay que normalizarlo para comparar.
- **CI repetido en otro equipo:** por defecto se permite solo dentro del mismo club y en otra categoría (P7). Eso crea una restricción: esos dos equipos no juegan a la vez (sección 5).
- **Profe en varios equipos:** se permite, y crea la misma restricción de no superposición. Se detecta por CI, no por nombre.
- **Dorsal:** opcional al inscribir, obligatorio antes del primer partido y único dentro del equipo (P9).
- **Datos del equipo:** nombre visible, club, categoría, nivel y colores de las camisetas 1 y 2. El reglamento pide que, si los colores coinciden, el visitante use la camiseta alterna.

### 4.3 Sede y horarios (Organización, Terreno de juego y Programación)

- Todos los partidos se juegan en JMP Soccer School (Urubo, condominio Villa Bonita), en pasto sintético.
- Franjas: viernes de 16:00 a 20:00; sábado y domingo de 8:00 a 16:00.
- Se respetan los horarios de la ACF. Fuera de eso, los clubes no pueden pedir horarios: "no habrá requerimientos para ninguna escuela participante".
- Si se suspende una fecha por lluvia u otro motivo, se reprograma entre semana: la organización agrega franjas entre semana.
- Los cambios de programación se avisan por WhatsApp; los resultados y estadísticas se publican en redes y en los grupos de WhatsApp.

### 4.4 Duración y turnos (sección 6)

| Categorías | Partido | Turno (partido + 5 min de cambio) |
|---|---|---|
| Sub 5 y Sub 6 | 15 + 5 + 15 = 35 min | 40 min |
| Sub 7 a Sub 11, todas las iniciales y Sub 15 Femenino | 20 + 5 + 20 = 45 min | 50 min |
| Sub 12 y Sub 13 Avanzado | 25 + 5 + 25 = 55 min | 60 min |
| Sub 14, Sub 15 y Sub 17 Avanzado | 30 + 5 + 30 = 65 min | 70 min |

- **Turnos:** los 5 minutos de cambio salen de los horarios de 2023, que coinciden exactamente con esta tabla. Falta confirmarlos (P16).
- **W.O.:** se espera 10 minutos en el primer partido del día y 5 en los demás. Si el equipo llega tarde y el rival acepta, juegan el tiempo que queda. El marcador por defecto es 3–0 (P23).

### 4.5 Formatos por cantidad de equipos (sección 9)

| Equipos | Fase de grupos | Copa de Oro | Copa de Plata | Partidos |
|---|---|---|---|---|
| 3 | Todos contra todos, ida y vuelta (6) | El 1.º va directo a la final; semi 2.º vs 3.º | El perdedor de la semi es campeón de Plata, sin partido | 8 |
| 4 | Todos contra todos (6) | Semis 1.º vs 4.º y 2.º vs 3.º; final | Final entre los perdedores de las semis | 10 |
| 5 | Todos contra todos (10) | Final 1.º vs 2.º | Final 3.º vs 4.º; el 5.º queda eliminado | 12 |
| 6 | Series A y B de 3. Cada equipo juega contra los 3 de la otra serie (9) | Semis 1.º A vs 2.º A y 1.º B vs 2.º B; final | Semi 3.º A vs 3.º B; final contra el mejor perdedor de las semis de Oro (P26) | 14 |
| 7 | Serie A de 4 y B de 3. Cada equipo juega contra todos los de la otra serie (12) | Semis 1.º A vs 2.º A y 1.º B vs 2.º B; final | El mejor 3.º va directo a la final (P26); el otro 3.º juega una semi contra el 4.º A | 17 |
| 8 | Dos series de 4, todos contra todos dentro de cada serie (12) | Semis 1.º A vs 2.º B y 1.º B vs 2.º A; final | Semis 3.º A vs 4.º B y 3.º B vs 4.º A; final | 18 |
| 9 | Series de 4 (A) y 5 (B), todos contra todos dentro de cada serie (16) | Igual que con 8 | Igual que con 8; el 5.º B queda eliminado | 22 |
| 10 | Dos series de 5, todos contra todos dentro de cada serie (20) | Igual que con 8 | Igual que con 8, más una final de Bronce | 27 |

**Casos especiales:**

- **Bronce con 10 equipos:** el reglamento dice "5.º A vs 4.º B", pero el 4.º B ya juega la Plata. Por defecto, 5.º A vs 5.º B (P25).
- **2 equipos, o más de 10:** no hay formato. Por defecto, con 2 se juega ida y vuelta, y con más de 10 la app avisa que falta el formato (P27).
- **Con 7 equipos**, los de la serie B juegan un partido más que los de la A. Eso afecta la comparación del "mejor 3.º".

**Notas de implementación:**

- **Todos contra todos:** usa el método del círculo (Berger) y **testea** dos cosas: que cada par se enfrente exactamente una vez (o dos en ida y vuelta) y que ningún equipo juegue dos veces en la misma fecha. Las plantillas de Excel de 2023 para 5, 7 y 9 equipos estaban mal: cada equipo enfrentaba dos veces a dos rivales y nunca a otros.
- **Series cruzadas (6 y 7 equipos):** cada equipo de A juega contra cada equipo de B, repartido en fechas sin que nadie juegue dos veces en la misma fecha. Con series de 4 y 3, en cada fecha descansa un equipo de A.
- **Mismo club en un grupo:** por defecto, dos equipos del mismo club se enfrentan en la fecha 1 (P24).
- **Eliminación:** los partidos llevan participantes "por definir" ("1.º serie A") hasta que haya posiciones, pero igual necesitan turno en el calendario (normalmente el último fin de semana). Un empate en eliminación se define con 3 penales por equipo (sección 8).

### 4.6 Puntos y desempate (secciones 8 y 12)

- **Puntos:** 3 por ganar, 1 por empatar y 0 por perder.
- **Desempate** entre dos o más equipos, considerando solo los partidos entre ellos:
  1. puntos;
  2. goles a favor;
  3. menos goles en contra;
  4. fair play: menos tarjetas amarillas y rojas;
  5. si siguen empatados, sorteo que registra el organizador (P28).
- **Sanciones del comité:** puede descontar 3 puntos o expulsar a un equipo (sección 5.2). Hace falta un ajuste manual de puntos con motivo.
- **Ojo:** el Excel de 2023 desempataba por diferencia de gol y gol average. Esa ya no es la regla.

### 4.7 Tarjetas y sanciones (secciones 5, 10 y 11). Fuera de la demo

- **Sub 5 a Sub 7:** amonestaciones verbales.
- **Sub 5 a Sub 9:** dos amarillas en un partido sacan al jugador 5 minutos.
- **Sub 10 a Sub 17:** dos amarillas en un partido son roja. El jugador paga 30 Bs al terminar o queda suspendido un partido.
- **Multas:** 500 Bs por desorden del público; 1000 Bs por agresión física o verbal, con el equipo suspendido. Se retienen los carnets hasta que se pague.
- **Pendiente:** la roja directa y las amarillas acumuladas no están definidas (P29).

### 4.8 Premios. Fuera de la demo

- **Copas:** de Oro, Plata y Bronce de Sub 5 a Sub 17, con trofeo y medallas para el 1.º y el 2.º.
- **Mejor jugador de cada partido:** lo eligen el árbitro y la mesa.
- **Medallas de participación:** de Sub 5 a Sub 9.
- **Copa Rotativa:** para la escuela con más copas de oro, o con más victorias (P30).

## 5. Programación: restricciones

### Duras

1. **Canchas:** cada cancha, o mitad de cancha, tiene un partido a la vez. La cancha 1 se usa entera o en dos mitades (C1A y C1B); entera ocupa las dos mitades.
2. **Compatibilidad:** cada categoría y nivel juega solo en las canchas compatibles con su modalidad (configurable, ver 4.1).
3. **Franjas:** los partidos van dentro de las franjas del día (4.3), con el turno de 4.4.
4. **Equipos:** un equipo no tiene dos partidos que se pisen. Si juega dos el mismo día, queda al menos un turno libre en medio (P17). El máximo de partidos por día es configurable.
5. **Profes:** un profe (identificado por CI) no tiene dos partidos que se pisen, y solo puede tener partidos seguidos si son en la misma cancha (P18).
6. **Jugadores en dos equipos:** esos dos equipos no juegan a la vez.
7. **Bloqueos ACF:** un equipo no juega dentro de un bloqueo (día y hora de su partido de la ACF). Son los únicos pedidos que se aceptan.
8. **Orden de fechas:** los partidos de cada equipo van en orden de fecha (P19). Puede configurarse como restricción blanda.
9. **Eliminación:** va después de la fase de grupos, y la final después de las semis.
10. **Partidos fijos:** los partidos jugados o fijados a mano no se mueven.

### Blandas (objetivo a optimizar)

1. Agrupar los partidos de un mismo club, seguidos y en la misma cancha (P20).
2. Dejar pocos huecos libres en cada cancha y repartir la carga entre fines de semana.
3. Al reprogramar, mover la menor cantidad de partidos y equipos, y preferir el mismo fin de semana.

### Qué tiene que devolver

- **Calendario:** el calendario completo o, si no entra todo, la lista de partidos sin ubicar con el motivo (falta de canchas o choque).
- **Verificador de choques:** una pieza independiente que recibe cualquier calendario (también uno hecho a mano) y lista todos los choques. Sirve para tests y para revisar cambios manuales.
- **Reprogramación:** 2 o 3 propuestas distintas, ordenadas por cuántos partidos mueven.

### Capacidad

Cada cancha tiene 20 horas por fin de semana: 4 el viernes, 8 el sábado y 8 el domingo. Con 3 canchas y 5 fines de semana son unos 360 turnos de 50 minutos, más lo que aportan las mitades de la cancha 1. El torneo 2023 tuvo unos 205 partidos, y en 2026 hay más categorías (Sub 14, Sub 17 y Sub 15 Femenino), así que la capacidad tiene que calcularse y mostrarse antes de programar.

## 6. Datos de referencia del torneo 2023 (sin datos personales)

### 6.1 Canchas y turnos que se usaron

| Cancha | Categorías en 2023 | Turno |
|---|---|---|
| C1A y C1B (mitades de la cancha 1) | Sub 5 y Sub 6 | 40 min |
| C1 (entera) | Sub 9 y Sub 11 Avanzado | 50 min |
| C2 | Sub 7, Sub 8, Sub 10 y Sub 11 Inicial | 50 min |
| C3 | Sub 12, Sub 13 y Sub 15 | 60 a 70 min |

Las plantillas de las semanas 2 a 4 de 2023 también mostraban "2A, 2B, 3A, 3B": quizá la 2 y la 3 también se parten (P13).

### 6.2 Equipos por categoría en 2023 (para los datos de demo)

JMP Soccer y JMP Academy son dos equipos del mismo club (JMP). En 2023 no existían Sub 14, Sub 17 ni Sub 15 Femenino: para la demo, inventa equipos con estos mismos clubes.

```json
{
  "Sub 5": ["JMP Soccer", "JMP Academy", "Leones"],
  "Sub 6": {"A": ["JMP Soccer", "River Plate", "Atlético Juniors", "De Taquito", "Panteras FC"],
            "B": ["JMP Academy", "Super Campeones", "Planeta FC", "Maravillita"]},
  "Sub 7": ["JMP Soccer", "Crack FC", "River Plate", "Maquinita", "Atlético Juniors", "Planeta FC"],
  "Sub 8 Inicial": {"A": ["Leoncitos", "Real FC", "JMP Soccer", "Super Campeones"],
                    "B": ["Blooming", "Leones", "De Taquito", "River Plate"]},
  "Sub 8 Avanzado": ["JMP Academy", "Atlético Juniors", "Planeta FC", "Crack FC", "River Plate"],
  "Sub 9 Inicial": ["Torito García", "Real FC", "Leones", "Inter Star", "River Plate", "Leoncitos"],
  "Sub 9 Avanzado": ["JMP Academy", "River Plate", "Atlético Juniors", "Super Campeones", "Maquinita", "Planeta FC"],
  "Sub 10 Inicial": ["Semillero", "Leonsangos", "Inter Star", "Leones PFC"],
  "Sub 10 Avanzado": ["JMP Soccer", "Atlético Juniors", "Planeta FC", "Libertad", "Leones"],
  "Sub 11 Inicial": ["JMP Soccer", "Inter Star", "Real FC", "Petrolero"],
  "Sub 11 Avanzado": {"A": ["JMP Academy", "Petrolero", "River Plate", "Super Campeones"],
                      "B": ["Blooming", "Torito García", "Planeta FC", "Oriente Petrolero"]},
  "Sub 12": {"A": ["JMP Soccer", "Planeta FC", "Juniors", "Oriente Petrolero"],
             "B": ["Semillero", "Atlético Juniors", "Crack FC", "Blooming"]},
  "Sub 13 (incompleto, no hay archivo)": ["Inter Star", "Atlético Juniors", "JMP Academy", "Torito García", "River Plate"],
  "Sub 15": ["JMP Academy", "Oriente Petrolero", "Planeta FC", "JMP Soccer", "Oriente Petrolero 2", "West Riders", "River Plate"]
}
```

Nombres dudosos: "Petrolero" podría ser el segundo equipo de Oriente Petrolero; "Juniors", el segundo de Atlético Juniors; "Leones" y "Leones PFC" podrían ser el mismo club. Por eso hace falta un catálogo de clubes con alias.

### 6.3 Calendario del primer fin de semana 2023 (sábado 14 y domingo 15 de octubre)

Son 38 partidos hechos a mano. Sirven como caso de prueba para el verificador de choques y como referencia de cómo se ve un calendario real. "C1" es la cancha 1 entera; "C1A" y "C1B", sus mitades.

```csv
fecha,cancha,inicio,categoria,local,visitante
2023-10-14,C1,09:20,Sub 11 Avanzado A,River Plate,Super Campeones
2023-10-14,C1,10:10,Sub 11 Avanzado B,Planeta FC,Oriente Petrolero
2023-10-14,C1,11:00,Sub 11 Avanzado B,Blooming,Torito García
2023-10-14,C1,11:50,Sub 9 Inicial,Torito García,Real FC
2023-10-14,C1A,08:00,Sub 5,JMP Soccer,Leones
2023-10-14,C1A,08:40,Sub 6 B,JMP Academy,Maravillita
2023-10-14,C1B,08:00,Sub 6 A,JMP Soccer,Panteras FC
2023-10-14,C1B,08:40,Sub 6 B,Super Campeones,Planeta FC
2023-10-14,C2,08:00,Sub 8 Inicial,Leoncitos,Real FC
2023-10-14,C2,08:50,Sub 10 Inicial,Inter Star,Leones PFC
2023-10-14,C2,09:40,Sub 10 Avanzado,JMP Soccer,Leones
2023-10-14,C2,10:30,Sub 10 Avanzado,Planeta FC,Libertad
2023-10-14,C2,11:20,Sub 11 Inicial,JMP Soccer,Inter Star
2023-10-14,C2,12:10,Sub 11 Inicial,Real FC,Petrolero
2023-10-14,C3,08:00,Sub 12 A,Oriente Petrolero,Planeta FC
2023-10-14,C3,09:00,Sub 12 B,Atlético Juniors,Crack FC
2023-10-14,C3,10:00,Sub 15,JMP Academy,River Plate
2023-10-14,C3,11:10,Sub 13 B,Inter Star,Atlético Juniors
2023-10-15,C1,08:40,Sub 9 Avanzado,Super Campeones,Atlético Juniors
2023-10-15,C1,10:10,Sub 9 Avanzado,JMP Academy,River Plate
2023-10-15,C1,11:50,Sub 9 Avanzado,Maquinita,Planeta FC
2023-10-15,C1,12:40,Sub 9 Inicial,Leones,Inter Star
2023-10-15,C1,13:30,Sub 9 Inicial,River Plate,Leoncitos
2023-10-15,C1A,08:00,Sub 6 A,Atlético Juniors,De Taquito
2023-10-15,C1A,09:20,Sub 6 A,River Plate,Atlético Juniors
2023-10-15,C1B,08:00,Sub 6 B,JMP Academy,Planeta FC
2023-10-15,C1B,09:20,Sub 6 A,Panteras FC,De Taquito
2023-10-15,C2,08:00,Sub 8 Inicial,JMP Soccer,Super Campeones
2023-10-15,C2,08:50,Sub 7,JMP Soccer,Planeta FC
2023-10-15,C2,09:40,Sub 7,River Plate,Maquinita
2023-10-15,C2,10:30,Sub 8 Avanzado,JMP Academy,River Plate
2023-10-15,C2,11:20,Sub 8 Avanzado,Crack FC,Planeta FC
2023-10-15,C2,12:10,Sub 7,Crack FC,Atlético Juniors
2023-10-15,C2,13:00,Sub 8 Inicial,Blooming,De Taquito
2023-10-15,C3,08:00,Sub 15,Petrolero,JMP Soccer
2023-10-15,C3,08:50,Sub 12 A,JMP Soccer,Juniors
2023-10-15,C3,10:30,Sub 15,Planeta FC,West Riders
2023-10-15,C3,13:50,Sub 13 B,JMP Academy,Torito García
```

### 6.4 Profes compartidos en 2023 (para armar los datos de demo)

En las listas de 2023, 18 de los 36 profes figuraban en dos o más equipos. Estos son los grupos de equipos que compartían un mismo profe, sin nombres:

- **Crack FC:** {Sub 7, Sub 8 Avanzado, Sub 12} × 3 profes; {Sub 7, Sub 8 Avanzado} × 1.
- **River Plate:** {Sub 6, Sub 8 Avanzado}, {Sub 6, Sub 7}, {Sub 8 Avanzado, Sub 9 Inicial}, {Sub 8 Inicial, Sub 9 Avanzado}, {Sub 9 Inicial, Sub 13}, {Sub 11 Avanzado, Sub 15} y {Sub 11 Avanzado, Sub 13, Sub 15}.
- **Super Campeones:** {Sub 9 Avanzado, Sub 11 Avanzado} × 2.
- **JMP:** {Sub 6 (JMP Soccer), Sub 11} × 1.
- **Planeta FC, Leones y Leoncitos:** {Planeta FC Sub 9 Avanzado, Leones Sub 9 Inicial, Leoncitos Sub 9 Inicial} × 2.
- **Inter Star:** {Sub 10 Inicial, Sub 11 Inicial} × 2.

Además, 7 jugadores estaban en dos categorías de su club: 4 en Inter Star (Sub 10 y Sub 11 Inicial), 2 en River Plate (Sub 6 y Sub 7) y 1 en River Plate (Sub 11 Avanzado y Sub 13).

**Prueba esperada:** con estos profes sobre el calendario de 6.3, el verificador tiene que encontrar exactamente 2 choques, los dos de River Plate:

- el sábado, Sub 11 Avanzado A a las 9:20 en C1 contra Sub 15 a las 10:00 en C3;
- el domingo, Sub 6 A a las 9:20 en C1A contra Sub 7 a las 9:40 en C2.

Los partidos seguidos en la misma cancha (Crack FC en C2 a las 11:20 y 12:10; Planeta, Leones y Leoncitos en C1 a las 11:50, 12:40 y 13:30) no son choque.

### 6.5 Cómo llegan las listas de buena fe (para la futura importación)

En 2023 llegaron 19 listas: 30 equipos de 10 clubes y 432 jugadores. Venían en cinco formatos:

- la plantilla de JMP en Excel, con hojas de 12, 14, 18 y 22 convocados;
- la plantilla reordenada;
- un PDF pasado a Excel;
- una lista propia de un club, con código RUDE;
- un Word.

Otros problemas:

- **Fechas de nacimiento:** solo 2 de cada 3 eran fechas reales. El resto venía como texto dd/mm/aaaa, en una lista entera con formato mm/dd/aaaa, con solo el año (3 listas) o con el mes en letras ("12 de marzo 2014").
- **CI:** 24 vacíos (9 en una sola lista de Sub 6) y 69 con sigla de departamento, "E-" o complemento.
- **Dorsales:** 22 de 32 listas venían sin dorsales.
- **Roles:** el rol del profe aparecía escrito de 18 formas ("D.T", "DT", "Director técnico", "A.C"…). Hay que usar una lista fija.
- **Nombres de club:** inconsistentes ("Atletico Jr", "Atl.Juniors", "Atle Junior"). El club se elige de un catálogo, no se escribe.

**Plantilla 2023 (Excel):**

- Encabezado: EQUIPO, CATEGORIA, LOCALIDAD, EQUIPACION 1 + COLOR, EQUIPACION 2 + COLOR.
- Jugadores: Nº, NOMBRES, APELLIDOS, FECHA DE NACIMIENTO, Nº DOCUMENTO, DORSAL.
- Profesores (4 filas): Nº, NOMBRES, APELLIDOS, FECHA DE NACIMIENTO, Nº DOCUMENTO, FUNCION, Nº TELEFONO.

**Plantilla 2025 (Word):**

- Encabezado: EQUIPO, CAT, AÑO NACIMIENTO, EQUIPACION 1 y 2.
- 22 filas de jugadores, con las mismas columnas.
- 4 filas de profesores: Nº, NOMBRES, APELLIDOS, FECHA DE NACIMIENTO, Nº DOCUMENTO, CAT.
- No pide ni el nivel del equipo ni la función de cada profe (P11).

## 7. Modelo de datos sugerido (a refinar)

- **Torneo:** edición, año, fechas, configuración (sección 4) y franjas horarias.
- **Categoría:** nombre, edad N, años de nacimiento que abarca, género. Tiene niveles (único, inicial o avanzado), cada uno con modalidad, mínimo y máximo de jugadores, minutos por tiempo y convocados por partido.
- **Club:** nombre y alias (para unificar cómo lo escribe cada uno).
- **Equipo:** club, categoría, nivel, nombre visible y colores de las camisetas 1 y 2.
- **Persona:** CI normalizado (único), nombres, apellidos y fecha de nacimiento. Sirve para jugadores y para profes, y es lo que permite detectar que alguien está en dos equipos.
- **Jugador en equipo:** persona, equipo, dorsal y verificado (sí o no).
- **Profe en equipo:** persona, equipo y rol.
- **Cancha:** nombre, mitades y compatibilidad por categoría o modalidad.
- **Franja horaria:** fecha, inicio y fin. Incluye las franjas entre semana que se agregan para reprogramar.
- **Bloqueo:** equipo, inicio, fin y motivo (partido de la ACF).
- **Serie:** categoría, nivel y equipos.
- **Partido:**
  - categoría y nivel, y fase (grupos, semi, final; Oro, Plata o Bronce);
  - número de fecha y serie;
  - local y visitante (o "por definir" en eliminación);
  - estado: sin programar, programado, jugado, W.O. o suspendido;
  - cancha, inicio y fin, y si está fijado a mano.
- **Cambio:** quién, qué, cuándo y motivo, para el historial de reprogramaciones.
- **Después de la demo:** resultados, goles, tarjetas, multas, ajustes de puntos y mejor jugador.

## 8. Plan sugerido (para refinar contigo)

| Día | Qué | Listo cuando |
|---|---|---|
| 1 | Repo, stack, base de datos en la nube, modelo de datos, configuración de la sección 4 como datos iniciales, ABM de clubes y equipos, generador de datos de demo con jugadores inventados | Se puede crear un torneo 2026 con todas sus categorías y equipos de prueba |
| 2 | Formulario de inscripción con las validaciones de 4.2, con tests | Las validaciones de la sección 10 pasan |
| 3 | Generador de fixture con los formatos de 4.5, con tests | Los tests de la sección 10 pasan para 3 a 10 equipos |
| 4 | Programador (sección 5), verificador de choques y reprogramación con propuestas | Calendario sin choques duros para un torneo del tamaño de 2023; la prueba de 6.4 pasa |
| 5 | Vistas del calendario, exportación a PNG, pulido y ensayo de la demo | Se puede mostrar el flujo completo en el celular |

## 9. Preguntas abiertas y valor por defecto

Todas son configurables. Están también en el documento compartido con el organizador, con las mismas preguntas y los mismos números.

| # | Pregunta | Por defecto |
|---|---|---|
| P1 | ¿Quién carga las listas? | La organización, con un formulario interno. Los clubes mandan su lista por WhatsApp. Un formulario público para clubes queda para después, si lo piden |
| P2 | ¿Hasta cuándo se puede cambiar una lista, y quién aprueba? | La organización carga los cambios hasta el cierre de inscripción; después, solo el organizador |
| P3 | ¿Se aceptan listas en Excel, Word o foto? | Sí, pero se cargan a mano. La importación de Excel queda para después |
| P4 | Plazo de inscripción 2026 | Una fecha de cierre configurable |
| P5 | ¿Qué separa Inicial de Avanzado, y quién decide? | Lo indica el club al inscribirse |
| P6 | ¿Se puede jugar en una categoría mayor? | Sí; en una menor, nunca |
| P7 | ¿Un jugador en dos categorías de su club? | Sí, y esos equipos no juegan a la vez |
| P8 | ¿Dos equipos del mismo club en una categoría? | Sí |
| P9 | ¿Dorsal obligatorio al inscribir? | Opcional al inscribir, obligatorio antes del primer partido |
| P10 | ¿Planeta, Leones PFC y Leoncitos PFC son un mismo club? | Clubes separados que comparten profes |
| P11 | La lista 2025 tiene 4 profes, sin función ni nivel | Hasta 3 profes con rol, y el nivel en el equipo |
| P12 | Fechas del torneo 2026 | Cinco fines de semana desde el viernes 23 de octubre |
| P13 | Canchas 2026: cuáles, de qué tamaño y cuáles se parten | Las de 2023: C1 (divisible en C1A y C1B), C2 y C3 |
| P14 | Sub 5: ¿fútbol 5 o fútbol 7? | Fútbol 5, en media cancha |
| P15 | ¿Inicial juega F7 y Avanzado F8 u F11? | Sí |
| P16 | ¿Alcanzan 5 minutos entre partidos? | 5 minutos (turnos de 40, 50, 60 o 70) |
| P17 | ¿Un equipo puede jugar dos veces el mismo día? | Sí, con al menos un turno libre en medio |
| P18 | ¿Un profe puede tener partidos seguidos? | Nunca dos que se pisen; seguidos, solo en la misma cancha |
| P19 | ¿Se respeta el orden de las fechas? | Sí, salvo que un cambio obligue a mover un partido |
| P20 | ¿Juntar los partidos de un club? | Sí, cuando se pueda |
| P21 | ¿Cómo llegan los partidos de la ACF? | El organizador carga un bloqueo por equipo (día y hora) |
| P22 | ¿Puede entrar un equipo con la categoría empezada? | No; solo antes de armar el fixture |
| P23 | Marcador del W.O. | 3–0 |
| P24 | ¿Dos equipos del mismo club en un grupo se enfrentan primero? | Sí, en la fecha 1 |
| P25 | Bronce con 10 equipos | 5.º A vs 5.º B |
| P26 | "Mejor perdedor" y "mejor tercero" con 6 y 7 equipos | Más puntos por partido jugado; después, diferencia de gol |
| P27 | Formato con 2 equipos, o con más de 10 | 2: ida y vuelta; más de 10: avisar |
| P28 | Empate después del fair play | Sorteo que registra el organizador |
| P29 | ¿Suspenden la roja directa y las amarillas acumuladas? | Solo lo que dice el reglamento |
| P30 | Copa Rotativa: ¿copas de oro o victorias? | Copas de oro; si hay empate, victorias |
| P31 | ¿Quiénes usan la app? | Solo la organización: organizador y mesa de control |
| P32 | ¿Qué vista se comparte, y con qué diseño? | Por día y cancha, con un diseño simple, descargable como imagen. El organizador va a pasar un diseño propio |

## 10. Criterios de aceptación de la demo

**Fixture:**

- Para 3 a 10 equipos se generan 8, 10, 12, 14, 17, 18, 22 y 27 partidos.
- En la fase de grupos no hay cruces repetidos, y ningún equipo juega dos veces en la misma fecha.
- Cada equipo juega la cantidad de partidos que dice su formato.

**Inscripción:**

- Rechaza siempre a un jugador más grande que su categoría (nacido antes del año de corte). A uno más chico lo acepta, salvo que se configure lo contrario (P6).
- No deja pasar del máximo de jugadores y avisa cuando falta llegar al mínimo.
- Avisa cuando un CI ya está en otro equipo.
- Limita el cuerpo técnico a 3 personas con rol.

**Programación:**

- Con un torneo del tamaño de 2023 (unos 80 equipos), el verificador no encuentra choques duros.
- Si algo no entra, lo informa con el motivo.

**Verificador:** pasa la prueba de 6.4: exactamente 2 choques, los dos de River Plate.

**Reprogramación:** ante un bloqueo ACF sobre un partido programado, da 2 o 3 propuestas válidas, ordenadas por cuántos partidos mueven.

**Exportación:** el calendario de un día se descarga como PNG y no muestra datos personales.

## 11. Qué no hacer

- No usar datos reales de jugadores ni subir las listas de buena fe al repositorio.
- No crear acceso para clubes ni formularios públicos por ahora.
- No escribir las reglas del reglamento en el código: van como configuración.
- No inventar reglas. Si falta algo, dejarlo configurable con un valor por defecto y anotarlo en `docs/PROGRESO.md` como pregunta.