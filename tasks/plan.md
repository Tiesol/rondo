# Plan de implementación: app de la JMP CUP

> **Estado: aprobado por Sebastian el 2026-10-06, con las dependencias listadas.** Se basa en [SPEC.md](../SPEC.md) (aprobada) y en [docs/ARQUITECTURA.md](../docs/ARQUITECTURA.md) (aprobada). Las tareas están en [todo.md](todo.md).

## Resumen

Las fases 0 y 1 están detalladas tarea por tarea. Las fases 2 a 6 quedan como índice y se detallan al llegar a ellas, con lo que se haya aprendido hasta ahí.

En la fase 0 se atacan primero los tres riesgos técnicos:

1. que el deploy en Cloud Run con Neon funcione y se pueda repetir;
2. que OR-Tools corra en Cloud Run a una velocidad aceptable;
3. que el PNG se genere y se comparta desde el celular.

Si alguno falla, se cambia el plan el día 1 y no el día 4.

## Decisiones para este plan

- **Dependencias.** Se piden al aprobar este plan:
  - **Producción:** `django`, `django-htmx`, `whitenoise`, `gunicorn`, `psycopg[binary]`, `dj-database-url`, `pydantic` y `ortools`.
  - **Desarrollo:** `pytest`, `pytest-django`, `hypothesis`, `mypy`, `django-stubs` y `ruff`.
  - **Más adelante:** `faker`, recién en la fase 2.
  - **En el navegador,** copiadas dentro del repo sin CDN: `htmx` y `modern-screenshot`. Tailwind CSS v4 se compila con su ejecutable propio, sin Node.
- **Configuración por variables de entorno:** `DATABASE_URL`, `SECRET_KEY`, `DEBUG` y `ALLOWED_HOSTS`. En local salen de `.env`; en Cloud Run, de Secret Manager.
- **Migraciones en la nube:** se corren como un Cloud Run Job antes de cada deploy, no al arrancar el contenedor. Así nunca hay dos migraciones a la vez.
- **Usuarios iniciales:** un comando `crear_usuario` que toma la contraseña de una variable de entorno y no la imprime nunca.
- **Pruebas de riesgo:** viven detrás del login, en `/diagnostico/`, solo para staff. Se borran al cerrar la fase 4.

## Índice de tareas

### Fase 0: cimientos (día 1, mañana)

- [x] T0.1 Proyecto Python con herramientas de calidad
- [x] T0.2 Proyecto Django con settings por entorno
- [x] T0.3 Login y plantilla base para el celular
- [x] T0.4 Guardas del repo: dominio sin Django y chequeo antes de cada commit
- [x] T0.5 Deploy repetible en Render con Neon (demo) *(necesita pasos tuyos)*
- [x] T0.6 Prueba de riesgo: OR-Tools en Render
- [ ] T0.7 Prueba de riesgo: PNG y compartir desde el celular

**Checkpoint de la fase 0:**

- [x] Tests, mypy y ruff en verde.
- [x] Entras con login a la URL de la demo (Render) desde el celular.
- [x] Están medidos los tiempos del solver con los límites de Render (H6 en PROGRESO.md).
- [ ] El PNG se compartió por WhatsApp desde tu celular. Si falla, se pasa al plan B con Pillow.
- [x] Revisión con `code-review-and-quality` (ver PROGRESO.md).
- [ ] Tu visto bueno.

### Fase 1: configuración (día 1, tarde)

- [x] T1.1 Dominio: modelos de configuración y reglas (CAT-01 a CAT-03)
- [x] T1.2 Dominio: franjas con fechas concretas y compatibilidad resuelta (CAT-04)
- [x] T1.3 Modelos Django de configuración
- [x] T1.4 Comando `cargar_config` con la configuración 2026
- [x] T1.5 Admin de la configuración e identidad del organizador

**Checkpoint de la fase 1:**

- [ ] El torneo 2026 está cargado en la demo, con 23 categorías-nivel, 5 canchas (incluidas C1A y C1B) y 15 franjas. *(Probado en local; en la demo lo corre Sebastian.)*
- [x] Se edita en el admin, y una regla inválida se rechaza con un mensaje junto al campo.
- [x] Cada regla CAT tiene su test.
- [x] Revisión con `code-review-and-quality` (ver PROGRESO.md).
- [ ] Tu visto bueno.

