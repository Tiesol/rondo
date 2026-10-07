# Tareas: fases 0 y 1

> Cada tarea va en su propia rama (`fase-N/...`) y termina en un PR a `main`. "Verde" significa que pasan `uv run pytest -m "not lento"`, `uv run mypy` y `uv run ruff check . && uv run ruff format --check .`.

## Fase 0: cimientos

### T0.1 Proyecto Python con herramientas de calidad

**Descripción:** crear `pyproject.toml` con `uv`, Python 3.14 y las dependencias aprobadas. Configurar ruff (líneas de 100), mypy (estricto en `src/dominio`), pytest con su marca `lento`, un `compose.yaml` con Postgres 18 y un `.env.example` sin secretos.

**Aceptación:**

- [x] `uv sync` instala todo con Python 3.14.
- [x] `docker compose up -d db` levanta Postgres 18 y responde.
- [x] Un test de humo pasa, y mypy y ruff quedan en verde.

**Verificación:** verde, más `docker compose ps` con la base sana.

**Depende de:** nada.
**Archivos:** `pyproject.toml`, `uv.lock`, `compose.yaml`, `.env.example`, `tests/test_humo.py`.
**Tamaño:** S.

### T0.2 Proyecto Django con settings por entorno

**Descripción:** crear el proyecto `rondo` y la app `torneo` en `src/`. Los settings salen de variables de entorno (`DATABASE_URL`, `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`), con zona `America/La_Paz` y español. Con `DEBUG=False` se activan cookies seguras, HSTS y redirección a HTTPS. WhiteNoise sirve los estáticos.

**Aceptación:**

- [x] `migrate` y `runserver` funcionan contra el Postgres local.
- [x] `manage.py check --deploy` no da advertencias con los settings de producción.
- [x] Sin `SECRET_KEY` en producción, la app no arranca. No hay un valor por defecto inseguro.

**Verificación:** verde, más `uv run python manage.py check --deploy` con variables de producción.

**Depende de:** T0.1.
**Archivos:** `manage.py`, `src/rondo/settings.py`, `src/rondo/urls.py`, `src/rondo/wsgi.py`, `src/torneo/apps.py`.
**Tamaño:** M.

### T0.3 Login y plantilla base para el celular

**Descripción:** activar `LoginRequiredMiddleware`, con login y logout de Django en español. La plantilla base usa Tailwind CSS (compilado, sin Node) y HTMX (copiado en `static/`), tiene un menú que funciona en el celular y una página de inicio vacía. El comando `crear_usuario` toma la contraseña de una variable de entorno.

**Aceptación:**

- [x] Un visitante anónimo que entra a cualquier URL va al login. Un usuario con sesión ve el inicio.
- [x] La página se ve bien a 360 px de ancho, sin scroll horizontal.
- [x] `crear_usuario` no imprime la contraseña, y falla si falta la variable.

**Verificación:** verde, con tests de acceso en `tests/torneo/test_acceso.py`, más una mirada manual en el celular con `runserver 0.0.0.0`.

**Depende de:** T0.2.
**Archivos:** `src/rondo/settings.py`, `src/rondo/urls.py`, `src/torneo/templates/base.html`, `src/torneo/templates/registration/login.html`, `src/torneo/management/commands/crear_usuario.py`.
**Tamaño:** M.

### T0.4 Guardas del repo

**Descripción:** crear el paquete vacío `src/dominio/`, con un test que falla si algún módulo del dominio importa Django. Agregar un hook `scripts/hooks/pre-commit` que:

- rechaza planillas, archivos de Word, PDF, fotos y `.env`;
- corre ruff y los tests rápidos.

Se instala con `git config core.hooksPath scripts/hooks`.

**Aceptación:**

- [x] Agregar `import django` en `src/dominio/` hace fallar el test de arquitectura.
- [x] Un commit que incluye un `.xlsx` (aunque se fuerce con `git add -f`) se rechaza con un mensaje claro.

**Verificación:** verde, más una prueba manual del hook con un archivo trampa.

**Depende de:** T0.1.
**Archivos:** `src/dominio/__init__.py`, `tests/test_arquitectura.py`, `scripts/hooks/pre-commit`.
**Tamaño:** S.

### T0.5 Deploy repetible en Render con Neon (demo)

