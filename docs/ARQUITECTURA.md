# Arquitectura y plan por fases

> **Aprobada por Sebastian el 2026-10-06.** Decisiones tomadas con Sebastian el 2026-10-06: Django + HTMX, Cloud Run y Neon en São Paulo, la prueba de 6.4 separada por tipo de choque y uso real en el torneo 2026. El análisis previo y las preguntas para el organizador están en [PROGRESO.md](PROGRESO.md).

## 1. En una página

- **Es una aplicación web.** Está en internet y se abre desde el navegador del celular o de la PC, con usuario y contraseña. Se puede instalar en la pantalla de inicio del celular y se abre como una app (PWA). No pasa por Play Store ni App Store.
- **Un solo servicio Django.** Renderiza las pantallas en el servidor y usa HTMX para las partes dinámicas. Corre como contenedor en Cloud Run, con la base en Neon. Los dos están en São Paulo.
- **Un núcleo de dominio en Python puro y tipado**, sin Django: validaciones de inscripción, fixture, verificador, capacidad y programador. Ahí van casi todos los tests y el tipado estricto.
- **Las reglas son datos.** La configuración del torneo vive en la base y se carga desde un JSON. Los formatos de 4.5 son un archivo de datos. Cada regla configurable dice de dónde sale: una sección del reglamento o una pregunta P.
- **El verificador es la definición ejecutable de las restricciones duras.** Todo calendario pasa por él: el que arma el solver, el de cada propuesta y los cambios hechos a mano.

## 2. Vista general

```
Celular o PC (organizador, mesa de control)
        │  HTTPS, siempre con login
        ▼
Cloud Run · southamerica-east1 · un contenedor (1 o 2 vCPU, según la prueba del día 1)
  Django 6.1 + Gunicorn
  ├── web: vistas, formularios, plantillas, HTMX, admin
  ├── servicios: arman las entradas del dominio desde la base y guardan los resultados
  └── dominio (Python puro)
        ├── inscripción: validaciones y normalización de CI
        ├── fixture: formatos como datos
        ├── verificador y capacidad
        └── programador: OR-Tools CP-SAT
        │  TLS
        ▼
Neon Postgres · aws-sa-east-1
  ├── rama main  → producción (datos reales)
  └── rama demo  → datos inventados
```

## 3. Stack

| Pieza | Elección | Por qué |
|---|---|---|
| Lenguaje | Python 3.14 con `uv` | Hay wheels de 3.14 para OR-Tools, psycopg, pydantic, numpy y pandas. `uv` maneja la versión y el lockfile |
| Web | Django 6.1 | Trae login, admin, formularios, CSRF y migraciones. Desde 6.0 tiene parciales de plantilla, útiles con HTMX |
| Interactividad | HTMX con `django-htmx` | Validación en vivo, propuestas y espera del solver sin armar una SPA |
| Estilos | Pico CSS y CSS propio | Se ve bien en el celular sin esfuerzo. La grilla del calendario lleva CSS propio |
| Solver | OR-Tools CP-SAT 9.15 | Nativo en Python, con límite de tiempo y la mejor solución encontrada |
| Configuración | Pydantic v2 | Valida la configuración y las reglas al cargarlas y al editarlas |
| Base | PostgreSQL en Neon (plan gratuito) | Se suspende sin uso y despierta sola. Las ramas separan la demo de la producción |
| Hosting | Cloud Run con facturación por request | CPU real para el solver, requests de hasta 60 minutos y capa gratuita |
| Archivos estáticos | WhiteNoise | Sin CDN ni bucket |
| PNG | `modern-screenshot` en el navegador y Web Share API | En el celular se comparte directo a WhatsApp; en la PC se descarga |
| Instalación en el celular | PWA: manifest e ícono, sin modo sin conexión | Se abre desde la pantalla de inicio como una app, y los datos personales no quedan guardados en el teléfono |
| Calidad | pytest, pytest-django, Hypothesis, mypy, django-stubs y ruff | mypy estricto en `dominio/`; tipado y tests como querías practicar |

