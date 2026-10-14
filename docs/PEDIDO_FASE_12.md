# Pedido para Claude Code: fase 12

**De:** Sebastian. **Fecha:** 2026-10-13. **Base:** `main` en 4e43ffd (fase 11). Reemplaza los dos bloques de revisión que pasó antes por chat.

## Cómo trabajarlo

- **Prioridad:** que la logística y la flexibilidad funcionen bien. Lo estético y los detalles van después.
- **Principio** (RESPUESTAS_Y_CAMBIOS): Rondo propone y avisa; la organización decide. Solo se bloquea lo físicamente imposible.
- **Orden:** bloque A, después B, después C. Cada punto con su test, y el verificador cuando corresponda.
- **Cambios de modelo autorizados:** los de C1 y C2. Son aditivos o sacan una restricción, sin pérdida de datos. Cualquier otro se pregunta.
- **Producción:** DESPLIEGUE.md está bien; no cambiarlo. Desde el 14/10 producción tiene datos reales: las migraciones no pueden borrar nada.

## Revisión externa de la fase 11

Tests rápidos (1012) y lentos (2), mypy y ruff: en verde. Demo 2026 con 1 CPU, 4 trabajadores y 120 s, revisada con un verificador aparte:

| Escenario | Ubicados | Notas |
|---|---|---|
| Sin jueves, orden "blanda" | 218 de 223 | 5 de C3 sin lugar |
| Sin jueves, orden "dura" | 217 de 223 | 6 de C3 sin lugar, todos de grupos. 0 al revés. Finales el 14 y el 15/11 |
| Jueves 29/10, 5/11 y 12/11 de 16 a 20, "blanda" | 223 de 223 | Ver A2, A3 y A4 |
| Mismos jueves, "dura", Sub 5 y Sub 6 sin jueves | 223 de 223 | Ver A1 |

## Bloque A. Programador (antes del 21/10)

- **A1. Máximo de partidos por día (P47) entre grupos y eliminación.** Ni el programador ni el verificador cuentan que un equipo que juega grupos ese día puede jugar después la semi y la final. Caso: Sub 11 Inicial (4 equipos), domingo 15/11: grupos 08:50, semis 10:30 y 12:10, final de Oro 13:50 y de Plata 14:40: los dos equipos de las 08:50 juegan 3 partidos ese día. Sin jueves pasó en Sub 11 Avanzado, sábado 14/11: grupos 09:00, semis de Plata 11:40 y 13:30, final de Plata 15:10.
- **A2. Orden de fechas "blanda" (P19).** Hoy "blanda" saca la restricción y no la penaliza; RESPUESTAS_Y_CAMBIOS pide penalizarla en el objetivo. Con "blanda", 36 de 93 equipos empiezan por una fecha que no es la 1 y 57 de 221 pares seguidos quedan al revés. Con "dura" entran igual: cuando se puede, 0 al revés.
- **A3. Sub 5 y Sub 6 (P56): solo sábado y domingo.** Con los jueves, la app puso 7 partidos de Sub 5 y Sub 6 el jueves a las 16:00. En la plantilla, `dias_sin_jugar` de lunes a viernes. Decirle a Sebastian qué cambiar a mano en Ajustes en producción.
- **A4. Tiempo extra solo para lo que no entra (P78).** Al agregar un día u horario, elegir en qué canchas vale (por ejemplo, solo C3). El programador lo usa solo si sin eso queda algo sin lugar. Hoy con los jueves puso 26 partidos ahí, 15 de F7 que entraban en C1 y C2 (al 53 %).
- **A5. "¿Entra todo?" con el último inicio a la hora de cierre (P48).** Sin jueves, C3 dice "Faltan 18 h", pero al programar quedan 5 o 6 sin lugar (unas 6 h). Con los jueves dice "Faltan 5,5 h" y entran los 223.

## Bloque B. Reprogramar (antes del 23/10)