### Fase 1b: pantallas propias (antes de la inscripción)

> Aprobada por Sebastian el 2026-10-07. Reemplaza al admin como pantalla del organizador, según `docs/DISENO.md`. El detalle está en [todo.md](todo.md).

- [x] TU.1 Base visual: tokens, plantilla y navegación
- [x] TU.2 Roles: Organización y Mesa de control
- [x] TU.3 Reglas del torneo con interruptores
- [x] TU.4 Crear torneo con el asistente
- [x] TU.5 Inicio y Torneo
- [x] TU.6 Página pública (base)
- [x] TU.7 Datos de la escuela

**Checkpoint de la fase 1b:**

- [x] El organizador crea el torneo 2026 y edita sus reglas sin tocar el admin ni la terminal.
- [x] La mesa entra con su rol y ve los avisos donde no tiene permiso.
- [x] La página pública se abre sin login y no muestra datos personales.
- [x] Revisión con `code-review-and-quality` (ver PROGRESO.md).
- [ ] Tu visto bueno (pendiente a tu vuelta: REVISAR.md).

### Fase 2: inscripción (día 2)

> Se avanza con la autorización general del 2026-10-07 (sin visto bueno entre fases; dudas en `docs/REVISAR.md`). El detalle está en [todo.md](todo.md).

- [x] T2.1 Dominio: normalización de documentos (INS-04)
- [x] T2.2 Dominio: validaciones de inscripción (INS-02, 03, 05 a 10)
- [x] T2.3 Modelos de inscripción, y datos personales fuera de los logs
- [x] T2.4 Servicio de inscripción
- [x] T2.5 Pantallas: equipos
- [x] T2.6 Pantallas: jugadores y cuerpo técnico, con avisos en vivo
- [x] T2.7 Generador de datos de demo

**Checkpoint de la fase 2:**

- [x] Se cumplen los criterios de inscripción de la sección 10, con un test por regla INS.
- [x] La demo tiene unos 80 equipos inventados (93), y ningún dato personal aparece en los logs. *(Probado en local; en la demo lo corre Sebastian: DESPLIEGUE.md, 3c.)*
- [x] Revisión con `code-review-and-quality` (ver PROGRESO.md).
- [ ] Tu visto bueno (pendiente a tu vuelta: REVISAR.md).

### Fase 3: fixture y verificador (día 3)

> Planificada el 2026-10-07. Se avanza con la autorización general del mismo día. El detalle está en [todo.md](todo.md).

- [x] T3.1 Formatos como datos (FIX-01, FIX-02, FIX-07)
- [x] T3.2 Dominio: cruces de la fase de grupos (FIX-03 a FIX-05)
- [x] T3.3 Dominio: sorteo de series y fixture completo (FIX-06, FIX-08)
- [x] T3.4 Modelos Serie y Partido, y servicio de fixture (FIX-09)
- [x] T3.5 Pantallas: series y fixture
- [x] T3.6 Dominio: verificador de choques y prueba 2023
- [x] T3.7 Capacidad con flujo máximo y pantalla "Programar"

```
T3.1 → T3.2 → T3.3 → T3.4 → T3.5
                       └──→ T3.7
T3.6 (independiente: recibe cualquier calendario)
```

**Checkpoint de la fase 3:**

- [x] Cada formato da de 8 a 27 partidos según corresponda, sin cruces repetidos ni equipos dos veces en una fecha.
- [x] El verificador pasa la prueba 2023 por tipo: 2 de personas, 3 de cancha y 0 de compatibilidad.
- [x] La capacidad de la demo se ve en pantalla.
- [x] Revisión con `code-review-and-quality` (ver PROGRESO.md).
- [ ] Tu visto bueno (pendiente a tu vuelta: REVISAR.md).

### Fase 4: programador (día 4)

> Planificada el 2026-10-07. Se avanza con la autorización general del mismo día. El detalle está en [todo.md](todo.md).