## 4. Mapa de módulos

| Módulo | Qué hace | Depende de |
|---|---|---|
| `plataforma` | Repo, proyecto Django, login, plantilla base para el celular, Neon, Cloud Run y herramientas de calidad | — |
| `configuracion` | Torneo, categoría-nivel, canchas y mitades, compatibilidad, franjas, reglas y formatos; carga de la configuración 2026 | plataforma |
| `inscripcion` | Clubes con alias, equipos, personas con CI normalizado, jugadores y cuerpo técnico; validaciones de 4.2; equipos que no pueden jugar a la vez | configuracion |
| `datos-demo` | Torneo inventado del tamaño de 2023, con profes y jugadores compartidos como en 6.4 | inscripcion |
| `fixture` | Series, cruces por formato y llaves con participantes "por definir" | configuracion, inscripcion |
| `verificador` | Choques duros de cualquier calendario y cálculo de capacidad | configuracion |
| `programador` | Programación completa con CP-SAT, límite de tiempo y partidos sin ubicar con su motivo | fixture, verificador |
| `reprogramacion` | Bloqueos de la ACF, suspensiones, franjas entre semana, 2 o 3 propuestas, cambios a mano verificados e historial | programador |
| `calendario` | Vistas por día y cancha, por categoría y por club; PNG sin datos personales | fixture |

**Orden:** plataforma → configuracion → inscripcion → datos-demo → fixture y verificador (en paralelo) → programador → reprogramacion → calendario.

El verificador no necesita el fixture, porque recibe cualquier calendario. Por eso se puede probar con el calendario 2023 antes de que exista el programador.

## 5. Estructura del repo

```
Rondo/
├── pyproject.toml          # dependencias (uv), ruff, mypy y pytest
├── Dockerfile
├── compose.yaml            # Postgres local para desarrollo y tests
├── manage.py
├── src/
│   ├── rondo/              # proyecto Django: settings, urls, login y plantilla base
│   ├── torneo/             # la única app Django
│   │   ├── models/         # configuracion, inscripcion, competencia, historial
│   │   ├── views/          # inscripcion, fixture, programacion, calendario
│   │   ├── forms/
│   │   ├── servicios/      # base ↔ dominio: arman entradas y guardan resultados
│   │   ├── templates/
│   │   ├── admin.py
│   │   └── management/commands/    # cargar_config, generar_demo
│   └── dominio/            # Python puro: no importa Django (lo comprueba un test)
│       ├── config.py       # modelos Pydantic de la configuración y las reglas
│       ├── documentos.py   # normalización de CI
│       ├── inscripcion.py
│       ├── fixture/
│       ├── verificador.py
│       ├── capacidad.py
│       └── programador/
├── datos/config/
│   ├── jmp_cup_2026.json   # sección 4 y valores por defecto de la sección 9
│   └── formatos.json       # tabla 4.5
├── tests/
│   ├── dominio/
│   ├── torneo/
│   └── casos/2023/         # calendario 6.3 y profes anónimos de 6.4
├── docs/
└── tasks/                  # plan y lista de tareas
```

**Una sola app Django.** Todos los modelos dependen entre sí (torneo → categoría-nivel → equipo → partido); repartirlos en varias apps solo suma dependencias cruzadas entre migraciones. Los límites entre módulos se mantienen en `dominio/` y en cómo se reparten los archivos.

## 6. Modelo de datos

