# Revisión externa de Rondo: fase 4

**Fecha:** 2026-10-07.
**Commit revisado:** `a0b9991` (merge de la fase 4 y plan de la fase 5). T5.1 (`f4b5ca3`) y lo que vino después no están revisados.

Esta revisión la pide Sebastian. Responde a R41 y R43 de `docs/REVISAR.md` y agrega hallazgos nuevos. Anótala en `docs/PROGRESO.md` y planifica las correcciones antes de seguir con T5.2.

## Cómo se revisó

- **Entorno:** clon limpio, Postgres 16 local y `uv sync`.
- **Calidad:** tests rápidos y lentos, mypy y ruff.
- **Demo:** `generar_demo`, luego fixtures y luego programar los 223 partidos.
- **Verificador propio:** el calendario resultante pasó por un verificador escrito desde las secciones 4 y 5 de `docs/CONTEXTO_JMP_CUP.md`, sin usar `dominio/verificador.py`.
- **Fixtures:** 1.800 fixtures al azar, de 2 a 10 equipos, con clubes al azar.
- **Datos reales:** se buscaron en el repo y en su historia los documentos y los textos de las listas de buena fe de 2023 y de la planilla 2025.
- **Secretos:** se revisó toda la historia de git.
- **Páginas públicas:** consultas a la base, tiempo de respuesta y datos personales.

## Lo que está bien

- **Calidad:** 478 tests rápidos y el lento pasan; el que falla se explica en el punto 6. mypy no encuentra problemas en 136 archivos y ruff tampoco.
- **Programación de la demo:** salen 223 de 223 partidos, con solución óptima, en 44 s con 2 CPU. El verificador propio, escrito desde el CONTEXTO, encuentra **0 choques duros**. Revisa:
  - canchas, con C1 ocupando C1A y C1B;
  - compatibilidad y franjas;
  - equipos: turno libre y máximo de 2 por día;
  - profes y jugadores compartidos;
  - orden de las fechas;
  - eliminación después de los grupos y desde el 5.º fin de semana.
- **Prueba de 2023:** da 2 choques de personas, los de River Plate.
- **Fixture:**
  - De 3 a 10 equipos da 8, 10, 12, 14, 17, 18, 22 y 27 partidos.
  - Las llaves de Oro, Plata y Bronce coinciden con la tabla 4.5, con P25 y P26.
  - En los 1.800 fixtures al azar: 0 cruces repetidos o faltantes, nadie juega dos veces en una fecha y P24 se cumple.
- **Configuración:** `jmp_cup_2026.json` coincide con la tabla 4.1 del reglamento en años, modalidad, plantel, minutos, turnos de 40/50/60/70, canchas, franjas y cuerpo técnico.
- **Privacidad:**
  - De los 426 números de 6 a 9 dígitos de las listas reales (documentos y teléfonos), ninguno está en el repo ni en su historia. De los textos de esas listas, solo aparece el encabezado "fecha de nacimiento".
  - Las 69 páginas públicas no muestran ninguno de los 1.502 apellidos de la demo.
  - Toda pantalla interna redirige al login, incluidos `/diagnostico/` y `/admin/`.
- **Secretos:** no hay ninguno en la historia, y `.env` nunca se subió.
- **Página pública:** hace de 6 a 10 consultas y responde en 10 a 25 ms en local. Es liviana.
- **Trabajo ordenado:** las reglas están en la configuración con su ID y su P#, y PROGRESO, REVISAR y las fases están al día.

## Para Claude Code: qué corregir, en orden

### 1. La eliminación no respeta el turno libre del equipo (P17). Prioridad alta

**Problema:** las llaves tienen participantes "por definir". Por eso, ni el modelo ni el verificador les aplican las restricciones de equipo. `_despues()` solo exige que la llave empiece después del turno de la llave anterior, así que el ganador de una semi puede jugar la final enseguida. El verificador dice "0 choques", pero el calendario rompe P17.

