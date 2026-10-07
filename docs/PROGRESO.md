# PROGRESO: app de la JMP CUP

Bitácora para retomar el trabajo si una sesión se corta. Las reglas del negocio están en [CONTEXTO_JMP_CUP.md](CONTEXTO_JMP_CUP.md). Las preguntas P1 a P32 están en su sección 9; las nuevas siguen desde P33.

## Estado

- **Fase:** 0, cimientos. Plan aprobado.
- **Siguiente paso:** T0.4 (ver [tasks/todo.md](../tasks/todo.md)).

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
- 2026-10-06: PR #1 (T0.1) y PR #2 (T0.2) abiertos en GitHub.

## Pendiente

- [ ] T0.1 a T0.7 (fase 0) y T1.1 a T1.5 (fase 1).
- [ ] Para la fase 0: facturación activa en la cuenta de Google Cloud de Sebastian, y el proyecto `rondo-jmp` en Neon (región São Paulo, sin las integraciones de GitHub ni de Vercel).
- [ ] Mandar al organizador las preguntas P33 a P51.

## Decisiones

| Fecha | Decisión | Motivo |
|---|---|---|
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