> Cambio del 2026-10-07: la demo va en Render porque la cuenta de Google Cloud quedó bloqueada. La imagen Docker sirve para los dos.

**Descripción:** crear el `Dockerfile` (python:3.14-slim, uv, Tailwind, collectstatic y gunicorn), el script de arranque (migraciones y gunicorn) y el `render.yaml`. Con eso, cada merge a `main` despliega solo. Todo el proceso queda escrito en `docs/DESPLIEGUE.md`.

**Pasos tuyos (en DESPLIEGUE.md):**

1. Rehacer el proyecto de Neon en N. Virginia y crear la rama `demo`.
2. Crear el Blueprint en Render y pegar ahí la cadena de conexión. Nunca por el chat.
3. Crear el primer usuario desde tu terminal.

**Aceptación:**

- [x] La imagen se construye y corre en modo producción contra Postgres local: redirige a HTTPS, el login responde, el CSS se sirve y usa unos 70 MB de RAM.
- [ ] Render despliega desde `main` sin pasos a mano.
- [ ] Entras con login a la URL `*.onrender.com` desde el celular.

**Verificación:** `docker build` y `docker run` en local (hecho), más la prueba manual desde el celular.

**Depende de:** T0.3.
**Archivos:** `Dockerfile`, `.dockerignore`, `scripts/arrancar.sh`, `render.yaml`, `src/rondo/settings.py`, `docs/DESPLIEGUE.md`.
**Tamaño:** M.

### T0.6 Prueba de riesgo: OR-Tools en Cloud Run

**Descripción:** armar un modelo CP-SAT sintético con la forma del problema real: unos 200 partidos, canchas con mitades, equipos que no se pisan y pares de equipos con un profe en común. Se corre con un límite de tiempo, desde `/diagnostico/solver` (solo staff), y se mide con 1 y 2 vCPU.

**Aceptación:**

- [ ] En local, el modelo sintético encuentra una solución factible.
- [ ] En Render, quedan anotados en `PROGRESO.md` el tiempo hasta la primera solución, el estado final y la memoria usada.
- [ ] Queda decidido si Render alcanza para la demo o si hace falta Google Cloud antes.

**Verificación:** un test chico del modelo sintético (rápido), más la medición en la nube.

**Depende de:** T0.5.
**Archivos:** `src/dominio/programador/espiga.py`, `src/torneo/views/diagnostico.py`, `tests/dominio/test_espiga_solver.py`.
**Tamaño:** S.

### T0.7 Prueba de riesgo: PNG y compartir desde el celular

**Descripción:** hacer una página `/diagnostico/png` (solo staff) con un calendario de mentira de 1080 px de ancho. Un botón genera el PNG con `modern-screenshot` y lo comparte con la Web Share API. Si el celular no puede compartir archivos, lo descarga.

**Aceptación:**

- [ ] Desde tu celular Android, el PNG llega a un chat de WhatsApp y se ve nítido.
- [ ] Desde la PC, se descarga.
- [ ] iPhone: no se prueba, porque no hay uno a mano. Queda como riesgo.

**Verificación:** manual, con capturas anotadas en `PROGRESO.md`.

**Depende de:** T0.5. La Web Share API exige HTTPS, así que se prueba en Render.
**Archivos:** `src/torneo/templates/diagnostico/png.html`, `src/torneo/static/js/exportar.js`, `src/torneo/views/diagnostico.py`.
**Tamaño:** S.

## Fase 1: configuración

### T1.1 Dominio: modelos de configuración y reglas

**Descripción:** crear en `src/dominio/config.py` los modelos Pydantic `ConfigTorneo`, `Categoria`, `Nivel`, `Cancha` y `Reglas`. Cada campo de `Reglas` lleva su P#. Hay que poder calcular el año de nacimiento y el turno de cada categoría-nivel. Crear `datos/config/jmp_cup_2026.json` a partir de 4.1, con los valores por defecto de las secciones 9 y de PROGRESO.

**Aceptación:**

- [ ] CAT-01: en 2026, Sub 9 corresponde a 2017, y Sub 17 a 2009 y 2010.
- [ ] CAT-03: los turnos dan 40, 50, 60 y 70 según la tabla 4.4, en todas las categorías-nivel.
- [ ] Una configuración inválida (máximo menor que mínimo, nivel desconocido, regla con tipo incorrecto) se rechaza con un mensaje que dice qué campo falla.