- [x] T4.1 Pares de equipos que comparten personas
- [x] T4.2 Dominio: modelo CP-SAT (cancha, franja y equipo)
- [x] T4.3 Dominio: personas, bloqueos, orden y eliminación
- [x] T4.4 Dominio: por qué no entra un partido
- [x] T4.5 Corrida y servicio de programación
- [x] T4.6 Pantallas: programar y calendario por día y cancha
- [x] T4.7 El torneo de demo programado, y limpieza de la espiga

```
T4.2 → T4.3 → T4.4 ─┐
T4.1 ───────────────┴→ T4.5 → T4.6 → T4.7
```

**Checkpoint de la fase 4:**

- [x] El torneo de demo queda programado con 0 choques duros, o la app lista lo que no entra y por qué. *(223 de 223, en local.)*
- [x] La programación corre dentro del request, con límite de tiempo, y no se pueden lanzar dos a la vez.
- [x] Revisión con `code-review-and-quality` (ver PROGRESO.md).
- [ ] Tu visto bueno (pendiente a tu vuelta: REVISAR.md).

### Fase 5: reprogramación y calendario (día 5)

> Planificada el 2026-10-07. Se avanza con la autorización general del mismo día. El detalle está en [todo.md](todo.md).

- [x] T5.1 Bloqueos de la ACF
- [x] T5.2 Dominio: propuestas de reprogramación
- [x] T5.3 Pantalla de propuestas, aplicar e historial
- [x] T5.4 Cambio manual verificado
- [x] T5.5 Suspender un día y agregar un día entre semana
- [x] T5.6 PNG del día por cancha
- [x] T5.7 Vistas por categoría y por club
- [x] T5.8 Instalación en el celular y ensayo de la demo

```
T5.1 → T5.2 → T5.3 → T5.4
                 └──→ T5.5
T5.6 y T5.7 (independientes)
T5.3 + T5.6 → T5.8
```

**Checkpoint de la fase 5:**

- [x] Un bloqueo ACF da 2 o 3 propuestas ordenadas, y aplicar una deja el calendario sin choques.
- [x] El PNG de un día se comparte sin datos personales. *(Falta la prueba en tu Android: R45.)*
- [x] Revisión con `code-review-and-quality` (ver PROGRESO.md).
- [ ] Tu visto bueno (pendiente a tu vuelta: REVISAR.md).

### Fase 6: producción 2026

> Planificada el 2026-10-08. A (T6.1 a T6.4) se puede avanzar ya; B (T6.5 a T6.7) necesita a Sebastian: producción, nube, costos y respuestas del organizador. El detalle está en [todo.md](todo.md).

- [x] T6.1 Asignar a mano los participantes de la eliminación (P50)
- [x] T6.2 Personas: invitar, cambiar el rol y la contraseña
- [x] T6.3 Revisión de seguridad
- [x] T6.4 Retención de datos (P49)
- [ ] ~~T6.5 Producción separada de la demo~~ *(reemplazada por T7.10)*
- [ ] ~~T6.6 Configuración con las respuestas del organizador~~ *(reemplazada por T7.4 y T7.5)*
- [ ] T6.7 Carga de las listas reales y publicación *(necesita a Sebastian; después de T7.8 y T7.10)*

**Checkpoint de la fase 6:**

- [ ] El fixture y el calendario 2026 están publicados (necesita T6.7, T7.10 y la fase 7).
- [x] Revisión con `code-review-and-quality` de la parte A (ver PROGRESO.md).
- [ ] Tu visto bueno.

### Pedido 2026 (fases 7 a 9)

> Planificadas el 2026-10-12 desde `docs/PEDIDO_CLAUDE_CODE.md`, con `docs/REVISION_RONDO_FASE4.md`, `docs/CONVOCATORIA_2026_PARA_RONDO.md` y `docs/PREGUNTAS_JMP_CUP_2026.md` (desde ahora, la fuente de las P). Pendientes del visto bueno de Sebastian. El detalle está en [todo.md](todo.md).
>
> **Cómo se trabaja (autorizado en el pedido):** las preguntas sin respuesta no frenan: quedan configurables con el valor por defecto de PREGUNTAS y un `TODO(P#)`. Dependencias aprobadas: `django-storages[s3]` y `Pillow`. Durante la prueba del martes 13/10 no se fusiona nada a `main` hasta que Sebastian avise, y nunca se corre `generar_demo` en la demo.