**Evidencia, en la demo programada:**
- Sub 15 Avanzado: la semi 1 de Oro es el viernes 20/11 a las 17:10 en C3, y la final de Oro, a las 18:20 en C3. Son dos partidos F11 de 65 minutos con solo 5 minutos entre uno y otro.
- Sub 11 Inicial: la semi 2 de Oro es el domingo 22/11 a las 8:50 en C2, y la final de Plata, a las 10:10 en C1. Quedan 30 minutos libres, y P17 pide un turno de 50.

**Qué hacer:**
- En el modelo, tratar a cada participante referido (ganador, perdedor o mejor perdedor de una llave) como un equipo virtual. Si la llave que lo define y la que lo usa caen el mismo día, la segunda empieza a partir de `inicio + turno × (1 + turnos_libres_mismo_dia)`.
- Lo mismo entre el último partido de grupos de la categoría y las llaves que toman posiciones, si caen el mismo día.
- El verificador tiene que detectar esos mismos casos.

**Listo cuando:**
- Un test con 4 equipos y una sola franja no deja la final a menos de semi + 2 turnos.
- El verificador marca el caso de Sub 15.
- En la demo no queda ninguna llave encadenada sin descanso.

### 2. Profes compartidos: se prohíbe justo lo que P18 permite (responde R41). Prioridad alta

**Problema:** el modelo suma el margen de 10 minutos (P35) aunque los dos partidos sean en la misma cancha. P18 y la sección 6.4 dicen que seguidos en la misma cancha está bien; así lo hacía el organizador (Crack FC en C2 a las 11:20 y 12:10). Además, el objetivo de agrupar (PRO-11, P20) se recortó. Resultado: los profes esperan mucho más que en 2023.

**Evidencia** (pares de partidos con un profe compartido, el mismo día):

| | 2023, a mano (un fin de semana) | Demo, Rondo (cinco fines de semana) |
|---|---|---|
| Pares | 10 | 12 |
| Espera mediana | 20 min | 65 min |
| Espera media | 49 min | 122 min |
| Espera máxima | 165 min | 355 min |
| Seguidos en la misma cancha | 3 | 0 |
| Esperas de más de 2 h | 2 | 5 |

**Qué hacer:**
- En `personas()`, aplicar el margen solo cuando cambia la cancha, igual que el verificador. Una forma: la cancha es una variable, así que se puede usar un `NoOverlap` sin margen y, para cada par de partidos del profe en canchas distintas, una restricción de separación condicionada a esas canchas.
- Sumar un objetivo blando que penalice la espera del profe entre sus partidos del día (PRO-11), con menos peso que ubicar partidos.
- Si el modelo se vuelve lento con el tamaño de 2026 (H4, H6), medirlo y avisar antes de recortar.

**Listo cuando:**
- Un test con un profe compartido acepta dos partidos seguidos en la misma cancha (5 minutos entre ellos) y rechaza 5 minutos en canchas distintas.
- En la demo, la espera mediana de los profes baja a menos de 30 minutos, sin choques. Si no se llega, se informa cuánto se logró y por qué.

### 3. Asignar los participantes de la eliminación (P50). Antes del 20/11

**Problema:** no hay pantalla para asignar quién juega cada llave, y no está en la fase 5. Sin eso, el calendario y el PNG del último fin de semana dicen "1.º A vs 2.º B".

**Qué hacer:** la organización asigna los equipos de cada llave. Al guardar, corre el verificador con los equipos ya definidos: ahí aparecen los choques de profes, los descansos y los bloqueos. Si los hay, se ofrece reprogramar con T5.2.

**Listo cuando:** asignar una llave que choca muestra el choque y ofrece propuestas.

### 4. El calendario se ve desprolijo. Prioridad baja

**Problema:** 30 de los 223 partidos empiezan en un minuto terminado en 5 (8:55, 10:15, 12:05…). El objetivo no premia los turnos seguidos en cada cancha: C1A tiene 795 minutos ociosos entre partidos y C3, 745.

**Qué hacer:** penalizar los huecos entre partidos de una misma cancha y el día, o preferir inicios en múltiplos de 10 minutos. Cualquiera de las dos, con menos peso que el punto 2.