**Verificación:** verde, con mypy estricto en `dominio`.

**Depende de:** T0.4.
**Archivos:** `src/dominio/config.py`, `datos/config/jmp_cup_2026.json`, `tests/dominio/test_config.py`.
**Tamaño:** M.

### T1.2 Dominio: franjas y compatibilidad

**Descripción:** convertir las franjas por día de la semana en franjas con fechas concretas, entre el inicio y el fin del torneo. Resolver las canchas compatibles de cada categoría-nivel: la regla por categoría manda sobre la de modalidad (CAT-04), y una cancha entera ocupa sus mitades.

**Aceptación:**

- [ ] 2026 da 15 franjas: 5 viernes, 5 sábados y 5 domingos, entre el 23 de octubre y el 22 de noviembre.
- [ ] Sub 6 va a C1A y C1B; Sub 10 Avanzado (F8), solo a C1; Sub 12 Avanzado (F11), solo a C3.
- [ ] Las canchas físicas de C1 son C1A y C1B, y las de C2 son solo C2.

**Verificación:** verde.

**Depende de:** T1.1.
**Archivos:** `src/dominio/franjas.py`, `src/dominio/canchas.py`, `tests/dominio/test_franjas.py`, `tests/dominio/test_canchas.py`.
**Tamaño:** S.

### T1.3 Modelos Django de configuración

**Descripción:** crear los modelos Torneo, CategoriaNivel, Cancha (con padre), Compatibilidad y Franja, y su primera migración. `Torneo.reglas` se valida con `dominio.config.Reglas` al guardar.

**Aceptación:**

- [ ] Restricciones en la base:
  - código de cancha único por torneo;
  - categoría y nivel únicos por torneo;
  - franjas con fin posterior al inicio.
- [ ] Guardar un Torneo con reglas inválidas falla con un error de validación, no con un error 500.
- [ ] Las fechas se guardan en UTC y se muestran en America/La_Paz.

**Verificación:** verde, con tests de modelos en `tests/torneo/test_modelos_configuracion.py`.

**Depende de:** T1.2 y T0.2.
**Archivos:** `src/torneo/models/__init__.py`, `src/torneo/models/configuracion.py`, `src/torneo/migrations/0001_initial.py`, `tests/torneo/test_modelos_configuracion.py`.
**Tamaño:** M.

### T1.4 Comando `cargar_config` con la configuración 2026

**Descripción:** crear el servicio que toma el JSON, lo valida con el dominio y crea o actualiza el torneo con todas sus tablas, sin duplicar nada. Es idempotente.

**Aceptación:**

- [ ] Después de cargar hay 23 categorías-nivel, 5 canchas (C1, C1A, C1B, C2 y C3), la compatibilidad de 4.1 y 15 franjas.
- [ ] Cargar dos veces deja las mismas cantidades.
- [ ] Un JSON inválido no deja nada a medias: todo va en una transacción.

**Verificación:** verde, más el comando corrido en la demo de la nube.

**Depende de:** T1.3.
**Archivos:** `src/torneo/servicios/configuracion.py`, `src/torneo/management/commands/cargar_config.py`, `tests/torneo/test_cargar_config.py`.
**Tamaño:** M.

### T1.5 Admin de la configuración e identidad del organizador

**Descripción:** armar el admin de Torneo, con las categorías-nivel, canchas y franjas editables. Las reglas se editan como JSON validado, y los errores de Pydantic se muestran en el campo. Agregar el modelo de configuración del sitio, que es único: nombre, logo y colores del organizador, para el PNG.

**Aceptación:**

- [ ] El staff edita un tope de jugadores y se guarda.
- [ ] Una regla inválida muestra el error junto al campo.
- [ ] La identidad del organizador se edita y aparece en la plantilla base.
- [ ] Alguien sin permisos de staff no entra al admin.

**Verificación:** verde, con tests del admin, más una revisión manual en la demo de la nube.

**Depende de:** T1.4.
**Archivos:** `src/torneo/admin.py`, `src/torneo/models/sitio.py`, migración, `tests/torneo/test_admin.py`.
**Tamaño:** M.