- **B1. Suspender un día por lluvia: se juega el jueves.** Prueba: suspender el sábado 31/10 en la demo programada. Las propuestas pusieron de 3 a 7 partidos el jueves 29/10 o el viernes 30/10, antes del sábado suspendido (la ventana empieza el lunes de esa semana). Sin jueves, 8 de los 26 suspendidos no entran en ninguna propuesta, y cada propuesta mueve de 3 a 19 partidos ya publicados. Un jueves de 16 a 20 tiene lugar para unos 14; un sábado lleno tiene unos 25. Pedido: al suspender, preguntar dónde se juegan (por defecto el próximo jueves, 16 a 20, creado solo; se puede elegir otro día u horario); ubicar primero ahí, lo que no entra a los días siguientes moviendo lo menos posible; nunca antes de ahora; mostrar cuántos partidos ya publicados se mueven.
- **B2. "Reanudar el día".** Vuelve a abrir las franjas. Los que siguen sin lugar vuelven adonde estaban (el Cambio guarda dónde). Los ya ubicados en otro lado quedan; se muestran para decidir. Con confirmación.
- **B3. Partidos en juego al suspender.** Que no los saque del calendario. Se muestran aparte, "en juego cuando se suspendió", y la organización decide: terminarlo con ese marcador o reprogramarlo.
- **B4. "Volver a programar" con el torneo empezado.** Nunca ubicar antes de ahora. No mover partidos cuya hora ya pasó, aunque no tengan nada cargado, y avisar que les falta el resultado. Con jugados o publicados, pedir confirmación y decir cuántos se mueven. Ofrecer "Ubicar solo lo que falta", con el resto fijo. "Puede tardar hasta un minuto" no vale en producción (hasta 2).
- **B5. Intercambiar dos partidos.** En "Mover", "Intercambiar con…": los partidos de ese día y fin de semana en canchas compatibles, primero los que se pueden cambiar sin choques. Los dos cambian en un solo paso, con el verificador (avisos con confirmación; bloqueo solo si es imposible). Queda en el historial y cuenta para el contador del equipo que lo pidió.
- **B6. Reglas solo para una reprogramación.** En suspender, en un pedido de equipo y en las propuestas: turnos libres, máximo por día, orden de fechas, empezar antes o terminar después (minutos), usar mitades de cancha. Las reglas del torneo no cambian; la corrida guarda qué se aflojó.
- **B7. "¿Estás seguro?" en lo importante**, con un diálogo que diga qué va a pasar: suspender y reanudar un día, volver a programar, aplicar una propuesta, rehacer un fixture, W.O., terminar un partido, borrar un jugador, equipo o partido, cambiar reglas, encender o apagar la página pública, anonimizar.
- **B8. Calendario por club con las mismas acciones que el del día:** tocar abre la ficha; botón "Mover".
- **B9. Menor:** las pestañas de días del calendario salen solo de las franjas; un partido en un día sin franja no aparece.

## Bloque C. Día de partido (antes del 23/10)

- **C1. Dorsal repetido: aviso, no bloqueo.** La planilla lo marca ("El 10 está repetido: Juan P. y Luis R.") y deja "Guardar igual". Sacar la restricción `dorsal_unico_en_el_partido` y el NoSePuede de `guardar_planilla`. Al anotar un gol con dorsal repetido, se elige por nombre.
- **C2. CI verificado en cada partido.** En la planilla, el CI de cada jugador (interno) y una casilla "CI ✓" por partido (Convocado). "Verificar todos". El resumen dice "12 de 14". No bloquea. Si se verifica en un partido, también se marca `Jugador.verificado`.
- **C3. Foto desde la planilla con la cámara:** "Sacar foto" (`capture="environment"`) y "Elegir de la galería"; se mantiene la autorización (P66); vuelve a la planilla en el mismo jugador.
- **C4. Menores:** los docstrings de `dominio/programador/modelo.py` y `verificador.py` todavía dicen que el partido termina dentro de la franja.

## Al terminar

Verde, revisión de cierre, PROGRESO.md al día y avisarle a Sebastian qué probar en la demo: sobre todo B1, B2, B5 y C1 a C3 desde el celular.