#### Fase 7: bloque A, calendario y carga de listas (para el miércoles 14/10)

- [x] T7.1 La eliminación respeta el turno libre (P17), en el modelo y en el verificador
- [x] T7.2 Profes: seguidos en la misma cancha, y el choque solo para el entrenador (P18, P35, P57)
- [x] T7.3 Objetivo blando: menos espera de los profes (PRO-11)
- [x] T7.4 Fútbol 6 y plantilla 2026 (convocatoria)
- [x] T7.5 Copa de Bronce con interruptor (P62)
- [x] T7.6 Fecha de nacimiento: alcanza con el año
- [x] T7.7 Dominio: leer filas pegadas
- [x] T7.8 Pantalla: pegar la lista de jugadores
- [x] T7.9 Pantalla: pegar el cuerpo técnico
- [x] T7.10 Producción preparada (T6.5) *(el despliegue lo hace Sebastian)*
- [x] T7.11 Borrador del calendario y fixture desactualizado
- [x] T7.12 Medir la programación 2026 con 1 CPU

```
T7.1 → T7.2 → T7.3 ─┐
T7.4, T7.5 ─────────┴→ T7.12
T7.6 → T7.7 → T7.8 → T7.9
T7.10 y T7.11 (independientes)
T7.8 + T7.10 → T6.7 (carga real, en producción)
```

**Checkpoint de la fase 7:**

- [x] Verde, más `pytest -m lento`.
- [x] La demo programada con la plantilla 2026, sin choques ni llaves encadenadas sin descanso, y la medición en PROGRESO.md (H7).
- [x] Una lista recreada con datos inventados se pega en menos de un minuto.
- [x] `docs/DESPLIEGUE.md` listo para crear producción.
- [x] Revisión con `code-review-and-quality` (PROGRESO.md). Visto bueno dado por adelantado (2026-10-12).

#### Fase 8: bloque B, reemplazar a Copa Fácil (antes del viernes 23/10)

- [x] T8.1 Almacenamiento de imágenes conectable (B1)
- [x] T8.2 Procesar la imagen al subirla
- [x] T8.3 Escudo del club, logo del organizador y patrocinadores (B2, P68, P69)
- [x] T8.4 Foto de la persona y autorización (B2, P66, P67, P75)
- [x] T8.5 Resultado y eventos del partido (dominio y modelo, B3)
- [x] T8.6 Ficha del partido en el celular (B3)
- [x] T8.7 Tabla de posiciones (B4, P26, P28, P34)
- [x] T8.8 Cruces de la eliminación desde la tabla (B6, P50)
- [x] T8.9 Suspensiones (B5, P29, P74)
- [x] T8.10 Página pública en vivo: partidos, posiciones, goleadores y ficha (B7, P65, P71)
- [x] T8.11 Página pública: equipo, patrocinadores y caché (B7)
- [x] T8.12 PNG del fixture con el diseño 2026 (B8) *(falta probarlo en el Android de Sebastian)*

```
T8.1 → T8.2 → T8.3 ─┬──────────→ T8.12
          └──→ T8.4 ┤
T8.5 → T8.6         │
  ├──→ T8.7 → T8.8  │
  │      └──→ T8.10 ┴→ T8.11
  └──→ T8.9
```

**Checkpoint de la fase 8:**

- [x] Verde, más `pytest -m lento`.
- [x] Un partido cargado desde el celular aparece en la página pública, con la tabla y los goleadores al día.
- [x] Ninguna página pública muestra CI, fecha de nacimiento, apellido completo ni fotos sin autorización.
- [x] Revisión con `code-review-and-quality` y `security-and-hardening` (subida de imágenes), (PROGRESO.md). Visto bueno dado por adelantado.

#### Fase 9: bloque C, durante el torneo

- [x] T9.1 Retención: anonimizar también borra las fotos (P49, P76)
- [x] T9.2 Pantalla de suspendidos para la mesa

