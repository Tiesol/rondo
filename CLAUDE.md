# Rondo: app de la JMP CUP

App web para que la organización de la JMP CUP inscriba equipos, arme el fixture, programe los partidos sin choques y comparta el calendario. Python 3.14, Django 6.1, HTMX, Tailwind, OR-Tools, Postgres (Neon) y Cloud Run. Se habla en español con Sebastian.

## Fuentes de verdad

Leer antes de decidir nada:

| Archivo | Qué tiene |
|---|---|
| `docs/PROGRESO.md` | **Estado actual y siguiente paso**, decisiones, supuestos y preguntas abiertas (P1 a P51) |
| `tasks/todo.md` | La tarea en curso, con su aceptación, su verificación y los archivos que toca |
| `tasks/plan.md` | Índice de tareas por fase y checkpoints |
| `SPEC.md` | Aprobada: stack, comandos, estilo, tests, flujo de git, **límites** y catálogo de reglas |
| `docs/ARQUITECTURA.md` | Aprobada: módulos, modelo de datos, programador, seguridad y cuentas |
| `docs/CONTEXTO_JMP_CUP.md` | Reglas del negocio del organizador. Nunca se modifica |

## Al empezar una sesión

1. Leer el "Estado" de `docs/PROGRESO.md` y la tarea que indica en `tasks/todo.md`.
2. Correr `git status` y `git branch -vv`. Si hay una rama de tarea a medias, seguir ahí.
3. Seguir con esa tarea. No reabrir decisiones que ya están en la tabla "Decisiones" de PROGRESO.md, salvo que Sebastian lo pida.

## Flujo de trabajo

- **Una tarea a la vez, y solo lo que dice la tarea.** No adelantar trabajo de otras tareas o fases. Lo que se note fuera de alcance se anota y se le consulta a Sebastian.
- **Planificación:** la spec ya existe. `spec-driven-development` es solo para algo que la spec no cubre. Antes de empezar una fase sin detalle (de la 2 en adelante), se detallan sus tareas con `planning-and-task-breakdown`, y Sebastian las aprueba.
- **Al implementar:** `incremental-implementation` y `test-driven-development`. El test va primero y tiene que fallar.
- **Al cerrar cada fase:** `code-review-and-quality`, y el visto bueno de Sebastian antes de seguir.
- **Git:** una rama por tarea (`fase-N/descripcion`) y un PR a `main` con `gh`, que se fusiona con *merge commit* (nunca *squash*: los PR van encadenados). Los commits son chicos y con todo en verde. **Claude hace los `push`** por HTTPS, con las credenciales de `gh` (configurado solo en este repo, `credential.helper`). Nunca se piden contraseñas ni claves. **Claude fusiona los PR él mismo** con `gh`, en orden y con *merge commit*, si pasan los tests (autorizado por Sebastian el 2026-10-07).
- **Al terminar una tarea:** marcar sus casillas en `tasks/todo.md` y `tasks/plan.md`, y actualizar el "Estado", lo "Hecho" y las "Decisiones" de `docs/PROGRESO.md`.

## Verificación ("verde")

```bash
git config core.hooksPath scripts/hooks      # una vez por copia del repo: chequeo antes del commit
docker compose up -d db                      # Postgres 18 local
uv run pytest -m "not lento"
uv run mypy
uv run ruff check . && uv run ruff format --check .
```

## Límites (resumen de SPEC.md)

- **Preguntar antes de:**
  - agregar dependencias;
  - cambiar un valor por defecto del reglamento;
  - cambiar el modelo de datos cuando haya datos reales;
  - desplegar a producción;
  - tocar la nube o cualquier cosa que tenga costo;
  - crear repos o servicios.
- **Nunca:**
  - datos reales de jugadores (son menores): en tests y demo, solo datos inventados;
  - credenciales en el chat o en el repo, y no leer ni mostrar `.env`;
  - reglas del reglamento escritas en el código: van en la configuración;
  - acceso sin login;
  - borrar o saltear tests que fallan.
- **No inventar reglas.** Si falta una, se deja configurable con un valor por defecto y se anota en PROGRESO.md como pregunta, con el número P que sigue.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
