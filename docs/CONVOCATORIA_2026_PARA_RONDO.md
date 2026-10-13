# Convocatoria JMP CUP 2026: qué cambia en Rondo

**Fuente:** "JMP CUP 2026 · Convocatoria", 9 láminas. La pasó el organizador el 2026-10-08.
**Contexto:** es la configuración de T6.6. Viene a pedido de Sebastian. Las preguntas P55 a P59 están en `REVISION_RONDO_FASE4.md`; las nuevas siguen desde P60.

**Ojo:** la convocatoria tiene el nombre y el teléfono de un delegado, y los datos de una cuenta bancaria. No van al repo.

## Lo que confirma (no cambia nada)

- **Años de nacimiento:** año del torneo − N. Sub 17 es 2010 y 2009.
- **Niveles:** Inicial y Avanzado desde Sub 7. Sub 5 y Sub 6 tienen nivel único.
- **Planteles:** mínimo y máximo por categoría y nivel, igual que la tabla 4.1. En F11 se inscriben 22 y van 18 a cada partido.
- **Cuerpo técnico:** hasta 3 personas: entrenador, asistente y delegado.
- **Documentos:** CI o pasaporte.
- **Franjas:** viernes de 16 a 20, sábado y domingo de 8 a 16.
- **Sede:** una sola, el Centro Deportivo Urubó.
- **Pedidos:** se respetan los partidos de la ACF y no se atienden otros.

## Lo que cambia en la configuración

| Qué | Hoy en Rondo | Convocatoria 2026 |
|---|---|---|
| Fechas del torneo | Del viernes 23/10 al domingo 22/11: 5 fines de semana, 15 días | Del **sábado 24/10 al domingo 15/11**: 4 fines de semana, **11 días**. Se juegan los viernes 30/10, 6/11 y 13/11; el viernes 23 no |
| `eliminacion_desde_fin_de_semana` | 5 | Como mucho 4. P33 sigue abierta: ¿las semis pueden ir antes? |
| Modalidad de Sub 5 | F5 | **Fútbol 6** |
| Modalidad de Sub 6 | F7 | **Fútbol 6** |
| `cierre_inscripcion` (P4) | Sin fecha | **2026-10-21 a las 12:00**, hora de Bolivia. La inscripción abrió el 21/09 |
| Costo de Sub 5 a Sub 7 | Bs 1.000 | **Bs 1.100**. Sub 8 a Sub 17 sigue en Bs 1.200 |
| Día para reprogramar fechas suspendidas | Cualquiera | **Jueves.** Que "Agregar un día entre semana" proponga el jueves |
| Resultados, tablas y estadísticas | Pestaña "Posiciones" en la página pública | **Copa Fácil.** Responde P59: hay que ocultar "Posiciones" en 2026 |
| Copas | Oro, Plata y Bronce (con 10 equipos) | La convocatoria nombra solo **Oro y Plata**. Ver P62 |

**Cambio de código necesario:** `Modalidad` en `src/dominio/config.py` acepta solo `F5`, `F7`, `F8` y `F11`, y las opciones del modelo son las mismas. Hay que agregar `F6`, con su migración. La compatibilidad de Sub 5 y Sub 6 sigue por categoría, en C1A y C1B, hasta que se responda P63.

## Contradicciones y preguntas nuevas

| # | Pregunta | Por defecto mientras tanto |
|---|---|---|
| P60 | Sub 10 y Sub 11 dicen "Fútbol 7/11", pero el plantel Avanzado es de 12 a 16. Eso corresponde a F8, como en 2025; en F11 sería de 18 a 22. ¿Avanzado juega F8 o F11? | F8, como en 2025 y como indica el plantel. **Con F11 no entra** (ver Capacidad) |
| P61 | Sub 15 Femenino no aparece en 2026. ¿Se sacó? | No se juega en 2026 |
| P62 | Con 10 equipos, ¿hay Copa de Bronce? La convocatoria nombra solo Oro y Plata | Sin Bronce: con 10 equipos son 26 partidos. Si se confirma, actualizar el criterio de la sección 10 (27 → 26) |
| P63 | Fútbol 6 de Sub 5 y Sub 6: ¿se juega en media cancha 1 (C1A y C1B), como en 2023? | Sí |
| P57 | La convocatoria dice que solo el entrenador entra a la cancha a dirigir. ¿El choque de profes aplica solo al entrenador? | Solo al entrenador. Libera lugar en el calendario |
| P55 | El torneo termina el domingo 15/11. ¿Las finales van todas ese día? | Abierta: es la de la revisión |

## Capacidad con las fechas 2026

Se midió con la demo de 93 equipos, en 2 CPU y con 120 segundos de límite.

| Escenario | Resultado |
|---|---|
| **A.** Fechas 2026, eliminación en el 4.º fin de semana, Sub 10 y Sub 11 Avanzado en F8 | **Entra todo:** 223 de 223, sin choques. Más justo que antes: C1 y C2 al 78 %, C3 al 90 %, y la eliminación ocupa el 92 % del último fin de semana. El solver se queda en FEASIBLE al llegar al límite; con 5 fines de semana daba OPTIMAL en 44 s |
| **B.** Lo mismo, pero Sub 10 y Sub 11 Avanzado en F11 | **No entra:** C3 necesita 5.610 minutos y hay 4.560. Quedan 18 partidos sin ubicar |

Si en 2026 se inscriben más equipos que en 2023 (H4 estimaba 117), el margen del escenario A puede no alcanzar. Por eso P33 (adelantar la eliminación) y P13 (más canchas, o partir C2 o C3) pasan a ser urgentes.

En el escenario A siguen los dos problemas de la revisión:
- **Llaves encadenadas sin descanso:**
  - Sub 14 Avanzado: semi el viernes 13/11 a las 16:00 y final a las 17:10, las dos en C3.
  - Sub 15 Avanzado: semi 2 el sábado 14/11 a las 10:20 y final a las 11:30, las dos en C3.
- **Esperas de los profes:** la mediana es de 98 minutos, con 8 esperas de más de 2 horas y ningún par seguido en la misma cancha.

## Orden sugerido

1. Puntos 1 y 2 de `REVISION_RONDO_FASE4.md`: descanso en la eliminación y profes seguidos en la misma cancha.
2. Agregar F6 y cargar en `jmp_cup_2026.json` la configuración de arriba, con P60 a P63 en su valor por defecto. Anotar las respuestas en PROGRESO.md.
3. Ocultar "Posiciones" en la página pública.
4. Volver a programar la demo con las fechas nuevas y reportar capacidad, tiempo y estado del solver. Medirlo también con la CPU del plan que elija Sebastian.
5. T6.5, producción, cuando Sebastian elija el hosting.
6. T6.7, carga de listas. Las listas llegan hasta el miércoles 21/10 a las 12:00 y el torneo empieza el sábado 24/10. Si alcanza el tiempo, sumar "pegar filas desde Excel" antes del 21.