**Checkpoint de la fase 9:**

- [x] Verde, revisión con `code-review-and-quality` (PROGRESO.md). Visto bueno dado por adelantado.

#### Fase 10: respuestas del organizador

> Planificada el 2026-10-13 con las respuestas en `docs/PREGUNTAS_JMP_CUP_2026.md`. Primero lo que pesa en el calendario del 21/10.

- [x] T10.1 Reglas del calendario que cambian solo de valor (P35, P19)
- [x] T10.2 La hora final de la franja es el último inicio (P48)
- [x] T10.3 Días y horarios por categoría (P56)
- [x] T10.4 Sub 10 y Sub 11 Avanzado en F11 (P60) y capacidad
- [x] T10.5 Canchas flexibles (P13, P63)
- [x] T10.6 Preferencias del calendario (P17, P55; el club el mismo día queda para después)
- [x] T10.7 Un solo rol por ahora (P64)
- [x] T10.8 Formato para más de 10 equipos (P27, P54)
- [x] T10.9 El partido en vivo, a mano
- [x] T10.10 Reprogramar con W.O. y contador
- [x] T10.11 Dorsal flexible

**Checkpoint de la fase 10:**

- [ ] Verde, más `pytest -m lento`.
- [ ] El calendario 2026 con F11 medido (H8).
- [x] Revisión con `code-review-and-quality` y PROGRESO.md al día.

#### Fase 11: respuestas y cambios

> Planificada el 2026-10-13 con `docs/RESPUESTAS_Y_CAMBIOS.md`. Detalle en `tasks/todo.md`.

- [x] T11.2 Avisos en lugar de bloqueos al mover
- [x] T11.3 Todas las canchas partibles y ubicar a mano
- [x] T11.4 Reglas del calendario (P33, P20) y faltante de F11
- [x] T11.5 Altas tardías y plantel máximo con aviso
- [x] T11.6 Pantalla de clubes
- [x] T11.1 Agregar una categoría o un nivel a un torneo creado
- [x] T11.7 Historial del partido
- [x] T11.8 Planilla: convocados y dorsal del partido
- [x] T11.9 Alta rápida en la cancha
- [x] T11.10 Eventos completos y partido terminado editable
- [x] T11.11 Partidos de hoy
- [x] T11.12 Cierre automático
- [x] T11.13 Penales tiro por tiro
- [x] T11.14 Página pública
- [x] T11.15 Rehacer el fixture con partidos jugados
- [x] T11.16 Pasada de UI/UX

#### Fase 12: revisión de la fase 11

> `docs/PEDIDO_FASE_12.md`. Detalle en `tasks/todo.md`.

- [x] Bloque A: programador (A1 a A5)
- [x] Bloque B: reprogramar (B1 a B9)
- [x] Bloque C: día de partido (C1 a C4)

#### Fase 13: producción y respuestas del 2026-10-15

> `docs/PENDIENTES_PRODUCCION.md`. Detalle en `tasks/todo.md`. Meta: usar Rondo desde el 24/10 (P77).

- [x] Bloque A, antes de cargar datos reales (17/10): T13.1 y T13.2 escudo por equipo, T13.3 borrar club y equipo, T13.4 retirar equipo, T13.5 roles
- [ ] Checkpoint A: revisión de cierre de las fases 11, 12 y del bloque A; desplegar, vaciar producción y crear el torneo real. Si no está el 17/10, avisar a Sebastian (carga de 1.700 jugadores)
- [x] Bloque B, fallos (salvo T13.6, que espera P90). Para el fixture (20/10): T13.6 mismo club (espera P90), T13.7 categoría de 2, T13.8 F11 en C3, T13.9 pendientes, T13.10 sorteo. Para el día de partido (22/10): T13.11 cierre "Nunca", T13.12 alta hasta el 2.º tiempo, T13.13 PNG, T13.14 logo y favicon
- [ ] Checkpoint B: recorrido como Organización y como Mesa, y despliegue
- [x] Bloque C, durante el torneo: T13.15 a T13.24 (reprogramar, bloqueos, horarios sugeridos, propuestas, fijar, editar cruces, copas por club)
- [x] Bloque D, diseño y textos: T13.25 a T13.31
- [ ] Checkpoint D: `code-review-and-quality` y visto bueno
- [x] Bloque E, prueba desde el celular (2026-10-15): T13.32 PNG, T13.33 interruptores, T13.34 y T13.37 "¿Entra todo?", T13.35 programar sin solución, T13.36 resultado de la última corrida
- [x] Bloque F, pedidos del 2026-10-17: T13.38 la imagen como en Render en local, T13.39 «Un equipo no puede jugar», T13.40 botones que calculan
- [ ] Bloque G, pedidos del 2026-10-17 (tarde): T13.41 "Calculando…" en Rehacer y Reprogramar lo cambiado (hecho), T13.42 propuestas que no encuentran lugar (hecho), T13.43 memoria con 512 MB

