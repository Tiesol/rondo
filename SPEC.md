# Spec: app de la JMP CUP (Rondo)

> **Estado: borrador, pendiente de aprobación.** Se apoya en [docs/CONTEXTO_JMP_CUP.md](docs/CONTEXTO_JMP_CUP.md) (reglas del negocio), [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) (aprobada el 2026-10-06) y [docs/PROGRESO.md](docs/PROGRESO.md) (decisiones, supuestos y preguntas abiertas).

## Objetivo

Una app web para la organización de la JMP CUP: el organizador y la mesa de control la usan desde el celular o la PC. Sirve para:

1. inscribir equipos con sus listas;
2. armar el fixture según el reglamento;
3. programar los partidos en canchas y horarios sin choques;
4. proponer reprogramaciones cuando algo cambia;
5. compartir el calendario como imagen por WhatsApp.

**Usuarios:** el organizador y la mesa de control. Los clubes no usan la app.

**Hitos:**

- **Demo:** en unos 5 días de trabajo, con datos inventados. Sirve para que el organizador la apruebe y responda las preguntas.
- **Uso real:** en el torneo 2026, que empieza el viernes 23 de octubre.

**Éxito:** el organizador deja de armar el calendario a mano en Excel, y ningún calendario publicado tiene choques duros.

## Stack

- **Lenguaje y web:** Python 3.14 (con `uv`), Django 6.1, HTMX con `django-htmx`, Pico CSS y WhiteNoise.
- **Configuración y solver:** Pydantic v2 para la configuración; OR-Tools 9.15 (CP-SAT) para la programación.
- **Base de datos:** PostgreSQL 18 en Neon, proyecto `rondo-jmp` en São Paulo. En desarrollo, Postgres 18 en Docker.
- **Hosting:** Cloud Run en `southamerica-east1`, con facturación por request.
- **Tests y calidad:** pytest, pytest-django, Hypothesis, mypy, django-stubs y ruff.
- **Navegador:** `modern-screenshot` para generar el PNG y Web Share API para compartirlo. La app es instalable en el celular (PWA), sin modo sin conexión.

## Comandos

Los comandos se terminan de fijar en la fase 0; esta es la forma prevista:

```bash
uv sync                                      # instalar dependencias
docker compose up -d db                      # Postgres local
uv run python manage.py migrate
uv run python manage.py cargar_config datos/config/jmp_cup_2026.json
uv run python manage.py generar_demo         # torneo inventado del tamaño de 2023
uv run python manage.py runserver

uv run pytest -m "not lento"                 # tests rápidos (antes de cada commit)
uv run pytest                                # todos, incluido el programador con el caso grande
uv run mypy                                  # estricto en src/dominio
uv run ruff check . && uv run ruff format --check .

./scripts/desplegar.sh demo                  # Cloud Run + rama demo de Neon
./scripts/desplegar.sh produccion            # pide confirmación
```

## Estructura

Es la de la sección 5 de [ARQUITECTURA.md](docs/ARQUITECTURA.md):

- **`src/dominio/`:** Python puro, sin Django.
- **`src/torneo/`:** la única app Django.
- **`src/rondo/`:** el proyecto Django.
- **`datos/config/`:** la configuración inicial y los formatos.
- **`tests/`:** los tests, con la misma forma que `src/`.
- **`docs/`:** el contexto, la arquitectura y el progreso.
- **`tasks/`:** el plan y las tareas.

## Estilo de código