### 5. Reparto entre fines de semana (R43). Solo informativo

La fase de grupos queda con 56, 42, 44 y 15 partidos, y la eliminación, con 66. El 4.º fin de semana queda casi libre. Puede servir de colchón por lluvia: es la pregunta P58 de más abajo. No cambiarlo hasta tener la respuesta.

### 6. Un test falla en un clon nuevo. Prioridad baja

`tests/rondo/test_settings.py::test_produccion_pasa_check_deploy_sin_advertencias` falla con `staticfiles.W004`, porque `assets/` no existe hasta compilar Tailwind. Hay dos opciones: crear el directorio, o poner `tailwind build` en la sección "verde" de CLAUDE.md.

### 7. Login sin límite de intentos. Antes de cargar listas reales

La app va a tener datos de menores en una URL pública, y el login no limita los intentos. Proponle a Sebastian una solución. Si necesita una dependencia, pregúntale antes (SPEC, Límites).

### 8. El solver corre dentro del request. Para la fase 6

Hay un solo worker de gunicorn con 4 threads, y CP-SAT usa 8 trabajadores. Mientras se programa o reprograma, la página pública se frena. En Render gratis, con 0,1 CPU, casi se detiene.

**Para producción:**
- correr el solver en un proceso aparte (job o cola), o limitar sus trabajadores;
- cachear las páginas públicas unos 60 segundos.

## Para Sebastian: decisiones y acciones

- **El repo es público.** Se clona sin credenciales, aunque PROGRESO dice "repo privado". Si vas a licenciar el sistema, cualquiera puede copiar el código. Además quedan a la vista notas internas: la URL de la demo y lo de la cuenta de facturación. Se cambia en GitHub → Settings → Danger Zone → Change visibility. Los repos privados son gratis.
- **Hosting para el torneo.** Render gratis no sirve para 100 personas a la vez:
  - tiene 0,1 CPU;
  - se duerme a los 15 minutos y tarda alrededor de 1 minuto en despertar;
  - el solver corre en el mismo proceso que la página.

  La cuenta de facturación de Google Cloud está bloqueada (PROGRESO, decisión del 2026-10-07). Hay dos caminos: resolverlo esta semana con soporte de Google, o elegir un plan pago (por ejemplo, Render Starter).
- **Tiempos.** El torneo empieza el viernes 23/10, y la fase 6 (producción, respaldos, usuarios reales) todavía no está planificada. Cargar unos 1.700 jugadores a mano (P51) lleva días. Conviene priorizar "pegar filas desde Excel" por delante de T5.7 (vistas por club).
- **Resultados y tabla.** No están en el alcance. Hay que decidir si en 2026 siguen en Copa Fácil, para no cargar los equipos dos veces.

## Preguntas nuevas para el organizador (siguen desde P55)

| # | Pregunta | Por defecto mientras tanto |
|---|---|---|
| P55 | ¿Las finales se juegan todas el domingo, por la premiación? Hoy 3 finales caen el viernes 20 (Sub 10 Avanzado a las 16:00 y 18:30, y Sub 15 Avanzado a las 18:20) | Sin preferencia. Si dice que sí, va como objetivo blando |
| P56 | ¿Hay un horario límite para Sub 5 a Sub 7 el viernes? Hoy hay 6 partidos desde las 18:00; la semi de Sub 5 es a las 19:20 | Sin límite. Si lo hay, franja por categoría en la configuración |
| P57 | ¿El choque de profes aplica solo al entrenador, o también al asistente y al delegado? Hoy cuentan los tres | Los tres |
| P58 | ¿El 4.º fin de semana queda como colchón para reprogramar (hoy tiene 15 partidos) o se reparte parejo? | Como está |
| P59 | ¿Los resultados y la tabla de 2026 se llevan en Copa Fácil o en Rondo? | Copa Fácil, hasta que se especifiquen en Rondo |

## Qué no cubre esta revisión

- El código de la fase 5 (T5.1 en adelante).
- Cómo se ven las pantallas y el PNG: hacen falta capturas.
- El sitio de demo en línea.