## Grafo de dependencias

```
T0.1 → T0.2 → T0.3 → T0.5 → T0.6
         │             └──→ T0.7
         └→ T0.4
T0.2 → T1.1 → T1.2 → T1.3 → T1.4 → T1.5
```

T0.4 y T1.1 no dependen del deploy. Si el deploy se traba esperando tus cuentas, la fase 1 avanza igual.

## Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| El deploy se traba por permisos o configuración de Google Cloud | Alto | Lo hacemos juntos, paso a paso, y queda documentado en `docs/DESPLIEGUE.md`. Mientras tanto, la fase 1 avanza en local |
| OR-Tools anda lento con 1 vCPU | Medio | Se mide en T0.6. Si hace falta, se usan 2 vCPU, y el peor caso de costo sigue siendo bajo |
| La Web Share API no comparte archivos en algún celular | Medio | T0.7 lo prueba en Android y, si es posible, en un iPhone. El respaldo es la descarga |
| No se cumple el día por tarea | Medio | Se aplica el orden de recorte de ARQUITECTURA.md |
| Bloque A son 12 tareas para el 14/10 | Alto | Primero lo que destraba el 21/10: T7.10 (producción, para cargar listas reales) y T7.6 a T7.8 (pegar listas); T7.1 a T7.3 y T7.11 antes del 21/10. Lo que no llegue se avisa con fecha |
| La fase 8 no llega al 23/10 | Alto | Orden del pedido (B1 → B8). Lo mínimo para la 1.ª fecha: T8.5, T8.6, T8.7 y T8.10. Si no está, la 1.ª fecha va en Copa Fácil (P77) |
| `modern-screenshot` no puede leer imágenes de R2 desde otro origen (canvas contaminado) | Medio | Servir las imágenes por la app (mismo origen) o configurar CORS en el bucket. Se decide en T8.12 |
| La caché pública entrega URL firmadas vencidas | Bajo | Las URL firmadas duran más que la caché (por ejemplo, 1 hora contra 60 segundos) |
| Sumar la espera de los profes vuelve lento al solver con 4 fines de semana | Medio | Se mide en T7.12 con 1 CPU antes de recortar, como pide la revisión |
| La migración del escudo por equipo (T13.1) llega tarde y hay que migrar datos reales | Alto | Va primera. La migración copia antes de quitar `Club.escudo`, y se prueba con la base de la demo antes de producción |
| El bloque B no llega al 23/10 | Alto | Primero lo del fixture (T13.6 a T13.10). Lo mínimo para el día de partido son T13.11, T13.12 y T13.13. El bloque C se usa recién con el torneo empezado |
| P90 (mismo club) no se responde antes del 21/10 | Medio | Valor por defecto "como mucho se cruzan en la final"; Sebastian decide el 20/10 si se implementa sin respuesta |

## Preguntas abiertas

- El PNG se prueba solo en Android: no hay un iPhone a mano.
- Las preguntas al organizador (P1 a P51) siguen abiertas. Ninguna bloquea las fases 0 y 1.
- Desde el 2026-10-12, las preguntas abiertas (P1 a P77) están en `docs/PREGUNTAS_JMP_CUP_2026.md`, cada una con su valor por defecto. Ninguna frena las fases 7 a 9.