| Modelo | Campos principales | Notas |
|---|---|---|
| Torneo | nombre, edición, año, inicio, fin, zona horaria, reglas (JSON validado) | Una fila por edición |
| CategoriaNivel | torneo, categoría (Sub N), edad, años de nacimiento, género, nivel, modalidad, mínimo y máximo de jugadores, minutos por tiempo, convocados | La unidad de competencia, por ejemplo "Sub 9 Inicial" |
| Cancha | torneo, código, nombre, padre | C1A y C1B tienen como padre a C1 |
| Compatibilidad | categoría-nivel ↔ canchas | Se genera desde la regla por categoría o por modalidad; editable |
| Franja | torneo, inicio, fin, tipo (regular o entre semana) | Fechas concretas, no días de la semana |
| Club | nombre, alias | Catálogo: el club se elige, no se escribe |
| Equipo | club, categoría-nivel, nombre visible, colores 1 y 2, pagado | |
| Persona | tipo y número de documento, CI normalizado, nombres, apellidos, fecha de nacimiento | **La única tabla con datos personales** |
| Jugador | persona, equipo, dorsal, verificado | Dorsal único dentro del equipo |
| Profe | persona, equipo, rol | Hasta 3 por equipo (configurable) |
| Serie | categoría-nivel, nombre, equipos | |
| Partido | categoría-nivel, fase, copa, número de fecha, serie, local y visitante (o una referencia como "1.º A"), estado, cancha, inicio, fijado | La duración y el turno se calculan desde la categoría-nivel |
| Bloqueo | equipos, inicio, fin, motivo | Partidos de la ACF u otros |
| Corrida | tipo (programar o reprogramar), parámetros, estado, resultado, duración | Cada ejecución del solver |
| Cambio | partido, antes, después, usuario, fecha, motivo, corrida | Historial de reprogramaciones |

- **Duración calculada.** Turno = 2 × minutos por tiempo + descanso + cambio. Da los 40, 50, 60 y 70 minutos de 4.4 sin escribirlos en ningún lado.
- **Mitades como canchas hijas.** Un partido en C1 ocupa C1A y C1B; uno en C1A, solo esa mitad. Si se confirma que C2 y C3 también se parten (P13), se agregan hijas sin tocar el código.
- **Persona concentra los datos personales.** Jugador y Profe la referencian, y así se detecta que alguien está en dos equipos. El CI normalizado es único cuando existe; puede faltar mientras el documento esté pendiente (P39).
- **Los equipos que no pueden jugar a la vez no se guardan:** se calculan desde Persona cuando hacen falta. Al dominio le llegan identificadores de equipo y el motivo (profe o jugador), nunca nombres ni CI.

## 7. Configuración como datos

| Qué | Dónde | Cómo se edita |
|---|---|---|
| Categorías, niveles, modalidades, topes y minutos | Tabla CategoriaNivel | Admin |
| Canchas, mitades y compatibilidad | Tablas Cancha y Compatibilidad | Admin |
| Franjas, incluidas las de entre semana | Tabla Franja | Pantalla de programación |
| Reglas sueltas (P6, P7, P9, P17, P18…) | `Torneo.reglas`, JSON validado con Pydantic | Admin, con validación |
| Formatos por cantidad de equipos | `datos/config/formatos.json` | Archivo versionado en el repo |
| Identidad del organizador: nombre, logo y colores del PNG | Configuración del sitio | Admin |

El JSON de 4.1 se usa una sola vez para crear el torneo 2026 (`manage.py cargar_config`). A partir de ahí, la verdad está en la base.

Las reglas sueltas son un modelo Pydantic. Cada campo dice de dónde sale:

```python
class Reglas(BaseModel):
    jugar_en_categoria_mayor: bool = True                     # P6
    jugador_en_dos_equipos: PoliticaJugador = "mismo_club_otra_categoria"  # P7
    dorsal_obligatorio: MomentoDorsal = "antes_del_primer_partido"         # P9
    turnos_libres_mismo_dia: int = 1                          # P17
    max_partidos_por_dia: int = 2                             # P47
    profe_minutos_cambio_de_cancha: int = 10                  # P18 y P35
    orden_de_fechas: Literal["dura", "blanda"] = "dura"       # P19
    eliminacion_desde_fin_de_semana: int = 5                  # P33
    marcador_wo: tuple[int, int] = (3, 0)                     # P23
```

Los formatos describen las series y las llaves con referencias. Este es el de 6 equipos:

```json
"6": {
  "series": [3, 3],
  "fase_de_grupos": "series_cruzadas",
  "llaves": [
    {"id": "O-S1", "copa": "oro",   "local": "1A",     "visitante": "2A"},
    {"id": "O-S2", "copa": "oro",   "local": "1B",     "visitante": "2B"},
    {"id": "O-F",  "copa": "oro",   "local": "G:O-S1", "visitante": "G:O-S2"},
    {"id": "P-S",  "copa": "plata", "local": "3A",     "visitante": "3B"},
    {"id": "P-F",  "copa": "plata", "local": "G:P-S",  "visitante": "MP:O-S1,O-S2"}
  ]
}
```

`1A` es el 1.º de la serie A; `G:` es el ganador de un partido, `P:` el perdedor y `MP:` el mejor perdedor (P26). Las dependencias entre partidos salen de las referencias: la final de Oro va después de las dos semis. Cambiar un formato no requiere tocar el código.

## 8. Programador

**Ejecución.** Cloud Run da CPU solo mientras hay un request abierto. Por eso el solver corre dentro del request, con un límite de tiempo configurable (por ejemplo, 90 segundos), mientras la pantalla muestra que está trabajando. El resultado se guarda en una Corrida antes de responder: si el celular pierde la conexión, el resultado queda igual. Un bloqueo en la base impide lanzar dos programaciones a la vez.

**Capacidad antes de programar.** Se muestran las horas pedidas contra las horas disponibles, por grupo de canchas y por fase (grupos y eliminación). Se calcula con un flujo máximo que respeta la compatibilidad: si ahí no alcanza, seguro no entra.

**Modelo CP-SAT**, en pasos de 5 minutos:

- Cada partido tiene un inicio y elige una cancha compatible. El inicio ya excluye lo que cae fuera de las franjas y en los bloqueos ACF de sus equipos.
- **Canchas:** no se pisan. Cada partido ocupa, durante su turno, cada cancha física que usa; C1 entera ocupa C1A y C1B.
- **Equipos:** no se pisan, dejan un turno libre si juegan el mismo día (P17) y no pasan del máximo por día (P47).
- **Profes y jugadores compartidos:** sus equipos no se pisan. Si es un profe y cambia de cancha, hace falta el margen de P35.
- **Orden:** las fechas de cada equipo van en orden (P19), la eliminación va después de los grupos y la final después de las semis.
- **Fijos:** los partidos jugados o fijados a mano no se mueven.
- **Objetivo:** primero ubicar todos los partidos. Después, agrupar por club (P20), dejar pocos huecos y repartir la carga entre fines de semana, con pesos configurables.

**Partidos que no entran.** Cada partido puede quedar sin ubicar, con una penalidad enorme. Así el solver siempre devuelve el mejor calendario posible. Para cada partido sin ubicar, el verificador revisa los turnos libres compatibles y resume por qué no sirve ninguno: falta de cancha, choque de equipo, profe, jugador o bloqueo.

**Reprogramación.** Ante un bloqueo nuevo o una suspensión, se resuelve el mismo modelo partiendo del calendario actual, con otro objetivo: mover la menor cantidad de partidos, afectar a la menor cantidad de equipos y preferir el mismo fin de semana. Solo se mueven partidos cercanos (ese fin de semana y el siguiente), para que sea rápido. Para obtener 2 o 3 propuestas distintas, después de cada solución se prohíbe repetir el mismo conjunto de movimientos y se resuelve otra vez. Cada propuesta pasa por el verificador y se muestra como una lista de movimientos. Al aplicarla, queda en el historial.

## 9. Calendario y PNG

- **Vistas:** por día y cancha (C1 con sus mitades), por categoría y por club.
- **Exportación:** una plantilla aparte, de ancho fijo (1080 px), que solo recibe equipos, canchas y horarios. El navegador la convierte en PNG; en el celular se comparte directo a WhatsApp y en la PC se descarga.
- **Plan B:** si la captura falla en algún celular, se dibuja el PNG en el servidor con Pillow.
- **Diseño:** el organizador va a pasar uno propio (P32). Con HTML y CSS es fácil adaptarlo.

## 10. Seguridad y datos personales

La app se va a usar en 2026 con datos reales de menores:

