# Guion de la demo para el organizador

Unos 20 minutos, desde el celular. Todo lo que se ve es inventado: los jugadores, sus CI y sus fechas los genera la app. Ningún dato real de menores.

## Antes de la demo (el día anterior)

En la demo de Render gratis (0,1 CPU), el programador tarda mucho más que en una PC (H6, R44). Conviene dejar todo programado antes.

1. Cargar la demo contra la rama `demo` de Neon, desde tu máquina (DESPLIEGUE.md, paso 3c): `generar_demo --soy-la-demo`. Arma 93 equipos inventados con la forma de 2023.
2. Entrar como organización y, en Inicio, tocar **Generar los fixtures que faltan**.
3. Ir a **Programar partidos** y tocar **Programar los partidos**. En una PC, los 223 partidos se ubican en unos 30 s. Si en Render no termina en el límite, sube `RONDO_PROGRAMADOR_SEGUNDOS` (gunicorn corta a los 300 s) o programa desde tu máquina con la cadena de Neon.
4. Comprobar que el resultado diga "223 de 223 partidos programados, sin choques".
5. Instalar la app en el celular: en Chrome, menú → "Instalar app".

## El recorrido

| # | Qué mostrar | Dónde | Qué decir |
|---|---|---|---|
| 1 | El inicio con el torneo y lo pendiente | Inicio | La app dice qué falta, no un porcentaje |
| 2 | Crear el torneo con el asistente | Más → Crear un torneo (solo mirar los pasos; el torneo ya existe) | Viene con el reglamento 2026; se destilda lo que no va |
| 3 | Reglas con interruptores | Inicio → Reglas del torneo | Cada regla dice de qué pregunta sale (P6, P7…) |
| 4 | Un equipo y su lista | Torneo → Sub 11 Avanzado → River Plate | Avisos al cargar: un jugador que ya está en otro equipo del club, uno sin CI |
| 5 | Agregar un jugador y ver el aviso en vivo | En la ficha, "Agregar jugador", escribir el CI de alguien que ya juega en otra categoría | El aviso aparece al salir del campo, antes de guardar |
| 6 | El fixture de una categoría | Torneo → Sub 6 → Fixture | Series que separan clubes; los del mismo club se cruzan en la fecha 1 |
| 7 | ¿Entra todo? | Inicio → Programar partidos | La eliminación entra justo en el último fin de semana (pregunta P33) |
| 8 | El calendario de un día | Calendario | Cancha por cancha, sin choques: lo revisó el verificador |
| 9 | **Un partido de la ACF** | Inicio → Cargar un partido de la ACF | Elegir un equipo con partido el sábado, cargar el horario y ver el choque al instante |
| 10 | **Las propuestas** | En el bloqueo, "Ver propuestas" | 2 o 3 opciones, de menos a más cambios. Aplicar la recomendada |
| 11 | El historial | Más → Cambios recientes | Quién cambió qué y cuándo |
| 12 | Suspender un día por lluvia | Calendario → un día → Suspender este día | Los partidos quedan sin programar y la app propone dónde ubicarlos |
| 13 | **La imagen para WhatsApp** | Calendario → un día → Compartir el día | Una imagen por cancha, con el diseño de 2025, sin datos de jugadores |
| 14 | La página pública | Más → JMP CUP 2026 → ver la página pública | Lo que ven las familias, sin login: partidos, día y hora |
| 15 | Los roles | Entrar con un usuario de mesa de control | Carga listas y verifica, pero no configura ni programa |

## Preguntas para el organizador

Las prioritarias (ARQUITECTURA 12). La app ya tiene un valor por defecto para cada una, que se cambia en Reglas o en la configuración.

| # | Pregunta | Hoy la app hace |
|---|---|---|
| P13 | ¿Qué canchas hay en 2026, de qué tamaño, y cuáles se parten (la 2 y la 3 aparecían como 2A, 2B, 3A y 3B)? | Las de 2023: C1 (con mitades C1A y C1B), C2 y C3 |
| P33 | La eliminación entra justo en el último fin de semana (con más equipos, no entraría). ¿Se pueden adelantar las semis al penúltimo? | Empieza el fin de semana 5; se cambia en Reglas |
| P35 | ¿Cuánto tiempo necesita un profe para cambiar de cancha? | 10 minutos |
| P44 | Si un equipo se inscribe tarde, ¿se puede rehacer el fixture de su categoría mientras no haya partidos jugados? | Sí, y se reprograma solo esa categoría |
| P46 | Todos Santos cae el domingo 1 de noviembre y el lunes 2 es feriado. ¿Se juega ese fin de semana? ¿Se usa el lunes para reprogramar? | Se juega normal; el lunes se usa solo si se agrega como día entre semana |
| P50 | ¿Cómo se definen los cruces de la eliminación (quién es "1.º A")? | El organizador calcula las posiciones y asigna a mano los participantes |

Después de la demo, las respuestas se anotan en PROGRESO.md y se ajusta la configuración (fase 6).
