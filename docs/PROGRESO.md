# PROGRESO: app de la JMP CUP

Bitácora para retomar el trabajo si una sesión se corta. Las reglas del negocio están en [CONTEXTO_JMP_CUP.md](CONTEXTO_JMP_CUP.md). Las preguntas P1 a P32 están en su sección 9; las nuevas siguen desde P33.

## Estado

- **Fases 7 a 10 terminadas, revisadas y fusionadas a `main` (2026-10-13, PR #75 a #117).** Antes de fusionar: tests rápidos y lentos, mypy, ruff, `docker build`, la imagen con `DEBUG=false` (migraciones hasta la 0025 al arrancar) y un recorrido HTTP con login (223 de 223 sin choques, página pública sin cookies, CSP). La demo se redespliega sola desde `main`.
- **Siguiente paso (decidido por Sebastian el 2026-10-13):** hoy, la demo para que el hermano de Sebastian pruebe todo; hoy también, producción, para que la organización la use desde el 14/10. Datos reales solo en producción.
- **Fase 11 terminada (2026-10-13, PR #119 a #135):** los cambios de `docs/RESPUESTAS_Y_CAMBIOS.md` y las respuestas P78, P80 y P82 (T11.1 a T11.16). Falta la revisión de cierre de fase (`code-review-and-quality`) y la prueba de Sebastian en la demo. Siguen sin respuesta P79, P81, P83, P84, P85 y P86 (con su valor por defecto).
- **Producción arriba y prueba de Sebastian (2026-10-14 y 15):** `rondo-produccion` en Render (por ahora Free; pasar a 1 CPU antes de programar el torneo real), Neon `rondo-produccion` y R2 `rondo-production`. Todo lo que salió de la prueba, las respuestas nuevas del organizador (convocatoria 2026 y audio: P77, P78, P79, P82, P83, P84, P85, P24 y Copa Rotativa) y las preguntas nuevas P87 está en **[PENDIENTES_PRODUCCION.md](PENDIENTES_PRODUCCION.md)**. Las respuestas ya están en `docs/PREGUNTAS_JMP_CUP_2026.md` (Parte 5). Siguen abiertas P86 ("formato más corto"), P81, P87 y P90 (mismo club, urgente), y hay que confirmar detalles de P79, P84, P85 y P13/P63.
- **Fase 13 planificada (2026-10-15), esperando el visto bueno de Sebastian:** `tasks/todo.md`, T13.1 a T13.31. Meta: usar Rondo desde el 24/10 (P77). Orden: A, antes de cargar datos reales (escudo por equipo, borrar o retirar equipos, roles; 17/10); B, fallos (lo del fixture para el 20/10 y lo del día de partido para el 22/10); C, funciones para durante el torneo; D, diseño y textos. **Bloque A terminado el 2026-10-15 (PR #140 a #144)**, revisado y verificado (checkpoint A, salvo el despliegue): falta que Sebastian apruebe desplegar a producción. Siguiente: bloque B.
- **Fase 12 terminada (2026-10-14):** bloques A, B y C de `docs/PEDIDO_FASE_12.md` (PR #137 y siguientes). Falta la prueba de Sebastian en la demo: sobre todo B1, B2, B5 y C1 a C3 desde el celular.

## Para retomar (actualizado el 2026-10-13, al cerrar el chat largo)

**Orden de hoy:**

1. ~~**Claude:** verificación completa y fusión de la cadena a `main`~~ **Hecho el 2026-10-13** (PR #75 a #117).
2. **Sebastian:** cargar en Render, servicio `rondo-demo`, las cuatro variables `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID` (no `R2_ACCESS_KEY`), `R2_SECRET_ACCESS_KEY` y `R2_BUCKET=rondo-demo` (token de cuenta de R2 con Object Read & Write solo para ese bucket). Se puede hacer antes o después de fusionar: el código viejo las ignora. Guardar variables reinicia el servicio pero **no** toca los datos.
3. **Sebastian:** regenerar los datos de la demo a mano (`generar_demo --soy-la-demo` contra la rama `demo` de Neon, DESPLIEGUE paso 3c), para que tenga la plantilla 2026 nueva. Regenerar o crear otro torneo, los dos le sirven.
4. En la demo, antes de programar: agregar los jueves 29/10, 5/11 y 12/11 de 16 a 20 ("Agregar un día" en el calendario). Sin ellos, con F11 en Sub 10 y Sub 11 Avanzado, quedan 6 partidos de C3 afuera (H8, P79).
5. **El hermano de Sebastian** recorre todo el flujo en la demo.
6. **Producción, hoy:** Neon `rondo-produccion` (N. Virginia, plan Launch, 7 días de historia), servicio `rondo-produccion` en Render Standard sin Auto-Deploy, bucket `rondo-produccion` con su propio token y sus variables, primer usuario, `cargar_clubes` y el torneo desde el asistente (DESPLIEGUE, "Producción").

**Pendientes sueltos:**

- La prueba local de R2 falló: la app no ve ninguna de las cuatro variables del `.env`. `docker compose` avisa que la línea 13 del `.env` tiene una clave con un espacio: hay que corregirla (y el nombre es `R2_ACCESS_KEY_ID`). Claude no lee el `.env`; para probar corre un `manage.py shell` que solo dice si cada variable está cargada y sube, lee y borra un archivo de prueba.
- Preguntas abiertas: P78, P79, P44, P75 y "fijar a mano" (Sebastian dice que son 7).
- Enlace de Copa Fácil con las categorías ya creadas: compararlas con la convocatoria y la plantilla.
- T11.1: agregar una categoría o un nivel a un torneo ya creado.
- **Diseño:** `docs/DISENO.md`. El prototipo aprobado está en https://claude.ai/artifact/VacxSHvhh36heQY2xS8Q3a; el diseño del PNG 2026, en `docs/disenio_fixture/` (sin entrar al repo todavía).
- **Demo:** https://rondo-demo.onrender.com. Repo: https://github.com/Tiesol/rondo.
- **Verde:** `uv run pytest -m "not lento"` (905 tests, unos 5 min), `uv run pytest -m lento` (unos 3,5 min), `uv run mypy` y ruff. El chequeo del commit corre los tests rápidos (unos 5 min).

## Auditoría de RESPUESTAS_Y_CAMBIOS (2026-10-13)

Lo que el .md pide contra lo que hay en `main` después de la fase 10:

- **Ya está:** franja por inicio (P48), días por categoría y temprano (P56), F11 en la plantilla (P60), sin Sub 15 Femenino (P61), sin Bronce (P62), margen 0 y solo el entrenador (P35, P57), orden de fechas blando (P19), finales en los 2 últimos días (P55), evitar 2 partidos por día (P17), formato de más de 10 (P27), un solo rol (P64), tiempos a mano (P16), amonestación verbal, mejor jugador con interruptor (P70), W.O. y contador al reprogramar, multa de Bs 30 (P74), suspendidos del día, partir y agregar canchas desde la app (P13), PNG con plantilla aparte (P69), sin borrado automático (P76).
- **Falta o está distinto:**
  - Mover a mano **bloquea** cualquier choque (franja, compatibilidad, descanso): tiene que ser aviso con confirmación; bloqueo solo cancha física doble y equipo doble. Mover todavía **fija** el partido.
  - La plantilla solo parte C1; el .md pide mitades en las tres canchas para lo manual.
  - `eliminacion_desde_fin_de_semana` sigue en 4 (P33 pide sacarla). Falta el blando "club el mismo día" (P20).
  - El cierre de inscripción y el plantel máximo bloquean; falta `altas_tardias_hasta` (P2, P22, P84).
  - Sin pantalla de clubes (P10).
  - Día de partido (sección 3): falta el dorsal **por partido** y los convocados, el alta rápida con cámara, el minuto de cada evento, gol en contra con jugador (P72), lesión, "afuera 5 min" con hora de vuelta, Partidos de hoy por cancha con atraso, cierre automático, penales tiro por tiro y el historial de los cambios del partido.
  - Página pública: recarga cada 60 s (pide 30) y sin interruptor de goleadores (P71).
  - Rehacer el fixture con partidos jugados (P44, P80): hoy FIX-09 lo impide.

## Hecho

- 2026-10-06: lectura completa del contexto.
- 2026-10-06: contraste del calendario 2023 (6.3) con las reglas 4.4, 5 y 6.4, con un script descartable que quedó fuera del repo. Resultados en H1, H2 y H3.
- 2026-10-06: estimación de capacidad para 2026 con la configuración por defecto (H4).
- 2026-10-06: revisión de los planes gratuitos vigentes (tabla al final).
- 2026-10-06: propuesta de arquitectura, mapa de módulos y fases en [ARQUITECTURA.md](ARQUITECTURA.md). Aprobada.
- 2026-10-06: borrador de [SPEC.md](../SPEC.md), con el catálogo de reglas.
- 2026-10-06: Sebastian crea el proyecto `rondo-jmp` en Neon (São Paulo, Postgres 18, sin Neon Auth).
- 2026-10-06: repo privado en GitHub (`Tiesol/rondo`) con la documentación inicial en `main`.
- 2026-10-06: SPEC.md aprobada. Plan de las fases 0 y 1 en `tasks/`, pendiente de aprobación.
- 2026-10-06: T0.1 lista: uv con Python 3.14.7, Django 6.1.2, Pydantic 2.13 y Postgres 18.6 local. Pasan los tests, mypy y ruff.
- 2026-10-06: T0.2 lista: proyecto Django con settings por variables de entorno. `check --deploy` sin advertencias en modo producción, y sin `SECRET_KEY` no arranca.
- 2026-10-06: T0.3 lista: login obligatorio en toda la app, plantilla base con Tailwind 4.3 y HTMX 2.0.4, y comando `crear_usuario`, que valida la clave y no la muestra. Login revisado a 360 px. Falta mirar el inicio en un celular real.
- 2026-10-07: PR #1 a #4 (T0.1 a T0.4) fusionados en `main` con merge commits. `main` queda con la fase 0 hasta T0.4.
- 2026-10-07: T0.5 lista: la demo está en https://rondo-demo.onrender.com (Render gratis, Virginia), con Neon N. Virginia en la rama `demo`. Se despliega sola en cada merge a `main`. Sebastian entró con su usuario.
- 2026-10-07: el login no distingue mayúsculas en el usuario, porque el teclado del celular pone la primera sola. `crear_usuario` guarda los nombres en minúsculas.
- 2026-10-07: T0.6 lista. Medición del solver en un contenedor limitado como Render (0,1 CPU y 512 MB); ver H6.
- 2026-10-07: T0.7 lista para probar: `/diagnostico/png/` (solo staff) genera el PNG de un calendario de prueba de 1080 px con `modern-screenshot` 4.7.0, y lo comparte con la Web Share API o lo descarga. Falta la prueba de Sebastian en su Android.
- 2026-10-07: T1.1 lista: `dominio/config.py` (Pydantic, inmutable y sin claves desconocidas) y `datos/config/jmp_cup_2026.json` (4.1 y los valores por defecto). Pasan CAT-01 (años de nacimiento) y CAT-03 (turnos de 40, 50, 60 y 70), y se rechazan las configuraciones inválidas.
- 2026-10-07: T1.2 lista: `dominio/franjas.py` (15 franjas en UTC para 2026) y `dominio/canchas.py` (compatibilidad con la regla por categoría por encima de la de modalidad, y canchas físicas: C1 ocupa C1A y C1B). Todas las categorías-nivel de 2026 tienen alguna cancha.
- 2026-10-07: T1.3 lista: modelos Torneo, CategoriaNivel (con sus canchas compatibles), Cancha (con sus mitades) y Franja, y su migración. Las reglas y el cuerpo técnico se validan con el dominio en cada `save()`. Las restricciones (unicidad, máximo ≥ mínimo, fin > inicio) viven en la base.
- 2026-10-07: T1.4 lista: `manage.py cargar_config` pasa el JSON validado a la base en una transacción. Es idempotente: no borra categorías ni canchas, regenera las franjas regulares y conserva las de entre semana. Probado en local (23 categorías-nivel, 5 canchas y 15 franjas).
- 2026-10-07: T1.5 lista: admin de Torneo (con canchas y franjas en línea), CategoriaNivel (con canchas compatibles y turno) y Organizador (uno solo, con nombre y color). Las reglas inválidas muestran el error junto al campo. Se sacó "JMP" de las plantillas: ahora sale del Organizador.
- 2026-10-07: revisiones de cierre de las fases 0 y 1, y fase 2 planificada (T2.1 a T2.7 en `tasks/todo.md`), pendiente de aprobación.
- 2026-10-07: Sebastian aprueba la fase 1b.
- 2026-10-07: TU.1 lista: tokens de DISENO.md en `frontend/tailwind.css` (claro y oscuro), Bebas Neue y Figtree servidas desde la app, plantilla base con barra superior azul, barra inferior en el celular y lateral desde 900 px, y 13 parciales con su muestrario en `/diagnostico/componentes/`. El admin salió del menú. Capturas a 360 y 1024 px, en claro y en oscuro.
- 2026-10-07: TU.2 lista: grupos Organización y Mesa de control con permisos propios de Torneo (migraciones 0004 y 0005), decorador `requiere` que muestra "Solo la organización puede…" con un 403, `403.html` con el mismo diseño, `crear_usuario --rol`, el rol en la barra y la pantalla "Más" con las personas y su rol.
- 2026-10-07: TU.3 lista: cada regla de `dominio.config.Reglas` trae título, ayuda, grupo, P# e ID de regla; `describir_reglas()` deduce el tipo (sí/no, número con sus límites, opción, fecha o par) y el formulario se arma solo. Pantalla `/torneos/<id>/reglas/`, solo para la organización, con interruptores, contadores y listas.
- 2026-10-07: TU.4 lista: asistente de 4 pasos en `/torneos/nuevo/` (datos, categorías, horarios y reglas). Parte de `datos/config/jmp_cup_2026.json` (setting `PLANTILLA_TORNEO`), guarda las respuestas en la sesión, arma la configuración con `servicios/asistente.armar()`, la valida con el dominio y la carga con `cargar_configuracion`. Sin cambios crea lo mismo que `cargar_config`. No pisa un torneo con el mismo nombre y año.
- 2026-10-07: TU.5 lista: Inicio con el torneo activo (`Torneo.activo()`: el más reciente), sus pendientes (`servicios/pendientes.py`) y accesos, o la invitación a crearlo. Torneo en `/torneo/<categoría>/<pestaña>/`, con selector de categoría y pestañas por HTMX (solo se reemplaza `#categoria` y la URL cambia). Ajustes de la categoría (plantel, minutos, convocados y canchas), editables solo por la organización.
- 2026-10-07: TU.6 lista: página pública en `/t/<torneo>/<categoría>/<pestaña>/` (Partidos, Posiciones y Equipos, por ahora vacías), sin login y solo para torneos con `publico` encendido (migración 0006). La organización la enciende y apaga desde "Más". Tests que fallan si una plantilla pública nombra datos personales o si la vista importa un modelo que no está en la lista permitida.
- 2026-10-07: TU.7 lista: pantalla `/escuela/` con el nombre y los colores del organizador (principal y acento, con vista previa en vivo). Los colores pintan toda la interfaz: base.html pone `--marca`, `--acento` y `--sobre-acento` (calculado por contraste, `torneo/colores.py`), y los tokens derivan de ahí, también en modo oscuro. El principal tiene que dejar leer texto blanco (contraste de 4,5 o más). La migración 0007 cambia el verde viejo por el azul marino.
- 2026-10-07: revisión de cierre de la fase 1b; se corrigieron 5 hallazgos (ver "Revisión de la fase 1b").
- 2026-10-06: T0.4 lista: test de arquitectura (el dominio no importa Django) y hook antes del commit que rechaza listas reales y `.env`, y corre ruff y los tests rápidos. Las dos guardas se probaron con archivos trampa.
- 2026-10-07: T2.1 lista: `dominio/documentos.py` normaliza CI, CI de extranjero y pasaporte. La clave de comparación usa número, complemento y "E-"; la sigla se guarda pero no se compara. Vacío o sin dígitos es "sin documento"; lo demás que no se reconoce da un error con ejemplos. Incluye un test de propiedad (hypothesis) sobre las formas de escribir un mismo CI.
- 2026-10-07: T2.2 lista: `dominio/inscripcion.py` con funciones puras que devuelven hallazgos (error o aviso, con el ID de la regla): edad (INS-02), cantidad (INS-03), otros equipos (INS-05 a INS-07), cuerpo técnico (INS-08), dorsal (INS-09), documento (INS-10) y cierre de inscripción (INS-11, sumado porque el checkpoint de la fase pide un test por regla). 35 tests, uno o más por regla.
- 2026-10-07: T2.3 lista: modelos Club (global, con alias), Equipo, Persona (la única con datos personales; clave de documento única si existe), Jugador y Profe, con sus restricciones en la base (migración 0008). Filtro de logs `rondo/logs.py`: de un error de la base queda solo el tipo, nunca el detalle (probado con un CI repetido). `django.db.backends` queda en WARNING. Catálogo de 21 clubes de 6.2 en `datos/config/clubes.json` y comando `cargar_clubes`; admin de Club con alias uno por línea.
- 2026-10-07: T2.4 lista: `servicios/inscripcion.py` con `agregar_jugador`, `agregar_profe` y sus versiones sin guardar (`revisar_*`, para los avisos en vivo). Normaliza el documento, busca a la persona por su clave, arma la entrada del dominio con sus otros equipos y guarda solo sin errores, en una transacción que bloquea al equipo. Si el documento ya existe, valen los datos guardados, con un aviso.
- 2026-10-07: T2.5 lista: la pestaña Equipos de Torneo lista los equipos con escudo (sigla y color), jugadores sobre el máximo y "Faltan N". Alta de equipo (organización y mesa) con club del catálogo, categoría, nombre visible y colores. Ficha del equipo con chips de estado y pestañas Plantel y Cuerpo técnico. Inicio cuenta de verdad las categorías sin equipos y los equipos debajo del mínimo.
- 2026-10-07: T2.6 lista: alta de jugadores y del cuerpo técnico desde la ficha del equipo, con avisos en vivo (HTMX al salir de cada campo, sin guardar: `/revisar/`). Los avisos no bloquean; los errores sí. Formularios sensibles (`sensitive_post_parameters`). La mesa marca a cada jugador como verificado tocando su estado (INS-12). Los mensajes se apilan; los avisos quedan hasta cerrarlos, y no se repite lo que ya muestra la ficha. Cada criterio de inscripción de la sección 10 tiene su test desde la pantalla.
- 2026-10-07: T2.7 lista: `manage.py generar_demo --soy-la-demo` arma 93 equipos (los 84 de 2023 en las categorías 2026 y 3 en cada categoría nueva), con 1.331 jugadores y 201 profes inventados por faker con semilla fija, en 1,4 s y en bloque. Incluye los profes y los 7 jugadores compartidos de 6.4, y casos para ver los avisos: menores, sin CI, sin dorsales y 3 equipos cortos. `Torneo.es_demo` (migración 0010) protege los datos que no son de demo. `faker` entra como dependencia de desarrollo.
- 2026-10-07: revisión de cierre de la fase 2; se corrigieron 2 hallazgos (ver "Revisión de la fase 2").
- 2026-10-07: fase 3 planificada (T3.1 a T3.7 en `tasks/todo.md`).
- 2026-10-07: T3.1 lista: `datos/config/formatos.json` con los formatos de 2 a 10 equipos (4.5, P25, P26 y P27) y `dominio/formatos.py`, que los valida (series que suman, referencias a partidos anteriores y a series y puestos que existen) y da los textos de cada participante ("1.º A", "Ganador de la semi 1 de Oro", "Mejor 3.º"). De 3 a 10 equipos dan 8, 10, 12, 14, 17, 18, 22 y 27 partidos; con más de 10, `FormatoFaltante` cita P27. `Estricto` pasa a ser público en `dominio.config`.
- 2026-10-07: T3.2 lista: `dominio/cruces.py` arma la fase de grupos por rondas: todos contra todos por el método del círculo, series cruzadas (con 4 y 3 descansa uno de A por fecha) y todos contra todos dentro de cada serie con las fechas alineadas. La ronda con más cruces del mismo club pasa a ser la fecha 1 (P24), y la ida y vuelta invierte la localía. Tests de propiedad (hypothesis) para 2 a 10 equipos.
- 2026-10-07: T3.3 lista: `dominio/fixture.py` con `sortear_series` (semilla; reparte primero a los clubes con más equipos, cada uno donde tenga menos de su club, P45) y `armar_fixture`, que usa las series dadas o las sortea, valida sus tamaños contra el formato y devuelve los partidos de grupos con fecha y los de eliminación con participantes por definir (FIX-08).
- 2026-10-07: T3.4 lista: modelos Serie y Partido (migración 0011), con local distinto de visitante y clave única por categoría en la base. `servicios/fixture.py`: `generar_fixture` respeta las series guardadas si siguen valiendo, rehace solo si la regla lo permite y no hay partidos jugados (FIX-09), y avisa P27 con más de 10 equipos; `generar_fixtures_faltantes` no pisa ninguno. `generar_demo` borra antes el fixture de demo. Nota: si mypy no ve una relación inversa nueva (`categoria.partidos`), es su caché incremental: `rm -rf .mypy_cache`.
- 2026-10-07: T3.5 lista: Torneo → Fixture muestra las series, los partidos por fecha (con escudos) y la eliminación por copa con sus participantes por definir. La organización lo genera, lo rehace con un sorteo nuevo o cambia equipos de serie (editor plegado; rehace el fixture). La mesa lo ve sin botones. Inicio suma el pendiente "N categorías sin fixture" y "Generar los fixtures que faltan". La página pública muestra el fixture en Partidos. Los errores quedan en pantalla hasta cerrarlos.
- 2026-10-07: T3.6 lista: `dominio/verificador.py` recibe cualquier calendario y devuelve choques por par (o por partido) con sus motivos y su tipo: cancha, compatibilidad, franja, equipo, persona y bloqueo. **Pasa la prueba 2023** (`datos/pruebas/calendario_2023.csv` con los grupos de 6.4 y las canchas de 6.1): 2 choques de personas (los de River Plate), 3 de cancha y 0 de compatibilidad. Con las canchas de 2026 aparecen los 2 de compatibilidad de H3. Un caso mínimo por tipo.
- 2026-10-07: T3.7 lista: `dominio/capacidad.py` con un flujo máximo de OR-Tools (cancha entera como recurso; una mitad ocupa media cancha) por grupo de canchas conectadas. `servicios/capacidad.py` cuenta los partidos del fixture (o los estima con el formato) para todo el torneo y para la eliminación desde P33. Pantalla `/torneos/<id>/programar/` con "¿Entra todo?". Con la demo de 93 equipos: C1 y C2, 118 de 200 h en todo el torneo y 37 de 40 h en la eliminación; C3, 68 de 100 h y 18 de 20 h.
- 2026-10-07: revisión de cierre de la fase 3; se corrigió 1 hallazgo y se cerró un hueco de los tests (ver "Revisión de la fase 3").
- 2026-10-07: fase 4 planificada (T4.1 a T4.7 en `tasks/todo.md`).
- 2026-10-07: T4.1 lista: `servicios/personas.pares_de_equipos` calcula, desde Persona, los pares de equipos que comparten a alguien, con identificadores y motivo (jugador, o profe si dirige en alguno). Con la demo: 7 pares de jugadores y 29 de profes.
- 2026-10-07: T4.2 lista: `dominio/programador/modelo.py`, un modelo CP-SAT en pasos de 5 minutos. Cada partido elige inicio (el dominio ya trae solo las franjas, P48) y cancha compatible, o queda sin ubicar. NoOverlap por cancha física (C1 ocupa C1A y C1B), por equipo con los turnos libres del día (P17) y máximo por día (P47); partidos fijos (PRO-10). Objetivo: ubicar la mayor cantidad. Cada test se comprueba con el verificador.
- 2026-10-07: T4.3 lista: el modelo suma personas (NoOverlap por par de equipos; con profe, más el margen de P35, también en la misma cancha), bloqueos (fuera del dominio), orden de fechas por equipo (P19 dura), eliminación después de los grupos de su categoría y de sus partidos referidos (sin ellos no se ubica) y desde P33, y un objetivo secundario que lleva cada fecha a su fin de semana (PRO-12).
- 2026-10-07: T4.4 lista: `dominio/programador/motivos.py` prueba, para cada partido sin ubicar, sus inicios y canchas contra el calendario resultante, y da el motivo que bloquea más candidatos (cancha, equipo, persona, bloqueo u orden). Casos especiales: sin canchas compatibles, ninguna franja, espera a un partido que tampoco entra, o hay lugar pero el solver no llegó en el tiempo.
- 2026-10-07: T4.5 lista: modelo Corrida (migración 0012) y `servicios/programador.programar_torneo`: una transacción corta bloquea el torneo y crea la Corrida (rechaza si hay otra corriendo; una colgada se da por abandonada pasado su límite más 2 min), arma el problema desde la base (hora local sin zona; referencias de la eliminación desde el formato; jugados y fijados como fijos), resuelve con `PROGRAMADOR_SEGUNDOS` y `PROGRAMADOR_TRABAJADORES`, calcula los motivos, verifica y guarda partidos y Corrida.
- 2026-10-07: T4.6 lista: el botón de Programar corre la programación con HTMX (esqueleto mientras trabaja, botón desactivado) y muestra el resultado de la última corrida: "N de M partidos programados, sin choques" y "Sin lugar" con motivos. Calendario por día (`/calendario/<fecha>/`, selector de días por HTMX) y por cancha, con la 1 y sus mitades. La página pública muestra día, hora y cancha. **Con la demo: 223 de 223 partidos programados, óptimo y sin choques, en 30 s en local con 8 trabajadores.**
- 2026-10-07: T4.7 lista: `tests/torneo/test_programar_demo.py` (marcado `lento`, unos 45 s) programa la demo entera y comprueba 0 choques duros, que todo lo que no entra tenga motivo y que entre todo (223 de 223). Se borró la espiga de T0.6 (`dominio/programador/espiga.py`, `probar_solver` y su test). La página de prueba del PNG queda hasta la fase 5.
- 2026-10-07: revisión de cierre de la fase 4; se corrigió 1 hallazgo (ver "Revisión de la fase 4").
- 2026-10-07: fase 5 planificada (T5.1 a T5.8 en `tasks/todo.md`).
- 2026-10-07: T5.1 lista: modelo Bloqueo (migración 0013; uno o varios equipos, P38) que el programador y el verificador respetan. Pantalla `/torneos/<id>/acf/` (solo la organización): equipos, día, horario y motivo; HTMX muestra al instante qué partidos programados chocan; lista de bloqueos con sus choques y botón para borrar. Inicio suma "Cargar un partido de la ACF".
- 2026-10-07: T5.2 lista: `dominio/programador/reprogramar.proponer` reusa el modelo CP-SAT (`Modelo`, ahora público): fija lo que queda fuera de la ventana y lo jugado o fijado, obliga a lo movible a seguir ubicado dentro de la ventana, intenta ubicar lo pendiente y minimiza movidos, equipos afectados y cambios de fin de semana. Prohíbe repetir el conjunto de movidos para dar hasta 3 propuestas distintas, ordenadas por cantidad. Cada una, verificada sin choques en los tests.
- 2026-10-07: T5.3 lista: modelo Cambio (migración 0014) y `servicios/reprogramar`: `calcular_propuestas(bloqueo)` guarda las propuestas en una Corrida de tipo reprogramar con una firma del calendario; `aplicar` rechaza si la firma cambió o si aparecen choques nuevos, y registra un Cambio por movimiento. Pantalla de propuestas como el prototipo (la primera, recomendada; antes tachado → después) y "Cambios recientes" en Más. Con la demo: 3 propuestas (2, 2 y 3 movimientos) en 6 s.
- 2026-10-07: T5.4 lista: "Mover" en cada turno del calendario (solo la organización): día, hora y cancha. `servicios/reprogramar.mover_a_mano` simula el cambio y lo pasa por el verificador; si hay choques con ese partido, los muestra y no guarda; si no, guarda el partido fijado (PRO-10) con su Cambio "a mano".
- 2026-10-07: T5.5 lista: `Franja.suspendida` (migración 0015), que el programador, las propuestas y la capacidad ya no usan. "Suspender este día" deja sus partidos sin programar (con su Cambio) y calcula propuestas para ubicarlos ese fin de semana o el siguiente, en la misma pantalla de propuestas ("Ubicar N partidos"). "Agregar un día entre semana" crea una franja de ese tipo. `calcular_propuestas_en` es el cálculo genérico (bloqueo o suspensión).
- 2026-10-07: T5.6 lista: `/calendario/<fecha>/png/` arma una pieza de 1220 × 690 por cancha (de a 5 partidos; si hay más, "1/2"), con el diseño de 2025: FIXTURE, el día, filas doradas con categoría, escudos, equipos y hora, el panel con la cancha, la marca y la edición, y la franja de patrocinadores. Colores de `--marca` y `--acento` (no cambian con el modo oscuro); fuente Arvo (OFL). Compartir una o todas (Web Share API con varios archivos, o descarga). Tests de que no usa datos personales. Se borró la página de prueba de T0.7.
- 2026-10-07: T5.7 lista: `/calendario/club/<id>/` muestra todos los partidos de los equipos de un club, por día y en orden; el calendario tiene un selector de club. La vista por categoría es la pestaña Fixture de Torneo (con día, hora y cancha), cubierta con un test.
- 2026-10-07: T5.8 lista: manifest (`/manifest.webmanifest`, con el nombre y el color del organizador) y service worker (`/sw.js`, sin guardar datos: si no hay red, un aviso), servidos sin login; íconos generados con `scripts/generar_iconos.py` (solo biblioteca estándar). `docs/DEMO.md` con el guion y las preguntas P13, P33, P35, P44, P46 y P50. Test lento de punta a punta: demo → fixtures → programar → bloqueo → propuestas → aplicar → PNG sin datos personales.
- 2026-10-08: revisión de cierre de la fase 5; se corrigió 1 hallazgo y se cerró un hueco de los tests (ver "Revisión de la fase 5").
- 2026-10-08: fase 6 planificada (T6.1 a T6.7 en `tasks/todo.md`; T6.5 a T6.7 necesitan a Sebastian).
- 2026-10-07: T6.1 lista: en Torneo → Fixture, cada partido de eliminación tiene "Asignar equipos" (local y visitante de la categoría, distintos). La referencia ("1.º A vs 2.º B") queda a la vista, y desde ahí el programador, el verificador, el calendario y el PNG usan esos equipos. Si el partido ya estaba programado y con esos equipos choca, se guarda igual y se avisa.
- 2026-10-07: T6.2 lista: en Más, la organización agrega personas (usuario, nombre y rol; sin staff) con una contraseña temporal generada con `secrets`, que se muestra una sola vez y no va a la sesión, los mensajes ni el log; cambia el rol de los demás (no el propio ni el del superusuario). Todos cambian su contraseña. `servicios/usuarios` también lo usa el comando `crear_usuario`.
- 2026-10-07: T6.3 lista: revisión de seguridad con modelo de amenazas. Corregido: rutas de recuperación por correo abiertas (se sacaron), sin CSP ni Permissions-Policy (agregadas), login sin límite de intentos (10 por IP y por usuario cada 15 min) y sin 500 propia. Un test recorre todas las URLs (login obligatorio salvo las públicas). `check --deploy` y `pip-audit` sin hallazgos.
- 2026-10-07: T6.4 lista: `manage.py anonimizar_torneo <id> --confirmo` (`servicios/retencion`) deja un torneo terminado sin nombres, documentos ni fechas de nacimiento (P49): "Jugador N" y "Profe N" según el plantel, con dorsales, equipos y calendario intactos; no toca a quien está en otro torneo; se niega con un torneo en curso o sin la bandera. Paso 3d de DESPLIEGUE.md.
- 2026-10-08: revisión de cierre de la parte A de la fase 6: 5 mutaciones, las 5 detectadas (ver "Revisión de la fase 6, parte A").
- 2026-10-12: T7.10 lista: `docs/DESPLIEGUE.md` tiene la sección "Producción" con la lista exacta (Neon Launch, proyecto aparte `rondo-produccion` en N. Virginia con 7 días de historia; Render Standard sin Auto-Deploy) y sus variables. `assets/.gitkeep` arregla el `staticfiles.W004` de un clon nuevo (revisión externa, punto 6). Los trabajadores del solver ya salían de `RONDO_PROGRAMADOR_TRABAJADORES`; el valor para 1 CPU se confirma en T7.12.
- 2026-10-13: T7.4 lista: `F6` en el dominio y en el modelo (migración 0016). Plantilla 2026: del 24/10 al 15/11 (11 días), eliminación desde el 4.º fin de semana, Sub 5 y Sub 6 en F6 en C1A y C1B (P63), Sub 10 y Sub 11 Avanzado en F8 (P60). El cierre de inscripción (INS-11) pasa a fecha y hora: 21/10 a las 12:00, hora local; uno guardado solo con fecha cierra al terminar ese día. Sub 15 Femenino arranca destildada en el asistente (`tildada_en_asistente`, P61). Regla nueva `dia_para_reprogramar` (jueves): "Agregar un día" propone el próximo jueves. La demo programada (test lento) sigue pasando con 4 fines de semana.
- 2026-10-13: T7.5 lista: regla `copa_de_bronce` (P62, FIX-07) en la pantalla de reglas, apagada por defecto. `Formatos.para(..., sin_copas=...)` saca las llaves de esa copa y se niega si otra llave depende de ellas; `formato_para()` la aplica en el fixture y en la capacidad. Con 10 equipos salen 26 partidos (27 con la regla prendida). SPEC, criterio 1 y FIX-07, actualizados. El aviso de fixture desactualizado al cambiar la regla queda en T7.11.
- 2026-10-13: T7.6 lista: `dominio/nacimiento.py` (`Nacimiento`: año obligatorio y fecha completa opcional; `leer_nacimiento` acepta dd/mm/aaaa con /, - o ., aaaa-mm-dd y solo el año). INS-02 mira solo el año; con solo el año da el aviso "Fecha incompleta", nunca un error. `Persona.anio_nacimiento` (migración 0017, copia el año de las fechas que ya había; restricción en la base: la fecha completa es del mismo año). El formulario pasa a texto ("12/03/2014 o 2014"), la ficha muestra "(fecha incompleta)" y la anonimización borra también el año.
- 2026-10-13: T7.7 lista: `dominio/pegado.py`. `analizar()` arma la tabla (tabuladores, o `;`), reconoce el encabezado y propone cada columna por el encabezado o por el contenido (N.º de orden 1, 2, 3… se ignora; teléfono y RUDE también). `leer_filas()` lee cada fila: separa el nombre completo (las dos últimas palabras son apellidos; con coma, "APELLIDOS, NOMBRES"), lee fechas dd/mm/aaaa, año corto, ISO con o sin hora, número de Excel, mes en letras y solo el año, y detecta una lista entera en mm/dd/aaaa (avisa y la corrige toda). Roles escritos de 18 formas ("D.T", "A.C"…) se llevan a los de la configuración. Lo que no se entiende queda como error de la fila. 44 tests, con las cinco formas de 2023 recreadas con datos inventados y tests de propiedad.
- 2026-10-13: T7.8 lista: "Pegar lista" en la ficha del equipo (`/equipos/<id>/jugadores/pegar/`). Tres pasos: pegar; elegir qué es cada columna (lista vertical con la propuesta y tres ejemplos de cada una, sin tabla ancha en el celular); y la vista previa. La vista previa es la carga real dentro de una transacción que se deshace (`servicios/pegado.cargar_lista`): muestra lo mismo que la carga a mano, incluido lo que depende de la lista entera (dorsal repetido, plantel lleno). Las filas con error se corrigen ahí mismo; guardar carga las demás y deja a la vista las que fallan. Los datos viajan solo en el formulario (sensible), nunca en la sesión. Máximo 60 filas. Capturas a 360 px con Firefox.
- 2026-10-13: T7.9 lista: "Pegar lista" también en Cuerpo técnico (`/equipos/<id>/profes/pegar/`), con la misma pantalla. Para los profes no se ofrecen las columnas de nacimiento ni dorsal (se proponen como "ignorar"); una tercera columna de texto se propone como rol. Un rol que no se reconoce queda para corregir, y un segundo entrenador o un cuarto profe dan el error de INS-08.
- 2026-10-13: T7.1 lista (revisión externa, punto 1): equipos virtuales en la eliminación. `formatos.equipos_virtuales()` da a cada llave el ganador y el perdedor que juega ("ganador de la semi 1 de Oro"); la llave que los usa lleva el mismo nombre (el mejor perdedor cuenta como todos los perdedores). El modelo y el verificador los tratan como equipos: no se pisan, dejan el turno libre de P17 y cuentan para P47. Una llave que toma posiciones de grupo (`toman_posiciones()`) deja el turno libre después de los partidos de grupos del mismo día. Con 4 equipos en una franja, la final queda a semi + 2 turnos; el verificador marca el caso de Sub 15 de la revisión; la demo programada (test lento) entra entera y sin choques. Límite conocido: P47 no suma los partidos de grupos del día a los de las llaves (con la eliminación en su propio fin de semana no pasa).
- 2026-10-13: T7.2 lista (revisión externa, punto 2; responde R41): el modelo ya no suma el margen de P35 en la misma cancha. Las personas compartidas tienen un `NoOverlap` sin margen y, para cada par de partidos de un profe compartido, una separación de 10 minutos condicionada a que vayan en canchas distintas (lo mismo que mira el verificador). Regla nueva `choque_de_profes` (P57): por defecto "Solo el entrenador"; con "Todo el cuerpo técnico" cuentan también asistente y delegado. En la demo, los pares de profes bajan de 29 a 12. La demo programada sigue entrando entera y sin choques.
- 2026-10-13: T7.3 lista (PRO-11): el objetivo penaliza la espera de cada profe compartido entre sus partidos del mismo día (del final de un turno al inicio del siguiente). Una semana de desvío en el reparto (PRO-12) pesa como una hora de espera, y ubicar un partido más pesa siempre más que todo lo blando junto. Los pesos están en el modelo (son del algoritmo, no del reglamento). Con un partido fijo a las 14:00, el del otro equipo del profe va a las 13:05 o a las 14:55. La reprogramación tiene su propio objetivo y no cambia.
- 2026-10-13: T7.11 lista: con la página pública apagada, el calendario por día y por club muestran "Borrador" y el PNG lleva un sello BORRADOR. `motivo_desactualizado()` compara los equipos del fixture con los de la categoría y la cantidad de llaves con la regla de Bronce (P62): si no coinciden, la pestaña Fixture avisa "El fixture de esta categoría está desactualizado" con el botón "Rehacer el fixture", y en Inicio aparece como pendiente. Rehacer ya borraba los partidos y su programación, y se niega con partidos jugados (FIX-09).
- 2026-10-13: T7.12 lista: medición de la programación 2026 con 1 CPU (H7). Entran los 223 partidos sin choques; espera mediana de los profes de 5 a 10 min; 0 llaves encadenadas sin descanso. Para producción, 4 trabajadores.
- 2026-10-13: T8.1 lista: dependencias `django-storages[s3]` y `Pillow` (aprobadas en el pedido). Con `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` y `R2_BUCKET`, las imágenes van a Cloudflare R2 (bucket privado, sin ACL pública, URL firmadas de 1 hora, sin pisar archivos). Sin las cuatro: disco local en desarrollo y tests (los tests en una carpeta temporal); en producción o en la demo, `IMAGENES_DISPONIBLES` es falso y el campo de imagen (`parciales/campo_imagen.html`) se ve desactivado con "Falta conectar el almacenamiento de imágenes". Los pasos de R2 están en DESPLIEGUE.md.
- 2026-10-13: T8.2 lista: `servicios/imagenes.procesar_imagen()`. Solo JPG, PNG o WebP (se abre y se verifica, no se confía en la extensión), hasta `RONDO_IMAGEN_MAX_MB` (8) y 40 MP. Aplica la orientación del teléfono, achica a 800 px (fotos) o 400 px (escudos, logos y patrocinadores), y redibuja en una imagen nueva guardada en WebP: no pasa ningún metadato (EXIF con GPS, XMP ni perfil de color; con test y mutación). Los escudos conservan la transparencia. El nombre es al azar (`fotos/<uuid>.webp`).
- 2026-10-13: T8.3 lista: `Club.escudo` (uno por club, P68), `Organizador.logo` y el modelo `Patrocinador` por torneo (imagen, nombre y orden, P69), migración 0018. Las imágenes se sirven desde la app en `/imagen/<tipo>/<id>/?v=<versión>` (escudos, logo y patrocinadores sin login; caché de 1 hora; la versión cambia con la imagen). El escudo se sube desde la ficha del equipo ("Escudo del club", solo la organización) y reemplaza a la sigla en todas las pantallas y en el PNG; el mapa de escudos va en la caché (una consulta por pantalla). El logo, en Datos de la escuela, aparece en la barra. Patrocinadores en Más → Patrocinadores. Reemplazar o quitar borra el archivo anterior. Sin almacenamiento conectado, no se sube nada y se avisa.
- 2026-10-13: T8.4 lista: `Persona.foto` y la autorización de la familia (`foto_autorizada`, con quién y cuándo; migración 0019). Pantalla "Foto" por persona (`/personas/<id>/foto/`), desde el plantel y el cuerpo técnico, para la organización y la mesa (P64, P67, P75). El formulario pregunta "La familia mandó esta foto para publicarla" (P66). La foto se sirve en `/imagen/foto/<id>/`: con sesión de quien carga listas, siempre; sin sesión, solo autorizada y en un torneo con la página pública encendida; si no, 404. Caché privada de 60 s. Quitar la foto la borra del almacenamiento y saca la autorización.
- 2026-10-13: T8.5 lista: `dominio/partido.py` (el marcador sale de los eventos; gol en contra sin jugador suma para el rival, P72; W.O. con el marcador de P23; en la eliminación, un empate pide penales que definan). Modelo `Evento` (gol, gol en contra, amarilla, roja; equipo, jugador, quién y cuándo) y en `Partido`: estado "en juego", W.O., penales y mejor jugador (P70); migraciones 0020 y 0021. Permiso nuevo `cargar_resultados` para la organización y la mesa (P64). Servicio `servicios/partido.py`: empezar, anotar (el jugador tiene que ser de ese equipo), deshacer el último, W.O., penales, mejor jugador y terminar. Un partido en juego tampoco se mueve ni deja rehacer el fixture. Pendiente de definir: qué pasa con un partido en juego si se suspende el día (hoy vuelve a "sin programar" con sus eventos).
- 2026-10-13: T8.6 lista: ficha del partido (`/partidos/<id>/ficha/`, enlazada como "Ficha" en el calendario del día) para la organización y la mesa. Marcador grande con escudos, "Empezar el partido" y W.O.; en juego, botones grandes Gol (verde), Amarilla y Roja que abren una hoja con la lista de cada equipo (dorsal y nombre) y "Gol en contra de …"; deshacer el último, penales en la eliminación, mejor jugador (se guarda al elegirlo, sin JavaScript en línea por la CSP) y terminar. Cada acción es un POST que vuelve a la ficha: funciona sin JavaScript. "Lo que pasó", con quién lo cargó y a qué hora. Capturas a 360 px. El aviso de jugador suspendido llega con T8.9.
- 2026-10-13: T8.7 lista: `dominio/tabla.py` (CONTEXTO 4.6): puntos y, entre los empatados, puntos, goles a favor, menos goles en contra y fair play solo en sus partidos; si no jugaron todos entre sí, todos los del grupo (P34, resuelve H5); si siguen empatados, sorteo (P28) o "Falta sorteo". `mejores()` para el mejor 3.º y el mejor perdedor (P26: puntos por partido y diferencia de gol). Reglas nuevas `puntos_por_partido` (3 y 1, RES-01) y `criterio_de_desempate` (reglamento 2025 o diferencia de gol del Excel de 2023, RES-02). Modelo `SorteoDeTabla` (migración 0022). La pestaña Posiciones muestra la tabla de cada serie (PJ, G, E, P, GF, GC, DG y Pts) y la organización registra el sorteo ahí. Supuesto: el fair play cuenta amarillas y rojas por igual, con las de todo el grupo. Los ajustes de puntos del comité (CONTEXTO 4.6, sección 5.2) no están: quedan anotados para después.
- 2026-10-13: T8.8 lista: `servicios/cruces.py`. Con los grupos terminados y sin sorteos pendientes, propone los equipos de cada llave sin asignar: posiciones de la tabla (1.º A, mejor 3.º y el otro 3.º por P26), ganador y perdedor de llaves jugadas (con penales), y el mejor perdedor por P26. Verifica la propuesta con el calendario en memoria y muestra los choques antes de guardar. En la pestaña Fixture, la organización ve "Cruces desde la tabla" y "Asignar estos cruces"; después se corrigen a mano (T6.1). Si falta algo, dice qué (partidos sin jugar o el sorteo). La página pública no la calcula.
- 2026-10-13: T8.9 lista: `dominio/suspensiones.py` (un incidente suspende los N partidos siguientes de su equipo). Doble amarilla desde la regla `doble_amarilla_desde` (Sub 10) sin multa pagada: un partido (P74; monto en `multa_doble_amarilla`, Bs 30). Roja directa y amarillas acumuladas solo si sus reglas lo dicen; por defecto 0 (P29). Modelos `MultaPagada` y `SuspensionManual` (migración 0023). En la ficha del partido: aviso "Suspendido" con nombre, equipo y motivo; "Multas por doble amarilla" con "Marcar que pagó Bs 30" (organización y mesa); y "Suspender a un jugador a mano" (solo la organización).
- 2026-10-13: T8.10 lista: página pública en vivo. `servicios/publico.py` es el único que lee personas para lo público: "Nombre I." y dorsal (P65), nunca CI, fecha ni apellido completo. Pestañas Partidos (con resultado, estado y enlace a la ficha), Posiciones (la tabla), Goleadores (P71, sin goles en contra) y Equipos; ficha pública del partido (`/t/<id>/partido/<id>/`: goles, tarjetas, mejor jugador, P70) y partidos de hoy de todo el torneo (`/t/<id>/hoy/`). Se recargan solas cada 60 s (HTMX). Test de privacidad que recorre todas las páginas públicas con un apellido, un CI y una fecha inventados y reconocibles. La pestaña Partidos pública sigue agrupada por fecha y, en la eliminación, por copa.
- 2026-10-13: T8.11 lista: página pública del equipo (`/t/<id>/equipo/<id>/`: escudo y plantel con "Nombre I." y dorsal; la foto, solo con autorización, P66), enlazada desde la pestaña Equipos. Patrocinadores al pie de todas las páginas públicas (P69). Las páginas públicas se guardan 45 s en la caché del proceso, aparte la página completa y el fragmento de HTMX (`Vary: HX-Request`); las internas no. Prueba de carga con 1 CPU (gunicorn con 1 worker y 4 hilos, `taskset -c 0`, base local con la demo): 500 pedidos, 100 a la vez, todos bien; con caché, mediana de 140 ms y unos 600 por segundo; sin caché, mediana de 2 s y 48 por segundo. Capturas a 360 px.
- 2026-10-13: T8.12 lista: PNG del día por cancha con el diseño 2026 (`docs/disenio_fixture/DISENO_FIXTURE_2026.md`), de 1920 × 1080. Fondo `src/torneo/static/png/fondo_fixture_1920.webp` (el JPG del PSD pasado a WebP: el chequeo del commit rechaza todo .jpg, por las listas reales en foto; los de 3840 y el mármol solo no entran al repo porque no se usan). La app dibuja el título "CANCHA 1 ~ SÁBADO 24" (con "1/2" si hace falta), filas en bloques por categoría que empiezan en dorado y alternan, categoría con la inicial del nivel si juegan Inicial y Avanzado ("SUB 7 A"/"SUB 7 I") y la mitad en media cancha, hora en dorado y los patrocinadores en blanco sobre la franja. Fuente Cinzel (OFL, servida desde la app) hasta que llegue RomanSD con una licencia que lo permita. La partición se calcula con la altura real (hasta y = 900: con los espacios entre bloques entran unas 10 filas). Nombres largos: tamaño estimado en el servidor (mínimo 23 px), afinado por JS, y después "…". **Escudos (decisión de UI):** el diseño no los tiene; van chicos (44 px) en los extremos de la fila, solo si el club tiene escudo cargado, y el nombre se corre para dejarles lugar; sin escudo, nada. Exporta a 1920 × 1080. Falta probarlo en el Android de Sebastian (R45).
- 2026-10-13: T9.1 lista: `anonimizar_torneo` también borra la foto y la autorización de cada persona anonimizada; los archivos salen del almacenamiento recién cuando la base confirma (`on_commit`). La foto de quien sigue en otro torneo queda.
- 2026-10-13: T9.2 lista: "Suspendidos del día" (`/calendario/<fecha>/suspendidos/`, desde el calendario del día) para la organización y la mesa: jugador con nombre completo (es interna y la mesa identifica con el documento) y dorsal, equipo, partido, hora, cancha y motivo, con enlace a la ficha. Sale de las mismas reglas que T8.9.
- 2026-10-13: T10.1 lista: plantilla 2026 con `profe_minutos_cambio_de_cancha` 0 (P35: todas las canchas están en el mismo predio) y `orden_de_fechas` "blanda" (P19: si se reprograma la fecha 2 después de la 3, no frena a la 3; el reparto por fin de semana igual tiende a respetar el orden). La demo programada sigue sin choques. Dos tests que suponían en qué cancha ponía el solver el primer partido ahora no dependen de eso.
- 2026-10-13: T10.2 lista: regla `fin_de_franja` (P48, PRO-03): "cuando termina el último partido" (como antes, el valor del modelo) o "cuando empieza el último partido" (la respuesta del organizador; en la plantilla 2026). El programador, el verificador y los motivos la usan. La capacidad que se muestra antes de programar sigue contando hasta el fin de la franja: queda conservadora (con último inicio entra un turno más por franja y cancha).
- 2026-10-13: T10.3 lista (P56): cada categoría tiene `dias_sin_jugar` y `prefiere_temprano` (configuración y `CategoriaNivel`, migración 0024; se editan en Ajustes de la categoría). En la plantilla 2026, Sub 5 y Sub 6 no juegan los viernes y prefieren los primeros horarios. El programador saca esos días de los inicios posibles; un objetivo blando acerca sus partidos al comienzo del día (con el mismo peso por paso que la espera de los profes); el verificador marca un partido puesto a mano en un día prohibido. La demo programada sigue sin choques.
- 2026-10-13: T10.4 lista: Sub 10 y Sub 11 Avanzado en F11 en la plantilla (respuesta a P60; plantel de 12 a 16 mientras no se responda P78). Medido en H8: sin días extra quedan 6 partidos de C3 afuera; con tres jueves de 16 a 20, entra todo. Preguntas nuevas P78 y P79.
- 2026-10-13: T10.5 lista (P13, P63): pantalla de canchas (Más → Canchas, `/torneos/<id>/canchas/`): agregar una cancha (C4, "Cancha 4"…), partir cualquiera en mitades A y B, unirlas y quitar una cancha; unir o quitar se niega si hay partidos en esas canchas. El programador y el verificador ya usaban `padre`: la entera ocupa sus mitades. Quién juega en cada cancha se elige en los ajustes de la categoría.
- 2026-10-13: T10.6 lista: dos objetivos blandos más, con el peso de una semana de desvío: un equipo no juega dos veces el mismo día (P17 y P47: se permite, pero mejor no) y las finales van en los dos últimos días (P55). Medido con 1 CPU, la demo 2026 con F11 y los tres jueves: 223 de 223, 0 choques, 0 equipos con dos partidos en un día y las 30 finales en los dos últimos días. Juntar a los equipos de un mismo club el mismo día queda para después (es preferencia y no frena nada).
- 2026-10-13: T10.7 lista (P64): por ahora todos los usuarios se crean como Organización y pueden hacer todo; la pantalla y `crear_usuario` lo proponen por defecto y lo explican. No se fusionaron los roles en el código: la mesa queda lista para cuando se separen. Anotado en DESPLIEGUE.
- 2026-10-13: T10.8 lista (P27, P54): formatos de 11 a 20 equipos en `formatos.json`, con la estructura del de 8: grupos A y B lo más parejos posible (por ejemplo, 6 y 5), todos contra todos dentro de cada uno; Copa de Oro con semis 1.º A vs 2.º B y 1.º B vs 2.º A, Copa de Plata con 3.º y 4.º. Con más de 20, sigue el aviso de que falta el formato. SPEC, FIX-01 y FIX-02, actualizados.
- 2026-10-13: T10.9 lista: la mesa marca los tiempos a mano (empezar guarda el inicio real; "Fin del 1.er tiempo", "Empieza el 2.º tiempo" y terminar guardan cada hora; migración 0025) y la ficha muestra "1.er tiempo · 12'". Evento nuevo "Amonestación" (verbal, Sub 5 a Sub 7), que no cambia el marcador. Por debajo de la categoría de la doble amarilla (Sub 10), la segunda amarilla de un jugador muestra "sale 5 minutos". Regla `mejor_jugador` (P70, por defecto prendida): apagada, no sale ni en la ficha ni en la página pública.
- 2026-10-13: T10.10 lista: en las propuestas de un pedido (bloqueo), cada partido afectado tiene "Dar W.O.: pierde <equipo>" (con el marcador de P23), y si el equipo ya reprogramó antes, la app avisa "<equipo> ya reprogramó N veces" (cuenta los pedidos de ese equipo que terminaron en un cambio aplicado). No hay límite: decide la organización. Mover la menor cantidad de partidos ya era el objetivo de la reprogramación.
- 2026-10-13: T10.11 lista: la regla del dorsal (INS-09) suma la opción "Nunca" (la plantilla 2026 la usa: sin aviso de dorsal pendiente) y la ficha del partido tiene "Cambiar un dorsal", que no deja repetir un número dentro del equipo.
- 2026-10-13: T11.2 lista (P78: flexibilidad): el verificador marca cada choque como **bloqueo** (dos partidos a la vez en la misma cancha física, o un equipo en dos partidos a la vez) o **aviso** (todo lo demás, incluido pisar solo los minutos de cambio). Mover a mano acepta cualquier día, hora y cancha o mitad: con avisos muestra "Revisa antes de mover" y "Mover igual"; con un bloqueo, "No se puede". Mover ya no fija (se sacó `Partido.fijado`, migración 0026): volver a programar todo mueve también lo movido a mano. En juego o jugado no se mueve. El solver acepta partidos fijos fuera de las franjas y no exige nada entre dos fijos (si no, un aviso confirmado lo volvía imposible). Las propuestas no mueven lo puesto a mano fuera de lo habitual. "Sin lugar", en Programar, tiene "Ubicar" por partido.
- 2026-10-13: T11.3 lista (P13, P63): la plantilla 2026 trae mitades en las tres canchas (C1A, C1B, C2A, C2B, C3A y C3B). La compatibilidad no cambia: el programador automático sigue usando solo C1 partida para F6; las otras mitades quedan para mover a mano, con el aviso "no juega en C2A" que se confirma (P79 sin respuesta: en lugar de una segunda lista de canchas "posibles", alcanza con el aviso). El selector de mover dice "Cancha 2 · mitad A". En un torneo ya creado, las mitades se agregan desde Más → Canchas.
- 2026-10-13: T11.4 lista: el fin de semana de la eliminación (P33) pasa a ser **sugerido**: sigue sirviendo para repartir las fechas de grupos, pero semis y finales pueden ir antes, apenas termina la fase de grupos de su categoría (con el turno libre de P17 entre llaves). Objetivo blando nuevo (P20): menos días distintos por club, con el peso de una semana de desvío. "¿Entra todo?" muestra solo todo el torneo por grupo de canchas; si algo no entra, "Faltan N h" y el aviso "Agrega un día en el calendario, o programa y ubica a mano lo que quede sin lugar". "Agregar un día" dice "o un horario" (cualquier día, 1.1).
- 2026-10-13: T11.5 lista: tercer nivel de hallazgo, "confirmar" (se guarda solo con "Guardar igual"). Pasar del plantel máximo (P84) y las altas después de `altas_tardias_hasta` (regla nueva; en la plantilla, el 01/11 a las 23:59, fin del 2.º fin de semana) piden confirmar. El cierre del 21/10 ya no bloquea a nadie: avisa "Fuera de plazo". Se sacó `es_organizacion` de la inscripción (con un solo rol ya no distinguía nada). Al pegar una lista, la vista previa muestra lo que pide confirmación y guardar la lista lo confirma.
- 2026-10-13: T11.6 lista (P10): Más → Clubes (`/clubes/`). Lista con escudo, cantidad de equipos y otros nombres; agregar un club (nombre y otros nombres, uno por línea, que sirven al pegar listas); ficha del club para editar, subir o quitar el escudo, ver sus equipos y "Unirlo con otro club": los equipos pasan al otro, que se queda con el nombre como alias (y el escudo, si no tenía). Se niega si los dos tienen un equipo con el mismo nombre en la misma categoría. Para quien carga listas (todos, por P64).
- 2026-10-13: T11.1 lista: "+ Categoría" al final de la lista de categorías de Torneo (`/torneos/<id>/categorias/nueva/`). Con el nombre y el nivel alcanza si la categoría es de la plantilla (por ejemplo, Sub 15 Femenino) o ya tiene otro nivel (Sub 9 Avanzado al lado de Sub 9 Inicial): edad, años, género, días, modalidad, minutos, plantel y canchas salen de ahí. Una categoría nueva ("Sub 20") pide modalidad, minutos y plantel, y toma las canchas de otra con la misma modalidad. No se repite un nivel ni se mezcla el único con otros. Después lleva a sus Ajustes para revisar.
- 2026-10-13: T11.7 lista: modelo `Registro` (migración 0027): cada acción de la ficha (empezar, tiempos, eventos, borrar, W.O., penales, dorsal, mejor jugador, multa, suspensión a mano y terminar) guarda usuario, fecha y lo de antes y después. Guarda referencias al equipo y al jugador, nunca nombres en texto: anonimizar no deja datos en el historial. La ficha tiene "Historial" (plegado) con eso y los cambios de horario (`Cambio`); Más → Historial muestra lo último del torneo con enlace a cada ficha.
- 2026-10-13: T11.8 lista (P9): modelo `Convocado` (migración 0028): quiénes juegan cada partido y con qué dorsal, único por equipo y partido **en la base** (y la pantalla dice "El 7 está repetido: Juan P., Pedro G."). Antes de empezar, la ficha muestra la planilla de cada equipo: casilla "juega", foto chica, dorsal propuesto (el del partido anterior del jugador o el habitual), "Todos" con un toque y "Entrenador presente" (`Partido.entrenador_local`/`entrenador_visitante`). Convocar a un suspendido pide "Guardar igual". Durante el partido, las hojas de Gol, Amarilla y Roja muestran primero los que juegan, con el dorsal del partido, y "Otros del plantel"; un evento de alguien que no estaba lo suma solo. "Cambiar un dorsal" cambia el del partido (el habitual del plantel queda). La página pública muestra el dorsal de ese partido en goles y mejor jugador. Titulares y suplentes no se marcan todavía (el .md dice "se pueden"; se agrega si lo piden).
- 2026-10-13: T11.9 lista (P39): "+ Agregar jugador" en la planilla de cada equipo (`/partidos/<id>/alta/<equipo>/`): foto con la cámara (`accept="image/*" capture="environment"`), nombres, apellidos, CI, año o fecha y dorsal. Corren las mismas reglas de inscripción (errores, avisos y "Guardar igual"); el jugador queda jugando ese partido con ese dorsal (el habitual queda vacío). La foto queda sin autorizar para lo público (P66). En cada fila de la planilla, la foto (o un "+") lleva a cambiarla o quitarla y vuelve a la ficha (solo se vuelve a rutas `/partidos/<id>/ficha/`). Si hay que confirmar, la foto se vuelve a elegir (un archivo no viaja de un envío al otro).
- 2026-10-13: T11.10 lista (migración 0029): cada evento guarda el minuto del reloj, seguido entre tiempos (con 20 por tiempo, el 2.º empieza en el 21'; en el descanso, el último del 1.º) y la ficha muestra "2.º tiempo · 27'". Gol en contra con el jugador que lo hizo (P72; suma al rival y no cuenta para goleadores). Evento "Lesión", interno. La página pública nunca muestra amonestaciones ni lesiones y sí el minuto de cada gol y tarjeta. Segunda amarilla hasta Sub 9: "Afuera 5 min · vuelve 10:42". Cada evento se corrige (minuto) o se borra, no solo el último; un partido terminado se corrige desde "Corregir el partido" (eventos y horas reales); el W.O. se quita. Todo queda en el historial.
- 2026-10-13: T11.11 lista: "Hoy" en la barra (`/hoy/`, para quien carga resultados): los partidos del día por cancha y hora, con marcador, estado ("Por jugar", "1T 12'", "Descanso", "2T 27'", "Terminado", "W.O." o "Sin iniciar" pasada media hora) y, en los que siguen, "15 min tarde" si un partido empezó tarde o se alargó (`dominio/hoy.py`, solo informativo; desde 5 minutos). Cada fila lleva a la ficha. Se recarga sola cada 30 s.
- 2026-10-13: T11.12 lista (P82, como respondió Sebastian): regla `cierre_automatico_min` (15). El final esperado sale de lo que marcó la mesa: con el 2.º tiempo empezado, su inicio real más los minutos del tiempo; en el descanso, el fin del 1.º más el descanso y un tiempo; si no, el inicio real más el partido. Pasado eso más 15, el partido se cierra con el marcador que tenía, `fin_real` en el final esperado y la marca `cerrado_automaticamente` (migración 0030), con su historial. Corre perezoso al abrir Hoy, la ficha y la página pública (también con el pedido periódico de HTMX), y con `manage.py cerrar_partidos_olvidados` para un cron. La ficha dice "Cerrado automáticamente. Revísalo." con "Ya lo revisé"; Hoy lo muestra como "Cerrado solo". Un partido sin iniciar no se cierra nunca.
- 2026-10-13: T11.13 lista (P83, por defecto): modelo `Penal` (migración 0031) y `dominio/penales.py`. En una llave empatada, la ficha muestra la tanda (un punto por tiro), "Convirtió" y "Falló" por equipo, a quién le toca, y "Gana X" apenas se define: 3 por equipo (regla `penales_por_equipo`), se corta si uno ya no alcanza, y después uno más por equipo hasta definir. "Deshacer el último penal". El atajo "Cargar solo el resultado" sigue, mientras no se haya pateado tiro por tiro. Todo con historial.
- 2026-10-13: T11.14 lista: la página pública se recarga cada 30 s (P73) y su caché baja a 25 s. Estado de cada partido con el minuto ("1T 12'", "Descanso", "2T 27'", "Terminado", "W.O."; nunca "Sin iniciar") y, en los que siguen, "unos 9 min tarde". Interruptor `tabla_de_goleadores` (P71; en Reglas y en el asistente): apagado, la pestaña Goleadores no aparece y su URL da 404. Amonestaciones y lesiones nunca se publican (T11.10).
- 2026-10-13: T11.15 lista (P44 y P80: los resultados cuentan): `dominio/rehacer.py` elige las series del formato nuevo que conservan la mayor cantidad de partidos jugados (en "series", los dos equipos juntos; en series cruzadas, separados; en todos contra todos, siempre), y con empate separa clubes. Con dos series prueba todos los repartos con máscaras de bits (20 equipos: 0,8 s). Si la categoría tiene partidos jugados y el fixture quedó desactualizado, la pestaña Fixture ofrece "Rehacer conservando lo jugado": una vista previa con "Se conservan N" (con su marcador), "Se borran N" (solo si no hay forma) y cuántos hay que programar. Al confirmar, los jugados quedan con sus goles, los sin jugar que siguen existiendo se quedan con su horario, y la app calcula propuestas para ubicar los nuevos sin mover lo jugado (ventana: de ahora al fin del torneo). Si la eliminación ya empezó, no se rehace. Ejemplo probado: 7 equipos con la fecha 1 jugada y llega un 8.º: se conservan los 3 partidos.
- 2026-10-13: T11.16 lista: pasada de UI/UX con capturas a 360 px (Firefox headless, base local `rondo_ux` con la demo inventada). Cambios: la barra inferior entra con 5 botones (Inicio, Hoy, Torneo, Calendario, Más); en la ficha, "Empezar el partido" va arriba de la planilla, la planilla de cada equipo se pliega con "N juegan" y "Juegan todos", la foto es un ícono de cámara y el dorsal sin flechitas; en juego, el orden es Gol/Amarilla/Roja, los secundarios, el tiempo, deshacer, "Lo que pasó", terminar, y lo demás plegado; un solo chip de estado ("1.er tiempo · 17'"); los eventos sin hora ni usuario (eso queda en el historial). Hoy sin el chip "Por jugar" repetido. Calendario del día: tocar el partido abre la ficha y queda solo "Mover" (antes se partía en dos líneas). Más: la fila del torneo ya no se rompe a 360 px; Clubes e Historial juntos. Clubes en orden alfabético con "Agregar" arriba. Mover dice "Ubicar" si el partido no tenía lugar. El botón de elegir foto tiene la forma de los demás.
- 2026-10-14: fase 12, bloque A lista (revisión externa de la fase 11):
  - **A1:** el verificador y el programador cuentan, para cada equipo que juega grupos un día, una ronda de eliminación (semi, final) por cada una que podría jugar ese día (`_maximo_con_llaves` y `grupos_y_llaves_por_dia`; las llaves por definir pueden ser de cualquiera).
  - **A2:** con orden "blanda", el programador primero exige el orden y, solo si así algo queda sin lugar, resuelve la versión blanda, donde cada par al revés cuesta en el objetivo; gana la que ubica más. En la demo con jueves: 223 de 223 y 0 fechas al revés (antes 57 pares).
  - **A3:** la plantilla 2026 deja a Sub 5 y Sub 6 sin lunes a viernes. **Producción ya creada con la plantilla vieja: Sebastian tiene que cambiarlo a mano** en Torneo → Sub 5 → Ajustes y Sub 6 → Ajustes, "Días en que no juega": tildar de lunes a viernes (hoy solo tiene el viernes).
  - **A4:** `Franja.canchas` (migración 0032, aditiva): lo que se agrega con "Agregar tiempo" es tiempo extra con las canchas donde vale (vacío: todas). El solver lo usa solo si sin él algo queda sin lugar (cada partido ahí cuesta más que todo lo blando, y ubicar cuesta más que eso). El verificador lo acepta solo en sus canchas. En la demo con jueves, los jueves solo llevan F11.
  - **A5:** "¿Entra todo?" suma por franja lo que dura el partido más largo de cada cancha (último inicio a la hora de cierre) y, aparte, el tiempo agregado: "Entra usando el tiempo agregado" o "Faltan N h".
  - **C4:** docstrings y "Puede tardar hasta N minutos" (sale de `RONDO_PROGRAMADOR_SEGUNDOS`).
- 2026-10-14: fase 12, bloques B y C listos (`docs/PEDIDO_FASE_12.md`):
  - **B1:** "Suspender este día" abre una pantalla que dice qué se suspende ("Se suspenden los 26 partidos del sáb 31/10") y dónde se juega: por defecto el próximo jueves de 16 a 20 (crea ese tiempo solo, `Corrida.parametros.franja_extra`); se puede elegir otro día, horario y canchas. Lo suspendido se ubica primero ahí; lo que no entra va a los días siguientes moviendo lo menos posible (`proponer(preferidas=…)`). Nunca se propone nada antes de ahora (también en los pedidos de equipo). Cada propuesta dice cuántos partidos ya publicados mueve.
  - **B2:** "Reanudar este día": reabre las franjas; los partidos que siguen sin lugar vuelven adonde estaban (el `Cambio` guarda dónde); los ya reubicados quedan donde están y se muestran; si el jueves agregado quedó vacío, se quita. Con confirmación.
  - **B3:** suspender no saca del calendario a los partidos en juego: se muestran aparte ("En juego cuando se suspendió"); desde su ficha se termina con ese marcador o se reprograma (vuelve a "sin programar" y a Ubicar; sus goles y tarjetas se borran y quedan en el historial).
  - **B4:** "Volver a programar" ya no ubica nada antes de ahora, no mueve lo jugado ni lo que su hora ya pasó (avisa "les falta el resultado") y, si hay algo publicado, pide confirmar diciendo cuántos se mueven. "Ubicar solo lo que falta" deja todo lo que tiene lugar donde está. El texto "Puede tardar hasta N minutos" sale de la configuración.
  - **B5:** en Mover, "Intercambiar con otro partido…": los de ese día y semana en canchas compatibles, los que no chocan primero (0,x s con los 223 partidos); los dos cambian en un paso, con el verificador (avisos con "Intercambiar igual"; bloquea solo lo imposible); queda en el historial y cuenta en el contador del equipo que lo pidió (guardado en el texto del `Cambio`, sin tocar el modelo).
  - **B6:** "Aflojar reglas solo esta vez" al suspender, en los pedidos de equipo y al recalcular propuestas: turnos libres, máximo por día, orden de fechas, minutos antes o después, mitades de cancha (no para F8 ni F11). La corrida guarda qué se aflojó y lo muestra; las reglas del torneo no cambian; aplicar verifica con las mismas reglas.
  - **B7:** un solo "¿Estás seguro?" (`views/confirmar.py`, funciona sin JavaScript) que dice qué va a pasar: suspender y reanudar, volver a programar, aplicar una propuesta, W.O., terminar un partido, borrar un evento, reprogramar un partido en juego, rehacer un fixture (o cambiar sus series), cambiar reglas (con "antes → después"), publicar y despublicar, unir o quitar una cancha, borrar un bloqueo y quitar un patrocinador. **No existen en la app** borrar un jugador, un equipo ni un partido (solo en el admin de Django) ni anonimizar (es el comando `anonimizar_torneo`): no tienen pantalla que confirmar.
  - **B8:** el calendario por club abre la ficha al tocar el partido y tiene "Mover" (mismos permisos). **B9:** las pestañas de días incluyen los días con partidos ubicados a mano sin franja.
  - **C1:** el dorsal repetido en un partido es un aviso ("El 10 está repetido: Juan P. y Luis R.") que se guarda con "Guardar igual"; se sacó la restricción `dorsal_unico_en_el_partido` (migración 0033); la planilla marca "Repetido"; al anotar un gol se elige por nombre. **C2:** `Convocado.ci_verificado` (migración 0033): el CI de cada jugador (interno, nunca público) con "CI ✓" por partido, "Verificar todos los CI" y "12 de 14 CI ✓"; verificar en un partido marca también `Jugador.verificado`; no bloquea nada. **C3:** la foto desde la planilla tiene "Sacar foto" (`capture="environment"`) y "Elegir de la galería", mantiene la autorización (P66) y vuelve a la planilla, al equipo y al jugador.
  - También: los campos de fecha mandaban "29/10/2026" a un `<input type="date">`, que lo ignora (el valor inicial no se veía): ahora van como 2026-10-29, en todos los formularios.
- 2026-10-14: A4 afinado tras la prueba lenta. Con solo la penalización, el solver a veces mandaba un F7 al jueves (no llegaba al óptimo en el tiempo dado). Ahora es determinista: si "¿Entra todo?" dice que un grupo de canchas entra en el horario normal (C1 y C2), sus categorías no pueden usar el tiempo agregado (`PartidoAProgramar.sin_extra`); las del grupo que no entra (C3) sí, con la penalización. Si todo entra, no se restringe nada. Se probaron y descartaron dos variantes en dos fases (sin y con tiempo agregado): con el tiempo repartido, la primera no ubicaba todo C1 y C2, o quedaban F11 sin lugar. Demo con jueves: 223 de 223 y los jueves solo con F11. También: los tests deben correr de a uno por base (dos corridas a la vez sobre `test_rondo` se rompen entre sí).
- 2026-10-15: respuestas del organizador (convocatoria 2026 y audio) y P88 y P89 pasadas a `docs/PREGUNTAS_JMP_CUP_2026.md` (Parte 5, y la columna de respuesta de P24, P30, P68 y P77). Fase 13 planificada con `planning-and-task-breakdown` a partir de `docs/PENDIENTES_PRODUCCION.md` (T13.1 a T13.31 en `tasks/todo.md`).
- 2026-10-15: bloque A de la fase 13. T13.1 y T13.2: escudo por equipo del club (`EquipoDeClub`, migraciones 0034 a 0036 que copian el escudo antes de quitarlo), pendiente "N equipos sin escudo" y su lista. T13.3: borrar club y equipo, y corregir uno mal cargado. T13.4: retirar un equipo (P87 por defecto, migración 0037). T13.5: roles Organización y Mesa (P85), con una matriz de permisos que recorre todas las rutas. Revisión de cierre de las fases 11, 12 y del bloque A: `wo()` ya no pisa un partido empezado.

## Pendiente

- [ ] T0.1 a T0.7 (fase 0) y T1.1 a T1.5 (fase 1).
- [ ] Para la fase 0: facturación activa en la cuenta de Google Cloud de Sebastian, y el proyecto `rondo-jmp` en Neon (región São Paulo, sin las integraciones de GitHub ni de Vercel).
- [ ] Mandar al organizador las preguntas P33 a P51.

## Decisiones

| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-10-15 | Fase 13 en cuatro bloques: A (modelo y roles, antes de cargar datos reales), B (fallos, primero lo del fixture), C (funciones para durante el torneo) y D (diseño y textos) | Pedido de Sebastian. Si no está lista para el 24/10, la organización vuelve a Copa Fácil (P77) |
| 2026-10-15 | El escudo va por equipo del club (club + nombre, modelo `EquipoDeClub`), no por club ni por cada categoría | P68 (2026-10-14) y P89: el nombre identifica al equipo en todas sus categorías. Así el escudo se sube una sola vez |
| 2026-10-15 | Se separan los roles Organización y Mesa de control. Reemplaza la decisión de P64 (todos como Organización) | P85 (audio): dos permisos, organizadores y quienes suben listas y cargan resultados |
| 2026-10-15 | El partido olvidado no se cierra solo: la regla de cierre tiene "Nunca", por defecto | P82: "no se cierra sola" |
| 2026-10-15 | Alta rápida en la cancha hasta el inicio del 2.º tiempo | P84: así lo dice el reglamento |
| 2026-10-15 | Dos equipos del mismo club (P24): no se implementa hasta la respuesta a P90. Por defecto, "como mucho se cruzan en la final" (con 6 y 7, en series distintas; con 8 o más, en la misma serie), y con un solo grupo siguen en la fecha 1 | Corrección de Sebastian: "misma serie en cruzadas" los hace cruzarse en la semi 1.º A vs 2.º A. No se pueden evitar a la vez el cruce en grupos y en semis |
| 2026-10-15 | Para que entre F11 no se usan jueves: se amplía el horario de la cancha 3 el fin de semana. Los jueves quedan para suspensiones | P79 y la convocatoria 2026 |
| 2026-10-15 | Una categoría con 2 equipos no se abre. Con 3 sigue ida y vuelta hasta que confirmen el triangular | P86c |
| 2026-10-13 | P64 (un solo rol): todos los usuarios como Organización, sin fusionar los roles en el código | Es reversible y no toca permisos: cuando se separen los roles, alcanza con cambiar el rol de cada persona |
| 2026-10-13 | Las respuestas del organizador (`docs/PREGUNTAS_JMP_CUP_2026.md`) arman la fase 10, primero lo que pesa en el calendario del 21/10 | Muchas cambian reglas o piden funciones nuevas (P60 F11, P56, P35, P13, P64, P27, W.O. al reprogramar, tiempos del partido a mano) |
| 2026-10-12 | El pedido 2026 se arma en tres fases: 7 (bloque A, calendario y listas), 8 (bloque B, reemplazar a Copa Fácil) y 9 (bloque C, durante el torneo). T6.5 y T6.6 pasan a T7.10, T7.4 y T7.5 | `docs/PEDIDO_CLAUDE_CODE.md`. Aprobado por Sebastian el 2026-10-12 |
| 2026-10-12 | Primero T7.10 con T7.4 y T7.5, después pegar listas, después el calendario (T7.1 a T7.3), y al final T7.11 y T7.12 | El torneo real se crea en producción ya con la configuración 2026; las listas cierran el 21/10 a las 12:00 y esa tarde se arma el calendario definitivo |
| 2026-10-12 | Las imágenes de R2 se sirven desde la app (mismo origen): el bucket sigue privado y sin CORS | Así `modern-screenshot` lee las imágenes para el PNG sin contaminar el canvas |
| 2026-10-12 | Desde ahora Claude desarrolla sin pedir el visto bueno de cada plan o fase; deja todo anotado y pregunta solo dudas concretas | Autorizado por Sebastian. Los límites de SPEC.md siguen valiendo |
| 2026-10-12 | Mientras no esté la cuenta de Cloudflare, las imágenes van al disco local en desarrollo y tests, y la subida se prueba ahí | Sebastian crea la cuenta más adelante; la app tiene que funcionar sin ella |
| 2026-10-12 | PNG 2026: fuente Cinzel, unas 10 filas por imagen; si un día tiene más partidos en una cancha, se parte en "1/2" y "2/2". El lugar de los escudos lo define el diseño de UI. Es de prioridad baja | Diseño en `docs/diseno-fixture-2026/DISENO_FIXTURE_2026.md`; imágenes en `src/torneo/static/png/` |
| 2026-10-12 | Las imágenes fijas del diseño del PNG (fondo, copa y adornos) van en el repo, en `src/torneo/static/png/`. Escudos, fotos, logo del organizador y patrocinadores van a Cloudflare R2, subidos desde la app | Las primeras son parte del diseño y cambian solo con el código; las otras cambian cada año y las carga la organización |
| 2026-10-06 | Django 6.1 + HTMX, un solo servicio. El núcleo de dominio va en Python puro y tipado | El solver (OR-Tools CP-SAT) es nativo de Python: un backend en Python evita un segundo servicio solo para el solver. Las pantallas son formularios, tablas y un calendario para pocos usuarios, y eso no necesita una SPA; el contexto lo dice. Django trae login, admin, formularios y migraciones. Que Sebastian quiera practicar Python no fue un criterio |
| 2026-10-06 | Cloud Run y Neon, los dos en São Paulo | CPU real para el solver (2 vCPU) y requests de hasta 60 minutos, dentro de la capa gratuita. Pide tarjeta |
| 2026-10-06 | La prueba de 6.4 se separa por tipo de choque: personas 2, canchas 3 y compatibilidad 0 (con las canchas de 2023) | Ver H1, H2 y H3 |
| 2026-10-06 | La app se usa en el torneo 2026 | Suma la fase 6 (producción) después de la demo, con backups, usuarios y separación entre demo y producción |
| 2026-10-06 | Es una app web instalable en el celular (PWA). Funciona solo con conexión | Hay buena señal en la cancha, según Sebastian. Así los datos personales no quedan guardados en los teléfonos |
| 2026-10-06 | Todo va en cuentas de Sebastian: un proyecto dedicado en Google Cloud, con su tarjeta, y un proyecto en Neon. Se traspasan a JMP si compra la app | La idea es venderle la app a JMP; así el traspaso no obliga a volver a desplegar |
| 2026-10-06 | No se usa la configuración de Neon para Node (`neon link`, `neon.ts`, `neon deploy`) ni su MCP | La app es Python en Cloud Run: de Neon solo hace falta la cadena de conexión |
| 2026-10-06 | Sin crédito de prueba de Google Cloud. El tope de gasto aceptado es de unos 5 USD al mes | Sebastian ya usó Google Cloud. La capa gratuita vale igual para las cuentas pagas |
| 2026-10-06 | Tailwind CSS v4 en lugar de Pico CSS | Que la interfaz se vea bien es una prioridad, y Tailwind da control total del diseño, incluido el que pase el organizador (P32). Se compila sin Node |
| 2026-10-06 | Tailwind se compila con `django-tailwind-cli`, que descarga el ejecutable oficial (sin Node). El CSS generado no entra al repo: se compila en local y en el Docker | Aprobado por Sebastian |
| 2026-10-07 | Las imágenes (logo, patrocinadores y escudos) y el PNG definitivo quedan para después | Prioridad de Sebastian: avanzar con las pantallas |
| 2026-10-07 | Sin barra de avance en Inicio (configurado, inscripción, etc.); se quedan los pendientes | No le gustó a Sebastian |
| 2026-10-07 | Antes de la inscripción va una fase de pantallas propias (1b) que reemplaza al admin | La interfaz es una prioridad, y la inscripción se construye sobre esas pantallas |
| 2026-10-07 | La página pública entra en la demo, en una versión simple: partidos por día, posiciones y equipos, sin login y sin datos personales (P53) | Sebastian quiere que familias y clubes la vean como en Copa Fácil |
| 2026-10-07 | Interfaz con la identidad de la JMP CUP (azul marino y dorado), listas en lugar de tarjetas y contrato de diseño en `docs/DISENO.md` | El prototipo 1 se rechazó por feo, por tener demasiadas tarjetas y por usar un verde inventado |
| 2026-10-07 | El logo del organizador queda para la fase 5, con el diseño del PNG (P32) | El disco de Render gratis se borra en cada reinicio: una imagen subida se perdería. Hay que guardarla en la base o en un almacenamiento externo |
| 2026-10-07 | El organizador se crea como superusuario (`crear_usuario --admin`) | Un staff sin permisos no ve nada en el admin. Los roles finos (mesa sin staff) quedan para antes de la fase 6 |
| 2026-10-07 | `cargar_config` no corre al arrancar el contenedor: se corre a mano | Cada arranque pisaría lo que se edite en el admin |
| 2026-10-07 | Render gratis sirve para la demo. El programador real usa varios workers de CP-SAT. Antes de la fase 6 se revisa si hace falta más CPU | Medición T0.6 (H6) |
| 2026-10-07 | Claude hace `push` por HTTPS con las credenciales de `gh`, configurado solo en este repo | La clave SSH de Sebastian tiene contraseña, y así Claude puede trabajar solo sin pedirla |
| 2026-10-07 | Claude fusiona los PR con `gh` sin preguntar, si pasan los tests | Autorizado por Sebastian, para no frenar el avance |
| 2026-10-07 | Los PR se fusionan con merge commit, no con squash | Los PR van encadenados; con squash, el siguiente choca con las líneas que tocaron los dos |
| 2026-10-07 | El proyecto de Google Cloud `rondo-jmp` queda sin organización | Para traspasarlo a JMP alcanza con agregarlos como dueños y cambiar la facturación |
| 2026-10-07 | La demo va en Render (gratis, Virginia), y la base se rehace en Neon N. Virginia | La cuenta de facturación de Google Cloud quedó cerrada y bloqueada por un cobro rechazado de la tarjeta, y reabrirla requiere soporte. Render no pide tarjeta. La app y la base van en la misma región. Cloud Run sigue como destino cuando la cuenta esté en regla: es la misma imagen Docker |
| 2026-10-07 | Las migraciones corren al arrancar el contenedor, no como un Job aparte | Hay una sola instancia, y el plan gratuito de Render no tiene comando previo al deploy |
| 2026-10-07 | Seguir con todas las fases sin esperar el visto bueno de Sebastian entre fases, con las dudas en `docs/REVISAR.md` y supuestos mientras tanto | Pedido de Sebastian, solo por esta vez. Los límites de SPEC.md siguen valiendo |
| 2026-10-07 | Los tokens viven en `@theme` de Tailwind y el modo oscuro sigue al sistema. Las pestañas son enlaces, y la hoja inferior es un `<dialog>` | La URL refleja la pestaña, y `<dialog>` da el foco y el Esc sin código |
| 2026-10-07 | Los colores del organizador se conectan a los tokens en TU.7 | Hoy el color guardado por defecto es el verde rechazado |
| 2026-10-07 | Los roles son grupos de Django con permisos propios de Torneo (configurar, programar, inscribir y verificar). Solo el superusuario es staff y entra al admin | La organización y la mesa usan las pantallas propias. Reemplaza la decisión de crear al organizador como superusuario. Los usuarios que ya existían sin grupo pasaron a Organización |
| 2026-10-06 | Una instalación por cliente: si otra organización compra la app, tiene su propio proyecto en Google Cloud y en Neon, con su facturación y el mismo código. La base no separa clientes | Por ahora el único cliente es JMP. Así el modelo de datos queda simple y cada cliente queda aislado. Nada propio de JMP va en el código: nombre, logo y colores van en la configuración |

## Hallazgos

### H1. La prueba de 6.4 da "exactamente 2 choques" solo con tres condiciones

Con los profes de 6.4, el verificador encuentra los dos choques esperados de River Plate. Pero eso se cumple solo si:

1. **Se cuenta un choque por par de partidos**, no por persona. El del sábado (Sub 11 Av A a las 9:20 en C1 contra Sub 15 a las 10:00 en C3) involucra a dos profes. Contados por persona, serían 3 choques.
2. **"Seguidos" (P18) significa turnos consecutivos.** El domingo, River Plate tiene Sub 6 A a las 9:20 en C1A y Sub 8 Av a las 10:30 en C2: 35 minutos entre el final de uno y el inicio del otro, en canchas distintas. Si "seguidos" significara "sin un turno libre en medio", habría un tercer choque.
3. **La prueba mira solo personas (profes y jugadores).** El verificador completo encuentra además los choques de H2 y H3.

Los jugadores compartidos no agregan choques: los dos de River Plate (Sub 6 y Sub 7) caen en el mismo par de partidos que el profe del domingo.

### H2. El calendario 2023 tiene 3 choques de cancha

Con las duraciones de 4.4 y la regla de que C1 entera ocupa sus dos mitades:

- **Domingo, C1:** Sub 9 Av ocupa la cancha entera de 8:40 a 9:30 (turno), pero en C1A y C1B empiezan dos partidos de Sub 6 A a las 9:20. Son 10 minutos de solape en cada mitad.
- **Domingo, C3:** Sub 15 ocupa la cancha de 8:00 a 9:10 (turno de 70), pero Sub 12 A empieza a las 8:50. Son 20 minutos de solape. El sábado, Sub 15 sí tuvo sus 70 minutos.

O son errores del calendario hecho a mano, que es justo el problema que la app tiene que resolver, o en 2023 las duraciones eran otras. Sirven para la demo.

### H3. La compatibilidad de canchas de 2026 no vale para 2023

En 2023, Sub 10 Avanzado jugó dos partidos en C2. Con la configuración 2026 (F8 solo en C1), el verificador los marca. La prueba con datos de 2023 tiene que usar las canchas de 2023 (tabla 6.1).

### H4. La eliminación no entra en el último fin de semana

**Escenario supuesto:** los equipos de 2023, más Sub 14 Av (5 equipos), Sub 17 Av (4), Sub 15 Femenino (4) y un Inicial de 4 equipos en Sub 12, 13, 14, 15 y 17. En total son 117 equipos y 281 partidos.

| Canchas | Ocupación en todo el torneo | Eliminación | Disponible el último fin de semana |
|---|---|---|---|
| C1 + C2 (F7, F8 y mitades) | 162 h de 200 (81 %) | 55 h | 40 h |
| C3 (F11) | 76 h de 100 (76 %) | 21 h | 20 h |

En todo el torneo entra, pero muy justo. La eliminación no cabe en un solo fin de semana. Con el tamaño de 2023, la eliminación ya ocupa el 88 % de C1 + C2 del último fin de semana, antes de sumar las restricciones de profes y descansos. Hacen falta P13 (¿se parten C2 y C3?) y P33.

### H5. El desempate "solo entre ellos" no funciona en las series cruzadas

Con 6 y 7 equipos, los de una misma serie nunca se enfrentan. Entonces no hay "partidos entre ellos" y cualquier empate va directo a sorteo. Lo mismo pasa al comparar equipos de series distintas (mejor 3.º, mejor perdedor). No afecta a la demo, porque no hay resultados, pero la regla queda incompleta (P34).

### H6. El solver alcanza en Render para la demo, pero no sobra para 2026

Se usó un modelo CP-SAT sintético con la forma del real (T0.6): canchas con mitades, un turno libre entre partidos del mismo equipo, profes compartidos y franjas reales. Solo fase de grupos, con los formatos de 4.5. Se midió en Docker con `--cpus=0.1 --memory=512m`, lo mismo que da Render gratis.

| Instancia | CPU | Workers | Primer calendario válido | Memoria pico |
|---|---|---|---|---|
| Tamaño 2023: 84 equipos, 139 partidos, 4 fines de semana | 0,1 | 1 | 0,4 s | 91 MB |
| La misma, con 3 fines de semana o 36 profes compartidos | 0,1 | 1 | 0,4 a 0,5 s | 94 a 97 MB |
| Estimación 2026: 117 equipos, 191 partidos, 5 fines de semana | 0,1 | 1 | 0,7 s | 73 MB |
| Estimación 2026, en 4 fines de semana | completa | 1 | no encontró en 60 s | — |
| Estimación 2026, en 4 fines de semana | completa | 8 | 2,0 s | — |
| Estimación 2026, en 4 fines de semana | 0,1 | 8 | 94 s | 117 MB |

- **Para la demo, Render gratis alcanza de sobra.** La memoria nunca pasa de 120 MB.
- **El problema justo (2026 en 4 fines de semana) depende más de la estrategia que de la CPU:** con un solo worker no encuentra solución ni con CPU completa, y con 8 sí. El programador real va a usar varios workers, y además una solución inicial armada a mano como pista (*hint*) o una resolución por fin de semana.
- **Para el torneo real de 2026, 0,1 CPU queda corto** si hay que reprogramar rápido con el calendario lleno. Antes de la fase 6 hay que decidir entre Render Starter (0,5 CPU, de pago) y Cloud Run, si la cuenta queda en regla.
- La imagen pesa 1 GB, por OR-Tools, pandas y numpy. El build de Render tarda más, pero no hay límite que lo impida.

### H7. La programación 2026 entra entera con 1 CPU (T7.12, 2026-10-13)

Plantilla 2026 (del 24/10 al 15/11, eliminación en el 4.º fin de semana, Sub 5 y Sub 6 en F6, sin Bronce) y la demo de 93 equipos: 223 partidos. Contenedor limitado a 1 CPU (`taskset -c 0`, como Render Standard), límite de 120 s. Script descartable fuera del repo: genera la demo, los fixtures, programa y mide.

| | 8 trabajadores | 4 trabajadores |
|---|---|---|
| Partidos ubicados | 223 de 223 | 223 de 223 |
| Estado del solver | FEASIBLE (usa los 120 s) | FEASIBLE (usa los 120 s) |
| Choques duros (verificador) | 0 | 0 |
| Pares de un entrenador compartido el mismo día | 10 | 8 |
| Espera de esos entrenadores: mediana / media / máxima | 10 / 26 / 100 min | 5 / 5 / 5 min |
| Esperas de más de 2 h | 0 | 0 |
| Seguidos en la misma cancha | 4 | 8 |
| Llaves encadenadas el mismo día / sin descanso | 21 / 0 | 22 / 0 |

Contra la revisión externa (demo con 5 fines de semana, 2 CPU): la espera mediana de los profes pasa de 65 min (98 en el escenario 2026 de la convocatoria) a 5 o 10 min, sin esperas de más de 2 h, y las llaves encadenadas sin descanso pasan de 2 a 0.

- **Asistentes y delegados** (con P57 por defecto no cuentan): con 4 trabajadores, 6 pares quedan con más de 2 h de espera (máxima 305 min). Si la respuesta a P57 es "todo el cuerpo técnico", se cambia la regla y se vuelve a programar.
- **Producción:** `RONDO_PROGRAMADOR_TRABAJADORES=4`. Da el mismo resultado, o mejor, y le deja más aire a la página mientras programa. Durante los 120 s la página responde más lenta: programar fuera del horario de visitas.
- **Margen:** con más equipos que la demo (H4 estimaba 117), puede no entrar todo; entonces vale P33 (semis en el 3.er fin de semana) o P13 (más canchas).

### H8. Con Sub 10 y Sub 11 Avanzado en F11, la cancha 3 no alcanza (T10.4, 2026-10-13)

Plantilla 2026 con las respuestas del organizador (F11 en Sub 10 y Sub 11 Avanzado, último inicio, Sub 5 y Sub 6 sin viernes, sin margen entre canchas) y la demo de 93 equipos (223 partidos). 1 CPU, 4 trabajadores, 120 s.

| Escenario | Ubicados | Lo que no entra |
|---|---|---|
| Fechas 2026 tal cual | 217 de 223 | 6, todos en C3: finales de Sub 10, Sub 12 y Sub 15 Avanzado, y un partido de grupos de Sub 15 |
| Eliminación desde el 3.er fin de semana (P33) | 217 de 223 | 6, todos en C3 |
| **Con tres jueves de 16 a 20 (29/10, 5/11 y 12/11)** | **223 de 223** | Nada. 0 choques; espera de los entrenadores: mediana 5 min, máxima 5; 0 llaves encadenadas sin descanso |

- **Por qué:** la cancha 3 (F11) pide 5.610 minutos y da 4.560 en las fechas 2026. El resto (C1 y C2) usa 5.600 de 9.120.
- **Qué lo destraba:** sumar tiempo en C3. Los jueves (la convocatoria ya los propone para reprogramar) alcanzan; también podría servir empezar antes o terminar después los sábados y domingos. Es la pregunta P79.
- Los tests lentos agregan esos tres jueves (fixture `agregar_jueves`) y siguen exigiendo que entre todo.

## Comentarios de Sebastian sobre la demo (2026-10-07)

- **PNG:** técnicamente funciona, pero no es el diseño que se quiere. Sebastian va a pasar el diseño de calendario de este año (P32).
- **Interfaz:** fea y poco intuitiva. El admin de Django ("Configuración") no sirve como pantalla del organizador: muestra reglas en JSON, "Usuarios" y "Grupos" sin explicar, y el "Organizador" se confunde con quién organiza. **Hacen falta pantallas propias**, con interruptores y números en lugar de JSON, y un flujo guiado: crear torneo → equipos → fixture → calendario. El admin queda solo como herramienta técnica.
- **Roles:** no está claro quién puede hacer qué. Hay que definir qué hace la organización y qué la mesa de control.
- **Imágenes:** el logo, los escudos de los equipos y quizá fotos de jugadores necesitan un almacenamiento persistente (un bucket). Las fotos de jugadores son datos de menores y no están en el contexto: hay que confirmar si hacen falta (P52).
- **Roles acordados:** Organización puede hacer todo. Mesa de control puede cargar equipos y listas, verificar jugadores y ver o exportar el calendario.
- **Prototipo de interfaz** al estilo de Copa Fácil, con mejoras (asistente para crear el torneo, reglas con interruptores, avisos al cargar listas, capacidad, propuestas de reprogramación): https://claude.ai/artifact/VacxSHvhh36heQY2xS8Q3a. Copia en `docs/prototipo/prototipo-rondo.html`. Pendiente: los comentarios de Sebastian.
- **Diseño del PNG (2026-10-07):** el organizador usa el de 2025, con una imagen por cancha y por día: fondo azul marino, filas amarillas (categoría, escudo, equipo, equipo, escudo, hora), panel dorado con "CANCHA N", la copa y "JMP CUP · N.ª EDICIÓN", y una franja de patrocinadores abajo. Réplica: https://claude.ai/artifact/H9uyeRSzhDwFj7CbfEMSKv (copia en `docs/prototipo/fixture-png.html`). Faltan las imágenes reales: copa o logo, escudos y patrocinadores.
- **Identidad visual:** azul marino y dorado, los colores de la JMP CUP. El prototipo verde no los respetaba.
- **Página pública (cambio de alcance):** Sebastian quiere que quienes entran a mirar (familias y clubes) vean algo como la página de Copa Fácil (https://copafacil.com/-78bk8). El contexto la dejaba para después de la demo (P53).

## Revisión de la fase 0 (2026-10-07, `code-review-and-quality`)

**Veredicto: aprobada.** El código es chico y sigue la spec. Quedan pendientes la prueba del PNG en Android y el visto bueno de Sebastian.

**Corregido en la revisión:**

- **Hook:** ningún test verificaba que `.env.example` pasara. Una mutación que lo bloqueaba seguía en verde, así que se agregó ese test.
- **Settings:** sin `DATABASE_URL`, el error era confuso (`Scheme '://' is unknown`). Ahora dice "Falta la variable de entorno DATABASE_URL", con su test.
- **Mutación comprobada:** quitar el `strip()` del login la detectan los tests.

**Pendiente para fases siguientes:**

- **Datos personales en los logs (fase 2, obligatorio):** los errores de Postgres incluyen los valores. Una violación de unicidad del CI dejaría el número en el log ("Key (ci)=(…) already exists"). Los duplicados de CI se validan antes de guardar, y se agrega un filtro de logs que no deje pasar el texto de errores de la base.
- **Roles (antes de la fase 6):** `crear_usuario` hace staff a todos, y con eso la mesa de control podría editar la configuración en el admin. Hace falta un usuario de mesa sin staff.
- **FYI:** `django-tailwind-cli` descarga el ejecutable oficial de Tailwind desde GitHub durante el build, y nosotros no verificamos su checksum. La imagen pesa 1 GB, por OR-Tools, pandas y numpy.

## Revisión de la fase 1 (2026-10-07, `code-review-and-quality`)

**Veredicto: aprobada.** Falta el visto bueno de Sebastian.

**Mutaciones:** se rompieron a propósito cuatro piezas clave para ver si los tests lo detectan.

| Mutación | Resultado |
|---|---|
| `cargar_config` borra también las franjas de entre semana | Detectada |
| La compatibilidad ignora la regla por categoría | Detectada (3 tests) |
| `Torneo.save()` guarda sin validar las reglas | Detectada |
| El Organizador no fija `pk=1` | **No la detectaba ningún test.** Se agregó uno: guardar otro organizador reemplaza al único |

**FYI:**

- `cargar_config` no borra categorías ni canchas que se saquen del JSON, porque podrían tener equipos. Si hace falta, se borran en el admin.
- El procesador de contexto hace una consulta por página para traer al Organizador. Es despreciable con 2 o 3 usuarios.

## Revisión de la fase 1b (2026-10-07, `code-review-and-quality`)

**Veredicto: aprobada, después de corregir 5 hallazgos.** El visto bueno de Sebastian queda para su vuelta (REVISAR.md).

**Hallazgos, comprobados con un experimento antes de corregirlos:**

| Hallazgo | Corrección |
|---|---|
| Con HTMX, al volver con el navegador a una página que HTMX no tenía guardada, la app devolvía solo el fragmento y la página quedaba rota | `views/fragmentos.pide_fragmento()`: en una restauración del historial se devuelve la página entera (Torneo y página pública) |
| El asistente validaba que el torneo no existiera solo en el paso 1. Si alguien lo cargaba desde la terminal mientras tanto, al terminar se pisaba | Se vuelve a comprobar antes de crear, con un error que explica qué hacer |
| "Más" hacía una consulta por persona para saber su rol (21 consultas con 12 personas) | `nombre_del_rol` usa `groups.all()`, que aprovecha el `prefetch_related` |
| Con la sesión iniciada, `/cuentas/login/` se veía en blanco | El login lleva al inicio (`redirect_authenticated_user`) |
| **Consider:** el 404 era el de Django, sin diseño, justo en la página pública | `404.html` con el estado vacío y un enlace al inicio |

Cada uno tiene su test en `tests/torneo/test_revision_1b.py`.

**Mutaciones:** se rompieron a propósito cuatro piezas clave; todas las detectaron los tests:

| Mutación | Resultado |
|---|---|
| La página pública no filtra por `publico` | Detectada |
| El superusuario no cuenta como Organización | Detectada |
| El contraste mínimo del color principal baja de 4,5 a 1,5 | Detectada |
| El asistente deja la compatibilidad de una categoría destildada | Detectada (la valida el dominio) |

**FYI:**

- `frontend/tailwind.css` tiene 905 líneas. Si pasa de unas 1.000, conviene partirlo por componente con `@import`.
- El formulario de reglas acepta tuplas como valor inicial (Django las trata como listas): se probó y no es un problema.
- Las capturas de cada pantalla se hicieron con Firefox, a 360 y 1024 px, en claro y en oscuro. No se probó en un celular real (R1).

## Revisión de la fase 2 (2026-10-07, `code-review-and-quality`)

**Veredicto: aprobada, después de corregir 2 hallazgos.** El visto bueno de Sebastian queda para su vuelta (REVISAR.md).

| Hallazgo | Corrección |
|---|---|
| **Seguridad:** la ficha del equipo (nombres y CI de menores) se abría con cualquier sesión, aunque el usuario no tuviera rol | Pide `inscribir_equipos` (organización y mesa) |
| La guarda de `generar_demo` miraba personas de torneos reales, algo que ya cubría la de equipos (la mutación sobrevivía), y no veía a las personas sin equipo, que pueden ser datos reales a medio cargar | Se niega si hay una persona que no está en un equipo de demo |

Cada uno tiene su test en `tests/torneo/test_revision_2.py`.

**Mutaciones** (antes de corregir):

| Mutación | Resultado |
|---|---|
| INS-05 deja jugar en otro club | Detectada |
| El filtro de logs no oculta nada | Detectada |
| El formulario de profes deja de ser sensible | Detectada |
| El servicio no busca a la persona por su CI | Detectada |
| La guarda de la demo no mira personas | **No detectada:** era redundante; ver la segunda corrección |

**FYI:**

- Quien carga listas puede saber si un CI ya está cargado y a nombre de quién (el aviso lo dice). Son 2 o 3 personas de confianza, y es justo lo que pide INS-05.
- `generar_demo` vuelve a cargar la configuración 2026 en cada corrida: pisa lo que se haya editado en el torneo de demo.
- La imagen de producción no tiene `faker` (`uv sync --no-dev`): `generar_demo` se corre desde la máquina de Sebastian (DESPLIEGUE.md, 3c).

## Revisión de la fase 3 (2026-10-07, `code-review-and-quality`)

**Veredicto: aprobada.** El visto bueno de Sebastian queda para su vuelta (REVISAR.md).

**Mutaciones:**

| Mutación | Resultado |
|---|---|
| Sin la fecha 1 para el mismo club (P24) | Detectada |
| La franja mira el turno (con el cambio) en lugar del partido (P48) | Detectada |
| Una mitad cuenta como cancha entera en la capacidad | Detectada |
| Se rehace un fixture con partidos jugados (FIX-09) | Detectada |
| El sorteo deja de separar clubes (P45) | Detectada |
| Dos equipos que comparten profe y juegan entre sí cuentan como choque | **No detectada:** el código estaba bien, pero ningún test lo cubría. Se agregó |

**Corregido:** el fixture hacía dos consultas por serie (un `order_by` dentro del bucle que ignoraba el `prefetch_related`). Test en `tests/torneo/test_revision_3.py`.

**FYI:**

- Con la demo (93 equipos), la eliminación entra justo en el último fin de semana: 37 de 40 h en C1 y C2 y 18 de 20 h en C3. Con los 117 equipos de H4 no entraría: P33 sigue siendo importante.
- La capacidad es una cota optimista (R39). El programador de la fase 4 es el que dice qué entra de verdad.
- Si mypy no ve una relación inversa nueva (`categoria.partidos`), es su caché incremental: `rm -rf .mypy_cache`.

## Revisión de la fase 4 (2026-10-07, `code-review-and-quality`)

**Veredicto: aprobada.** El visto bueno de Sebastian queda para su vuelta (REVISAR.md).

**Resultado:** la demo (93 equipos, 223 partidos) se programa entera, con solución óptima y 0 choques según el verificador, en unos 30 s en local con 8 trabajadores (`pytest -m lento`).

**Mutaciones:** las 6 las detectaron los tests:

| Mutación | Resultado |
|---|---|
| Sin el turno libre del equipo en el día (P17) | Detectada |
| El profe compartido sin margen (P35) | Detectada |
| La eliminación puede ir antes de los grupos | Detectada |
| El servicio guarda encima de jugados y fijados | Detectada |
| Una final sin sus semis igual se ubica | Detectada |
| C1 entera no ocupa sus mitades | Detectada |

**Corregido:** al armar el problema se consultaban las canchas de la categoría por cada partido (20 consultas con 14 partidos, 50 con 42). Ahora salen todas de una vez. Test en `tests/torneo/test_revision_4.py`.

**FYI:**

- En Render gratis (0,1 CPU), el solver va a tardar mucho más que en local (H6, R44). Para mostrarle la demo al organizador, conviene programar antes.
- Si se rehace el fixture de una categoría, sus partidos pierden el horario y hay que volver a programar.

## Revisión de la fase 5 (2026-10-08, `code-review-and-quality`)

**Veredicto: aprobada.** El visto bueno de Sebastian queda para su vuelta (REVISAR.md).

**Resultado de punta a punta** (test lento): demo de 93 equipos → fixtures → 223 de 223 partidos programados sin choques → bloqueo de la ACF → 2 o 3 propuestas → aplicar sin choques → PNG del día sin datos personales.

**Mutaciones:**

| Mutación | Resultado |
|---|---|
| Las propuestas pueden repetir el mismo conjunto de movidos | Detectada |
| Las propuestas pueden mover partidos antes de la ventana | **No detectada** al principio: el objetivo y el máximo por día ya lo evitaban en los tests. Se agregó un caso mínimo que la detecta |
| Se aplica una propuesta vieja (calendario cambiado) | Detectada |
| El cambio manual no pasa por el verificador | Detectada |
| Suspender no marca el día | Detectada |
| El programador usa días suspendidos | Detectada |

**Corregido:** `calcular_propuestas` le daba a cada una de sus 3 resoluciones el límite entero de `PROGRAMADOR_SEGUNDOS`: podía tardar el triple, cerca del corte de gunicorn (300 s). Ahora lo reparte. Test en `tests/torneo/test_revision_5.py`.

**FYI:**

- Al aplicar una propuesta, las otras de la misma corrida quedan viejas (la firma cambió) y se rechazan. Es lo esperado.
- Si se suspende un día y no se aplica ninguna propuesta, sus partidos quedan sin programar hasta volver a programar o aplicar una.
- La prueba del PNG en Android sigue pendiente (R45).

## Revisión de seguridad (2026-10-08, T6.3, `security-and-hardening`)

**Modelo de amenazas:** los límites de confianza son los formularios, las páginas públicas, la PWA y el admin. El activo principal son los datos personales de menores. Con STRIDE: suplantación (fuerza bruta en el login), divulgación (páginas públicas, logs y errores), elevación (permisos por vista) y negación de servicio (el programador, ya acotado por tiempo y por una corrida a la vez).

**Hallazgos, comprobados con un experimento y corregidos, cada uno con su test (`tests/torneo/test_seguridad.py`):**

| Hallazgo | Corrección |
|---|---|
| La recuperación de contraseña por correo estaba abierta sin login, sin correo configurado | Se sacaron esas rutas; quedan login, logout y cambio de contraseña |
| No había CSP ni Permissions-Policy | CSP de Django 6.1 (`SECURE_CSP`): solo scripts propios, sin `unsafe-inline` en scripts. `Permissions-Policy` apaga cámara, micrófono, ubicación y pagos |
| El login aceptaba intentos fallidos sin límite | 10 intentos por IP y por usuario cada 15 minutos; después, 429 con un aviso, aunque la contraseña sea correcta |
| Sin página 500 propia | `500.html` que no depende de la base ni de la sesión |

**Comprobado sin cambios:** toda URL pide login salvo las públicas y la PWA (un test las recorre todas); las de la organización dan 403 a la mesa; `check --deploy` sin advertencias; `pip-audit` sobre el lockfile, sin vulnerabilidades conocidas; HSTS, cookies seguras, `X-Frame-Options: DENY`, `nosniff` y `Referrer-Policy: same-origin`.

## Revisión de la fase 6, parte A (2026-10-08, `code-review-and-quality`)

**Veredicto: aprobada.** La revisión de seguridad está arriba ("Revisión de seguridad").

| Mutación | Resultado |
|---|---|
| Se puede asignar el mismo equipo a los dos lados de un cruce | Detectada |
| Alguien puede cambiarse el rol propio | Detectada |
| El login sin límite de intentos | Detectada |
| Anonimizar toca a quien está en otro torneo | Detectada |
| Sin CSP | Detectada |

## Revisión de la fase 7 (2026-10-13, `code-review-and-quality`)

**Veredicto: aprobada.** Diff de `main` a `fase-7/medicion`: 42 archivos de código, unas 1.400 líneas, con sus tests (716 rápidos y los 2 lentos en verde; mypy y ruff limpios).

| Mutación (se invierte una condición nueva y se corre su test) | Resultado |
|---|---|
| La llave que toma posiciones no descansa después de los grupos | Detectada |
| El margen de P35 también en la misma cancha | Detectada |
| El verificador ignora los equipos virtuales | Detectada |
| El modelo ignora los equipos virtuales | Detectada |
| Sin el objetivo de la espera de los profes | Detectada |
| La regla de Bronce no marca el fixture como desactualizado | Detectada |
| Toda lista se lee en mm/dd | Detectada |
| P57 cuenta a todo el cuerpo técnico | Detectada |
| "Fecha incompleta" al revés | Detectada |
| La vista previa de pegar guarda de verdad | Detectada |

- **Seguridad:** pegar lista pide el permiso de cargar listas, usa CSRF, limita a 60 filas, el formulario es sensible y nada va a la sesión ni al log (con test). Todo lo que llega del formulario pasa por el mismo servicio que la carga a mano.
- **FYI:** dos imágenes del diseño (`copa_marca_de_agua.png` y `logo_jmp_cup.png`) entraron en el commit de T7.5 por un `git add src`. No tienen datos personales; se acomodan en T8.12. Desde ahora se agregan rutas concretas, nunca carpetas enteras.
- **Consider (anotado, sin cambio):** P47 no suma los partidos de grupos del día a los de las llaves encadenadas. Con la eliminación en su propio fin de semana no pasa; si P33 adelanta semis, hay que revisarlo.
- **Nit:** los nombres de los días están en `dominio/config.py` (opciones de la regla) y en `servicios/asistente.py`. Se dejan: son dos capas distintas.

## Revisión de la fase 8 (2026-10-13, `code-review-and-quality` y `security-and-hardening`)

**Veredicto: aprobada, con una corrección de seguridad.** Verde con los lentos (858 rápidos y los 2 lentos).

**Modelo de amenazas:** fronteras en la subida de imágenes, la vista que las sirve, los POST de la ficha del partido, patrocinadores y sorteo, y la página pública con caché. Activo principal: fotos y nombres de menores.

| Hallazgo | Corrección |
|---|---|
| **Un aviso de la sesión de alguien de la organización quedaba en la caché pública y se le mostraba a cualquier visitante** (los avisos de Django viajan en una cookie, que no hacía variar la caché) | Las páginas públicas no muestran avisos ni ponen el token CSRF (no tienen formularios), y la caché varía también por cookie. Test: el aviso no sale en lo público, queda para la próxima pantalla interna, y la página pública no pone cookies |

**Comprobado con tests:** un SVG con script no pasa como imagen; un tipo de imagen inventado da 404; la foto sin autorización da 404 afuera; los eventos validan que el jugador sea de ese equipo; el escudo valida el club para la redirección.

| Mutación | Resultado |
|---|---|
| La foto sin autorización se sirve igual | Detectada |
| P34: siempre solo entre ellos | Detectada |
| La multa pagada no evita la suspensión | Detectada |
| Los cruces se proponen con grupos sin terminar | Detectada |
| El gol en contra suma para el que lo hizo | Detectada |
| La foto del plantel público sin mirar la autorización | Detectada |
| Un jugador de otro equipo en un evento | Detectada |

- **FYI:** Django no limita el tamaño de un archivo subido antes de procesarlo (se guarda en un temporal); `procesar_imagen` lee como mucho 8 MB. Solo pueden subir usuarios con sesión.
- **Catálogo:** RES-01 a RES-03 y SUS-01 y SUS-02 en SPEC.md.

## Revisión de la fase 9 (2026-10-13, `code-review-and-quality`)

**Veredicto: aprobada.** Dos tareas chicas, con sus tests.

| Mutación | Resultado |
|---|---|
| Anonimizar no borra los archivos de las fotos | Detectada |
| Los suspendidos de otro día aparecen en la lista | Detectada |

- **Privacidad:** las fotos de las personas anonimizadas salen del almacenamiento después de confirmar la base; si algo falla antes, no se pierde nada.

## Revisión de la fase 10 (2026-10-13, `code-review-and-quality`)

**Veredicto: aprobada.** Verde con los lentos (904 rápidos y los 2 lentos, que agregan los tres jueves de H8).

| Mutación | Resultado |
|---|---|
| El modelo no saca los días sin jugar (P56) | **Sobrevivió** al principio: el solver igual elegía el sábado. Se agregó un test con solo un viernes disponible; ahora se detecta |
| El verificador no marca un día sin jugar | Detectada |
| Último inicio ignorado (P48) | Detectada |
| Sin los objetivos de un partido por día y finales al final | Detectada |
| Unir una cancha con partidos en sus mitades | Detectada |
| Dorsal repetido en el equipo | Detectada |
| El contador de reprogramaciones siempre en 0 | Detectada |

- **Consider (anotado):** la capacidad que se muestra antes de programar sigue contando hasta el fin de la franja, aunque la regla sea "último inicio": queda conservadora.
- **Consider:** juntar a los equipos de un mismo club el mismo día (preferencia de la respuesta 1.4.8) no está.
- **Para Sebastian:** P44 (inscribir un equipo durante las primeras fechas choca con FIX-09), P75 (la galería de fotos de partidos, que el pedido había descartado), P78 y P79 (plantel de F11 en Sub 10 y Sub 11; cómo dar más tiempo a la cancha 3), y si se saca "fijar a mano" al mover un partido ("no existen partidos fijados a mano").

## Revisión de las fases 11 y 12 y del bloque A de la fase 13 (2026-10-15, `code-review-and-quality`)

Antes del checkpoint A, porque todo eso va a producción. Unas 5.600 líneas en `src` desde el PR #118. Se miró a fondo lo que se usa en la cancha (ficha del partido, planilla, alta rápida, W.O.), lo que borra o mueve datos (borrar y retirar equipos, unir clubes, migraciones del escudo), los permisos y lo que sale en la página pública.

- **Corregido:** `wo()` no impedía dar un W.O. a un partido empezado o terminado. La ficha esconde el botón, pero una pestaña vieja o un doble toque lo pisaban (con sus goles). Ahora lo rechaza, con tests.
- **Corregido (Nit):** los números mal escritos en la ficha (minuto, partidos de suspensión) decían "Los penales son números".
- **Corregido (Nit):** "Corregir equipo" aclara que el nombre cambia solo en esa categoría y que, para todas, se usa la pantalla del club.
- **Bien:** la ficha valida que el equipo y el jugador sean del partido en cada acción; la página pública no lee CI, nacimiento, lesiones ni amonestaciones, y la foto sale solo con autorización; las acciones que borran piden "¿Estás seguro?"; las migraciones del escudo copian antes de quitar y tienen un test con `MigrationExecutor`; la matriz de permisos cubre todas las rutas.
- **FYI:** `jugados_de` mira también `no_se_presento`, aunque hoy un W.O. siempre deja el partido como jugado: es redundante a propósito.
- **Para después (no bloquea):** `servicios/reprogramar.py` (629 líneas) y `views/ficha_partido.py` (474) pasan el tamaño sano de un módulo. Partirlos (propuestas por un lado, aplicar y deshacer por otro; acciones de la ficha en un despachador aparte) conviene antes de T13.18, que toca las propuestas.
- **Sin revisar línea por línea:** el modelo del programador (`dominio/programador/modelo.py`, A1 a A4). Lo cubren los tests lentos con el calendario 2026 (223 de 223).

## Supuestos

Valores que no están en el contexto. Quedan como configuración:

- **Choque:** un par de partidos que no pueden convivir, con la lista de motivos (cancha, equipo, profe, jugador, bloqueo…). Se cuenta uno por par.
- **Compatibilidad:** la regla por categoría tiene prioridad sobre la regla por modalidad. Por ejemplo, Sub 6 es F7, pero juega en C1A o C1B.
- **CI:** para comparar se usan el número, el complemento y el prefijo "E-". La sigla de departamento se guarda, pero no se compara.
- **Franjas:** el partido tiene que terminar dentro de la franja; el cambio del último partido puede quedar afuera (P48).
- **Tiempo:** se guarda en UTC y se muestra en America/La_Paz (UTC−4, sin horario de verano). El programador trabaja en pasos de 5 minutos.
- **Partidos por día de un equipo:** como máximo 2 (P47).

## Preguntas nuevas para el organizador

| # | Pregunta | Por defecto |
|---|---|---|
| P33 | La eliminación no entra en el último fin de semana (H4). ¿Se pueden adelantar las semis al penúltimo? | Configurable: desde qué fin de semana empieza la eliminación. La app avisa antes de programar si no entra |
| P34 | ¿Cómo se desempata entre equipos que no jugaron entre sí (misma serie en series cruzadas, o mejor 3.º entre series)? | Se usan todos los partidos del grupo, con el mismo orden de criterios |
| P35 | ¿Cuánto tiempo necesita un profe para cambiar de cancha? Esto define "seguidos" en P18 | Al menos 10 minutos entre el final de un partido y el inicio del otro. Así quedan prohibidos los turnos consecutivos en canchas distintas |
| P36 | Jugadores en dos equipos: ¿alcanza con que los partidos no se pisen? | Sí |
| P37 | ¿Alguien puede ser jugador en un equipo y profe en otro (por ejemplo, un Sub 17 que dirige un Sub 6)? | Sí, y esos equipos no juegan a la vez |
| P38 | Bloqueo de la ACF: ¿incluye el traslado? ¿Puede afectar a varios equipos del club? | El organizador carga inicio y fin con el margen que quiera, y un bloqueo puede abarcar varios equipos |
| P39 | ¿Se puede cargar un jugador sin CI? | Sí, con el aviso "documento pendiente". Es obligatorio antes del primer partido |
| P40 | Cuerpo técnico: ¿cuántas personas de cada rol? | Hasta 3 en total, con un solo entrenador, obligatorio antes del primer partido |
| P41 | Sub 15 Femenino: ¿se valida el género? ¿Las chicas pueden jugar en las otras categorías? | No se registra el género; la mesa lo verifica con el documento |
| P42 | Jugar en una categoría mayor (P6): ¿hay un límite de años? | Sin límite, pero la app avisa si son más de 2 años |
| P43 | ¿Los penales de la eliminación necesitan más tiempo en el turno? | No |
| P44 | Un equipo que se inscribe tarde es uno de los problemas del contexto. ¿Se puede rehacer el fixture de una categoría que todavía no empezó? | Sí, mientras no tenga partidos jugados. Se reprograma solo esa categoría |
| P45 | ¿Cómo se arman las series: por sorteo, a mano o separando a los equipos del mismo club? | Sorteo automático que separa a los equipos del mismo club cuando se puede, editable antes de generar el fixture |
| P46 | Todos Santos cae el domingo 1 de noviembre (2.º fin de semana), y el lunes 2 es feriado. ¿Se juega ese fin de semana? ¿Se usa el lunes 2 para reprogramar? | Se juega normal. El lunes 2 se usa solo si se agrega una franja |
| P47 | ¿Cuántos partidos por día puede jugar un equipo como máximo (P17)? | 2 |
| P48 | ¿El último partido tiene que terminar antes del cierre de la franja? | Sí, el partido; el cambio de 5 minutos puede quedar afuera |
| P49 | ¿Cuánto tiempo se guardan los datos de los jugadores después del torneo? | Hasta fin de año; después se anonimizan y quedan los planteles sin nombres ni CI |
| P50 | Resultados y tabla quedan fuera de la demo, pero en 2026 la eliminación necesita saber quién pasa. ¿Cómo se definen los cruces? | El organizador calcula las posiciones como hasta ahora y asigna a mano en la app los participantes de cada partido de eliminación |
| P51 | ¿Cuántas listas se esperan en 2026 y quién las carga? A mano son unos 1.700 jugadores | La organización las carga con el formulario. Si no alcanza el tiempo, se agrega pegar filas copiadas de Excel |
| P52 | ¿Hace falta guardar fotos de los jugadores? Son datos personales de menores | No, hasta que se confirme y se defina quién las ve |
| P53 | ¿La página pública (calendario, fixture y posiciones sin login, como Copa Fácil) entra en la demo o queda para después? | **Respondida por Sebastian:** entra una versión simple, solo de lectura, sin datos personales |
| P54 | Con muchos equipos (por ejemplo, 24 en Sub 15) la categoría se divide en grupos A y B, y los mejores se cruzan después. ¿Desde cuántos equipos se divide, en cuántos grupos y de qué tamaño? ¿Todos contra todos dentro del grupo? ¿Cuántos pasan de cada grupo y cómo sigue (cuartos, semis, final)? | Configurable en `formatos.json`. Mientras no se responda, con más de 10 equipos la app avisa que falta el formato (P27) |
| P78 | Sub 10 y Sub 11 Avanzado juegan F11 (respuesta a P60). ¿El plantel sigue de 12 a 16, como dice la convocatoria, o pasa a 18 a 22 como el resto de F11? | 12 a 16, como la convocatoria |
| P79 | Con F11 en Sub 10 y Sub 11 Avanzado, la cancha 3 no alcanza (H8). ¿Se agregan jueves de 16 a 20, se amplía el horario del sábado y el domingo, o se juega F11 en otra cancha? | **Respondida en parte (2026-10-15):** sin jueves ni otra cancha. Falta cuánto se amplía C3 (Parte 5 de PREGUNTAS) |
| P90 | Dos equipos del mismo club: ¿que no se enfrenten en grupos o que como mucho se crucen en la final? Con un solo grupo, ¿fecha 1 o última? (ejemplos en PREGUNTAS, Parte 5) | Como mucho en la final; con un solo grupo, fecha 1 |
| P87 | Si un equipo se retira con el torneo empezado, ¿sus partidos jugados cuentan? ¿Los que faltan se dan por W.O. o se borran? | Los jugados cuentan; los que faltan, W.O. 3 a 0 para el rival |

## Planes gratuitos (revisados el 2026-10-06)

| Servicio | Límites que importan |
|---|---|
| Neon (Postgres) | 1 GB por proyecto, según la pantalla de alta de Neon (los artículos de 2026 decían 0,5 GB), y 100 CU-hora por proyecto al mes. Se suspende a los 5 minutos sin uso y despierta solo. Tiene región en São Paulo |
| Supabase (Postgres) | 500 MB. El proyecto se pausa a los 7 días sin uso y hay que reactivarlo a mano |
| Render (web) | 512 MB y 0,1 CPU. Se duerme a los 15 minutos y tarda alrededor de 1 minuto en despertar. Su Postgres gratis vence a los 30 días. No tiene región en Sudamérica |
| Koyeb (web) | 512 MB y 0,1 vCPU. Se duerme tras 1 hora sin tráfico y despierta en 1 a 5 segundos. Regiones: Washington o Frankfurt |
| Google Cloud Run | Gratis cada mes: 180 mil vCPU-segundos, 360 mil GB-segundos y 2 millones de requests. Requests de hasta 60 minutos. La CPU se corta al responder, salvo con facturación por instancia. Tiene región en São Paulo. Pide tarjeta, pero solo para verificar la identidad (es una retención temporal). Las cuentas nuevas reciben 300 USD de crédito por 90 días y, al terminar la prueba, no hay cobro automático: si no se activa la cuenta paga, los servicios se apagan |
| Vercel (Hobby) | 300 segundos por función y 2 GB. Solo uso personal no comercial, y JMP cobra inscripciones |

Versiones: OR-Tools 9.15 tiene wheels para Python 3.14 en Linux x86_64. Django 6.1 (agosto de 2026) soporta Python 3.12 a 3.14 y pide PostgreSQL 15 o superior.