- **Todo con login.** Se usa `LoginRequiredMiddleware` de Django, y cualquier excepción se declara a mano. Usuarios: el organizador y la mesa de control. Los roles más finos quedan para después.
- **Demo y producción separadas.** Son dos servicios de Cloud Run y dos ramas de Neon. Los datos reales nunca tocan la demo.
- **Nada personal en los logs.** No se vuelcan formularios ni requests, los formularios con datos personales se marcan como sensibles y `DEBUG` va apagado en la nube.
- **Las vistas de calendario no reciben datos personales.** Un test renderiza la exportación con datos inventados y comprueba que no aparecen nombres ni CI.
- **Las listas reales no entran al repo.** Lo impiden el `.gitignore` y un chequeo antes de cada commit que rechaza planillas, archivos de Word y PDF.
- **Backups (fase 6):** copia diaria con `pg_dump` a un bucket privado de Google Cloud, además de la restauración de Neon.

### Cuentas, costos y traspaso

La idea es venderle la app a JMP. Por eso todo se arma en las cuentas de Sebastian, pero de forma que se pueda traspasar sin volver a desplegar:

- **Google Cloud:** un proyecto `rondo` dedicado solo a esta app, con la tarjeta de Sebastian. Para traspasarlo, JMP crea su propia cuenta de facturación, Sebastian agrega su cuenta de Google como Owner del proyecto y le cambia la facturación. El servicio y la URL siguen iguales.
- **Neon:** el proyecto no se conecta a las integraciones de GitHub ni de Vercel, porque con ellas activas no se puede traspasar. Al cederlo a la cuenta de JMP, la cadena de conexión no cambia. Si algo falla, se copia la base con `pg_dump`, que es chica.
- **Despliegue reproducible:** los comandos para desplegar y configurar la nube van en el repo. Con eso se puede montar todo en otra cuenta en minutos.
- **Otros clientes:** cada organización que compre la app tiene su propia instalación, con su proyecto en Google Cloud, su base en Neon y su facturación, y el mismo código. Por eso la base no separa clientes, y nada propio de JMP va en el código: nombre, logo y colores van en la configuración. En Neon, cada cliente es un proyecto aparte (`rondo-jmp`, `rondo-<cliente>`).
- **Costos:** no hay crédito de prueba, porque Sebastian ya usó Google Cloud. Pero la capa gratuita vale igual para las cuentas pagas, así que el gasto esperado es 0 o unos centavos al mes. El tope aceptado es de unos 5 USD.
- **Protecciones:** como máximo 1 instancia y alertas de presupuesto por correo a los 1, 3 y 5 USD. Las alertas avisan, pero no cortan el gasto. No se pone un corte automático porque apagaría la app en pleno torneo.

## 11. Tests

| Qué | Cómo |
|---|---|
| Fixture | Propiedades con Hypothesis para 2 a 10 equipos: cada par se enfrenta una vez (dos en ida y vuelta), nadie juega dos veces en la misma fecha y cada formato da su cantidad de partidos (8, 10, 12, 14, 17, 18, 22 y 27) |
| Verificador | Caso 2023 separado por tipo: 2 choques de personas (River Plate), 3 de cancha y, con las canchas de 2023, ninguno de compatibilidad. Además, casos chicos para cada tipo de choque |
| Programador | Instancias chicas y rápidas, y un caso del tamaño de 2023 marcado como lento. Todo calendario del solver tiene que pasar el verificador con 0 choques duros |
| Inscripción | Tablas de casos para CI y edades; formularios con pytest-django |
| Arquitectura | `dominio/` no importa Django |
| Datos personales | La exportación no contiene datos de Persona |

Los tests usan un Postgres local en Docker.

## 12. Fases

Se cuentan en días de trabajo, no en fechas. Cada fase termina con los tests en verde, una revisión con `code-review-and-quality` y tu visto bueno antes de pasar a la siguiente.