- **Idioma:** el dominio se nombra en español, con los términos del glosario y sin tildes en los identificadores (`categoria_nivel`, `minutos_turno`). Lo propio del framework sigue sus nombres en inglés (`views`, `forms`).
- **Tipado:** completo en `dominio/` (mypy estricto). Se usan dataclasses inmutables para los datos y funciones puras para la lógica. Las funciones reciben todo lo que necesitan; no hay estado global.
- **Reglas:** ninguna regla del reglamento queda escrita en el código. Llega como dato, y el comentario dice de dónde sale (sección o P#).
- **Comentarios:** en español, solo cuando explican el porqué.
- **Formato:** `ruff format`, con líneas de 100 caracteres.

```python
@dataclass(frozen=True, slots=True)
class PartidoProgramado:
    id: int
    equipos: tuple[int | None, int | None]  # None = "por definir" en eliminación
    cancha: str
    inicio: datetime
    minutos_partido: int
    minutos_turno: int


def se_pisan(a: PartidoProgramado, b: PartidoProgramado) -> bool:
    """Los partidos se superponen en el tiempo (sin contar el cambio de 5 minutos)."""
    fin_a = a.inicio + timedelta(minutes=a.minutos_partido)
    fin_b = b.inicio + timedelta(minutes=b.minutos_partido)
    return a.inicio < fin_b and b.inicio < fin_a
```

## Tests

- **TDD en el dominio:** primero el test que falla y después el código. Las reglas del catálogo (más abajo) tienen al menos un test cada una, que lleva el ID de la regla en el nombre o en el docstring.
- **Propiedades con Hypothesis:** fixture de 2 a 10 equipos, con clubes al azar.
- **Casos de referencia en `tests/casos/2023/`:** el calendario de 6.3 y los profes anónimos de 6.4, sin datos personales.
- **Web:** pytest-django para formularios, vistas y permisos (todo pide login).
- **Lentos:** los tests que tardan más de 5 segundos llevan la marca `lento` y no bloquean el commit.
- **Cobertura:** sin un número mínimo. Lo que se exige es que cada regla del catálogo tenga su test.

## Límites

**Siempre:**

- Correr los tests rápidos, mypy y ruff antes de cada commit.
- Tomar las reglas de la configuración.
- Pasar todo calendario por el verificador antes de guardarlo.
- Mantener `docs/PROGRESO.md` al día.
- Usar solo datos inventados en tests y demo.

**Preguntar antes:**

- Agregar dependencias.
- Cambiar un valor por defecto del reglamento.
- Cambiar el modelo de datos cuando ya haya datos reales.
- Desplegar a producción.
- Tocar la configuración de la nube o cualquier cosa que tenga costo.
- Crear repos remotos.

**Nunca:**

- Subir al repo listas reales, archivos `.env` o credenciales.
- Pedir o mostrar credenciales en el chat.
- Escribir reglas en el código.
- Abrir acceso sin login.
- Mostrar o registrar datos personales fuera de las pantallas de inscripción.
- Borrar o saltear tests que fallan sin acordarlo.
- Inventar una regla: si falta, se deja configurable y se anota como pregunta.

## Criterios de éxito de la demo

Son los de la sección 10 del contexto, con el ajuste de H1:

1. **Fixture:** de 3 a 10 equipos da 8, 10, 12, 14, 17, 18, 22 y 27 partidos. En la fase de grupos no se repite ningún cruce, nadie juega dos veces en la misma fecha y cada equipo juega lo que dice su formato.
2. **Inscripción:**
   - Rechaza siempre a un jugador mayor que su categoría y acepta a uno menor (P6).
   - No deja pasar del máximo y avisa por debajo del mínimo.
   - Avisa cuando un CI ya está en otro equipo.
   - Limita el cuerpo técnico a 3 personas con rol.
3. **Verificador**, sobre el calendario de 6.3 con los profes y jugadores de 6.4:
   - exactamente 2 choques de personas, los de River Plate, contados por par de partidos;
   - exactamente 3 choques de cancha: C1 con C1A y con C1B el domingo a las 9:20, y C3 el domingo a las 8:50;
   - ningún choque de compatibilidad con las canchas de 2023 (6.1).
4. **Programación:** el torneo de demo (unos 80 equipos) queda con 0 choques duros según el verificador. Lo que no entra se informa con su motivo, y la capacidad se ve antes de programar.
5. **Reprogramación:** un bloqueo ACF sobre un partido programado da 2 o 3 propuestas válidas, ordenadas por cuántos partidos mueven.
6. **Exportación:** el calendario de un día se descarga o se comparte como PNG, sin datos personales (lo comprueba un test).
7. **Acceso:** toda pantalla pide login, y la app funciona en el celular.

## Catálogo de reglas

Cada regla tiene un ID estable. La columna "Clave" es dónde vive en la configuración: CN = tabla CategoriaNivel, R = `Torneo.reglas` y F = `formatos.json`.

### Categorías y partidos

| ID | Regla | Origen | Clave | Por defecto |
|---|---|---|---|---|
| CAT-01 | Año de nacimiento = año del torneo − N. Sub 17 abarca dos años | 4.1 | CN `edad`, `anios_nacimiento` | Tabla 4.1 |
| CAT-02 | Modalidad, mínimo y máximo de jugadores, minutos por tiempo y convocados por nivel | 4.1, P14, P15 | CN | Tabla 4.1 |
| CAT-03 | Turno = 2 × minutos por tiempo + descanso + cambio | 4.4, P16 | `partido.descanso_min`, `cambio_entre_partidos_min` | 5 y 5 |
| CAT-04 | La compatibilidad por categoría manda sobre la de modalidad | Supuesto | Compatibilidad | Canchas de 2023 |

### Inscripción

| ID | Regla | Origen | Clave | Por defecto |
|---|---|---|---|---|
| INS-01 | Un equipo es un club del catálogo más una categoría-nivel. Puede haber dos equipos del mismo club en una categoría | 4.2, P8 | — | — |
| INS-02 | Un jugador mayor que su categoría se rechaza siempre. Uno menor se acepta, con aviso si son más de 2 años | P6, P42 | R `jugar_en_categoria_mayor`, `aviso_anios_menor` | Sí, 2 |
| INS-03 | No se pasa del máximo de jugadores; por debajo del mínimo hay aviso | 4.1, 4.2 | CN | Tabla 4.1 |
| INS-04 | El CI se normaliza (sigla, "E-", complemento o pasaporte) y se compara por número, complemento y "E-" | 4.2, supuesto | — | — |
| INS-05 | Un jugador en otro equipo solo se permite en el mismo club y otra categoría, con aviso | P7 | R `jugador_en_dos_equipos` | `mismo_club_otra_categoria` |
| INS-06 | Un profe puede estar en varios equipos, de cualquier club; se detecta por CI | 4.2, P10 | — | — |
| INS-07 | Alguien puede ser jugador en un equipo y profe en otro | P37 | R `jugador_y_profe` | Sí |
| INS-08 | Cuerpo técnico: hasta 3 personas, con roles fijos y un solo entrenador | 4.2, P11, P40 | R `cuerpo_tecnico` | 3; 1 entrenador |
| INS-09 | El dorsal es opcional al inscribir, obligatorio antes del primer partido y único en el equipo | P9 | R `dorsal_obligatorio` | Antes del primer partido |
| INS-10 | Se puede cargar un jugador sin CI, con aviso de documento pendiente | P39 | R `ci_obligatorio` | Antes del primer partido |
| INS-11 | Hay un cierre de inscripción. Después, solo el organizador cambia las listas | P2, P4 | R `cierre_inscripcion` | Configurable |
| INS-12 | La mesa marca a cada jugador como verificado al ver el documento | 4.2 | — | — |

### Fixture

| ID | Regla | Origen | Clave | Por defecto |
|---|---|---|---|---|
| FIX-01 | Formato según la cantidad de equipos, de 3 a 10 | 4.5 | F | Tabla 4.5 |
| FIX-02 | Con 2 equipos, ida y vuelta. Con más de 10, aviso de que falta el formato | P27 | F | — |
| FIX-03 | Todos contra todos por el método del círculo | 4.5 | F | — |
| FIX-04 | Series cruzadas con 6 y 7 equipos; con 7, descansa un equipo de A en cada fecha | 4.5 | F | — |
| FIX-05 | Los equipos del mismo club en un grupo se enfrentan en la fecha 1 | P24 | R `mismo_club_fecha_1` | Sí |
| FIX-06 | Series por sorteo, separando a los equipos del mismo club cuando se puede; editables antes de generar | P45 | R `sorteo_separa_clubes` | Sí |
| FIX-07 | Bronce con 10 equipos: 5.º A contra 5.º B | P25 | F | — |
| FIX-08 | La eliminación tiene participantes "por definir", que el organizador asigna a mano | 4.5, P50 | — | — |
| FIX-09 | Se puede rehacer el fixture de una categoría sin partidos jugados, y se reprograma solo esa | P22, P44 | R `rehacer_fixture` | Sí |

### Programación

| ID | Regla | Tipo | Origen | Clave | Por defecto |
|---|---|---|---|---|---|
| PRO-01 | Una cancha, o una mitad, tiene un partido a la vez. La cancha entera ocupa sus mitades | Dura | 5.1 | Cancha | — |
| PRO-02 | Cada categoría-nivel juega solo en canchas compatibles | Dura | 5.2 | Compatibilidad | — |
| PRO-03 | El partido empieza y termina dentro de una franja | Dura | 4.3, P48 | Franja | — |
| PRO-04 | Un equipo no tiene partidos que se pisen. Si juega dos el mismo día, deja un turno libre en medio, y no pasa del máximo por día | Dura | 5.4, P17, P47 | R `turnos_libres_mismo_dia`, `max_partidos_por_dia` | 1, 2 |
| PRO-05 | Un profe no tiene partidos que se pisen. Si cambia de cancha, necesita un margen | Dura | 5.5, P18, P35 | R `profe_minutos_cambio_de_cancha` | 10 |
| PRO-06 | Dos equipos que comparten un jugador no juegan a la vez | Dura | 5.6, P36 | — | — |
| PRO-07 | Un equipo no juega durante un bloqueo de la ACF | Dura | 5.7, P21, P38 | Bloqueo | — |
| PRO-08 | Los partidos de cada equipo van en el orden de las fechas | Dura o blanda | 5.8, P19 | R `orden_de_fechas` | Dura |
| PRO-09 | La eliminación va después de los grupos, la final después de las semis, y desde un fin de semana dado | Dura | 5.9, P33 | R `eliminacion_desde_fin_de_semana` | 5 |
| PRO-10 | Los partidos jugados o fijados a mano no se mueven | Dura | 5.10 | — | — |
| PRO-11 | Agrupar los partidos de un club, seguidos y en la misma cancha | Blanda | P20 | R `pesos` | — |
| PRO-12 | Pocos huecos por cancha y la carga repartida entre fines de semana | Blanda | 5 | R `pesos` | — |
| PRO-13 | Al reprogramar, mover la menor cantidad de partidos y equipos, preferir el mismo fin de semana y dar 2 o 3 propuestas | Blanda | 5 | R `pesos`, `propuestas` | 3 |
| PRO-14 | Lo que no entra se informa con su motivo, y la capacidad se muestra antes de programar | — | 5 | — | — |
| VER-01 | Un choque es un par de partidos con la lista de sus motivos, clasificado por tipo | Supuesto, H1 | — | — | — |

### Fuera de la demo

Puntos y desempate (4.6, P28, P34), W.O. (P23), tarjetas y sanciones (4.7, P29), premios (4.8, P30) y retención de datos (P49). Se van a especificar cuando lleguen.

## Preguntas abiertas

- **Para el organizador:** P1 a P51, en [docs/PROGRESO.md](docs/PROGRESO.md) y en la sección 9 del contexto. En la demo se priorizan P13, P33, P35, P44, P46 y P50.
- **Para Sebastian:** ¿se crea un repo privado en GitHub? Por ahora la carpeta no es un repo de git; en la fase 0 se hace `git init` local.