| Fase | Cuándo | Qué | Lista cuando |
|---|---|---|---|
| 0. Cimientos | Día 1, mañana | Repo, Django con login, Postgres local, Neon y deploy en Cloud Run. Tres pruebas de riesgo: OR-Tools resuelve un modelo de juguete en Cloud Run, el PNG se genera y se comparte desde tu celular, y el deploy se repite con un comando | Entras con login a la URL de Cloud Run desde el celular |
| 1. Configuración | Día 1, tarde | Modelos, reglas con Pydantic, carga de la configuración 2026 y admin | El torneo 2026 existe con todas sus categorías, canchas y franjas, y se edita en el admin |
| 2. Inscripción | Día 2 | CI, validaciones de 4.2, formularios para el celular, avisos y generador de datos de demo | Pasan los criterios de inscripción de la sección 10 y hay un torneo de demo de unos 80 equipos |
| 3. Fixture y verificador | Día 3 | Formatos como datos, todos contra todos, series cruzadas, llaves y sorteo de series. Verificador y capacidad | Cada formato da de 8 a 27 partidos según corresponda, pasa la prueba 2023 por tipo y la capacidad se ve en pantalla |
| 4. Programador | Día 4 | Modelo CP-SAT, corrida dentro del request, partidos sin ubicar con motivo y una vista básica por día y cancha | El torneo de demo queda programado con 0 choques duros, o la app lista lo que no entra y por qué |
| 5. Reprogramación y calendario | Día 5 | Bloqueos, suspensiones, propuestas, cambio manual verificado e historial. Vistas, PNG, instalación en el celular y ensayo de la demo | Un bloqueo ACF da 2 o 3 propuestas ordenadas y el PNG de un día se comparte sin datos personales |
| Demo | — | Mostrarla al organizador | Responde las preguntas prioritarias: P13, P33, P35, P44, P46 y P50 |
| 6. Producción 2026 | Después de la demo, antes del cierre de inscripción | Configuración con las respuestas, backups, usuarios, revisión de seguridad, carga de las listas reales y asignación a mano de los cruces de eliminación (P50) | El fixture y el calendario 2026 están publicados |

**Si el tiempo no alcanza,** se recorta en este orden: las vistas por club y por categoría, la tercera propuesta, las franjas entre semana y el objetivo de agrupar por club.

**Fechas tentativas.** Hoy es martes 6 de octubre y el torneo empieza el viernes 23. Si los 5 días de trabajo son seguidos, la demo sería alrededor del lunes 12 y quedaría una semana para la fase 6. El cierre de inscripción 2026 (P4) marca cuándo tiene que estar lista la carga de listas reales.

## 13. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| El solver tarda o no encuentra calendario, porque la capacidad está justa (H4) | Alto | Capacidad visible antes de programar, partidos sin ubicar en vez de "sin solución", límite de tiempo y prueba en Cloud Run el día 1 |
| Poco tiempo entre la demo y el 23 de octubre | Alto | La fase 6 es chica y está definida desde ahora. Resultados y tabla quedan afuera (P50) |
| Cargar unos 1.700 jugadores a mano | Medio | Formulario rápido en el celular. Si no alcanza, pegar filas copiadas de Excel (P51) |
| La captura PNG falla en algún celular | Medio | Se prueba el día 1, con Pillow como plan B |
| Fuga de datos de menores | Alto | Login en todo, demo y producción separadas, tests de las vistas y nada personal en los logs |
| Reglas sin responder (P1 a P51) | Medio | Todo es configurable. En la demo se priorizan las que cambian la programación |
| Costos en Google Cloud, sin crédito de prueba | Bajo | Capa gratuita, facturación por request, máximo 1 instancia y alertas a los 1, 3 y 5 USD |

## 14. Siguiente paso

Si apruebas esta propuesta:

1. Escribo `SPEC.md` (objetivo, comandos, estructura, estilo de código, tests, límites y criterios de éxito) con un catálogo de reglas: cada una con su origen, su clave de configuración, su valor por defecto y su test.
2. Armo `tasks/plan.md` y `tasks/todo.md`, con las fases 0 y 1 en detalle. Las siguientes se detallan al llegar a ellas.
