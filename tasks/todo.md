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
- [x] Render despliega desde `main` sin pasos a mano.
- [x] Entras con login a la URL `*.onrender.com` desde el celular.

**Verificación:** `docker build` y `docker run` en local (hecho), más la prueba manual desde el celular.

**Depende de:** T0.3.
**Archivos:** `Dockerfile`, `.dockerignore`, `scripts/arrancar.sh`, `render.yaml`, `src/rondo/settings.py`, `docs/DESPLIEGUE.md`.
**Tamaño:** M.

### T0.6 Prueba de riesgo: OR-Tools en Cloud Run

**Descripción:** armar un modelo CP-SAT sintético con la forma del problema real: unos 200 partidos, canchas con mitades, equipos que no se pisan y pares de equipos con un profe en común. Se corre con un límite de tiempo, desde `/diagnostico/solver` (solo staff), y se mide con 1 y 2 vCPU.

**Aceptación:**

- [x] En local, el modelo sintético encuentra una solución factible.
- [x] Con los límites de Render quedan anotados en `PROGRESO.md` el tiempo hasta la primera solución, el estado final y la memoria usada.
- [x] Queda decidido si Render alcanza para la demo o si hace falta Google Cloud antes.

**Verificación:** un test chico del modelo sintético (rápido), más la medición en la nube.

**Depende de:** T0.5.
**Archivos:** `src/dominio/programador/espiga.py`, `src/torneo/management/commands/probar_solver.py`, `tests/dominio/test_espiga_solver.py`.
**Tamaño:** S.

### T0.7 Prueba de riesgo: PNG y compartir desde el celular

**Descripción:** hacer una página `/diagnostico/png` (solo staff) con un calendario de mentira de 1080 px de ancho. Un botón genera el PNG con `modern-screenshot` y lo comparte con la Web Share API. Si el celular no puede compartir archivos, lo descarga.

**Aceptación:**

- [ ] Desde tu celular Android, el PNG llega a un chat de WhatsApp y se ve nítido.
- [ ] Desde la PC, se descarga. (Pendiente de prueba manual. Desde T5.6, la prueba se hace con la página real: Calendario → un día → "Compartir el día".)
- [ ] iPhone: no se prueba, porque no hay uno a mano. Queda como riesgo.

**Verificación:** manual, con capturas anotadas en `PROGRESO.md`.

**Depende de:** T0.5. La Web Share API exige HTTPS, así que se prueba en Render.
**Archivos:** `src/torneo/templates/diagnostico/png.html`, `src/torneo/static/js/exportar.js`, `src/torneo/views/diagnostico.py`.
**Tamaño:** S.

## Fase 1: configuración

### T1.1 Dominio: modelos de configuración y reglas

**Descripción:** crear en `src/dominio/config.py` los modelos Pydantic `ConfigTorneo`, `Categoria`, `Nivel`, `Cancha` y `Reglas`. Cada campo de `Reglas` lleva su P#. Hay que poder calcular el año de nacimiento y el turno de cada categoría-nivel. Crear `datos/config/jmp_cup_2026.json` a partir de 4.1, con los valores por defecto de las secciones 9 y de PROGRESO.

**Aceptación:**

- [x] CAT-01: en 2026, Sub 9 corresponde a 2017, y Sub 17 a 2009 y 2010.
- [x] CAT-03: los turnos dan 40, 50, 60 y 70 según la tabla 4.4, en todas las categorías-nivel.
- [x] Una configuración inválida (máximo menor que mínimo, nivel desconocido, regla con tipo incorrecto) se rechaza con un mensaje que dice qué campo falla.

**Verificación:** verde, con mypy estricto en `dominio`.

**Depende de:** T0.4.
**Archivos:** `src/dominio/config.py`, `datos/config/jmp_cup_2026.json`, `tests/dominio/test_config.py`.
**Tamaño:** M.

### T1.2 Dominio: franjas y compatibilidad

**Descripción:** convertir las franjas por día de la semana en franjas con fechas concretas, entre el inicio y el fin del torneo. Resolver las canchas compatibles de cada categoría-nivel: la regla por categoría manda sobre la de modalidad (CAT-04), y una cancha entera ocupa sus mitades.

**Aceptación:**

- [x] 2026 da 15 franjas: 5 viernes, 5 sábados y 5 domingos, entre el 23 de octubre y el 22 de noviembre.
- [x] Sub 6 va a C1A y C1B; Sub 10 Avanzado (F8), solo a C1; Sub 12 Avanzado (F11), solo a C3.
- [x] Las canchas físicas de C1 son C1A y C1B, y las de C2 son solo C2.

**Verificación:** verde.

**Depende de:** T1.1.
**Archivos:** `src/dominio/franjas.py`, `src/dominio/canchas.py`, `tests/dominio/test_franjas.py`, `tests/dominio/test_canchas.py`.
**Tamaño:** S.

### T1.3 Modelos Django de configuración

**Descripción:** crear los modelos Torneo, CategoriaNivel, Cancha (con padre), Compatibilidad y Franja, y su primera migración. `Torneo.reglas` se valida con `dominio.config.Reglas` al guardar.

**Aceptación:**

- [x] Restricciones en la base:
  - código de cancha único por torneo;
  - categoría y nivel únicos por torneo;
  - franjas con fin posterior al inicio.
- [x] Guardar un Torneo con reglas inválidas falla con un error de validación, no con un error 500.
- [x] Las fechas se guardan en UTC y se muestran en America/La_Paz.

**Verificación:** verde, con tests de modelos en `tests/torneo/test_modelos_configuracion.py`.

**Depende de:** T1.2 y T0.2.
**Archivos:** `src/torneo/models/__init__.py`, `src/torneo/models/configuracion.py`, `src/torneo/migrations/0001_initial.py`, `tests/torneo/test_modelos_configuracion.py`.
**Tamaño:** M.

### T1.4 Comando `cargar_config` con la configuración 2026

**Descripción:** crear el servicio que toma el JSON, lo valida con el dominio y crea o actualiza el torneo con todas sus tablas, sin duplicar nada. Es idempotente.

**Aceptación:**

- [x] Después de cargar hay 23 categorías-nivel, 5 canchas (C1, C1A, C1B, C2 y C3), la compatibilidad de 4.1 y 15 franjas.
- [x] Cargar dos veces deja las mismas cantidades.
- [x] Un JSON inválido no deja nada a medias: todo va en una transacción.

**Verificación:** verde, más el comando corrido en local. En la demo de la nube lo corre Sebastian (DESPLIEGUE.md, 3b), porque necesita la cadena de Neon.

**Depende de:** T1.3.
**Archivos:** `src/torneo/servicios/configuracion.py`, `src/torneo/management/commands/cargar_config.py`, `tests/torneo/test_cargar_config.py`.
**Tamaño:** M.

### T1.5 Admin de la configuración e identidad del organizador

**Descripción:** armar el admin de Torneo, con las categorías-nivel, canchas y franjas editables. Las reglas se editan como JSON validado, y los errores de Pydantic se muestran en el campo. Agregar el modelo de configuración del sitio, que es único: nombre, logo y colores del organizador, para el PNG.

**Aceptación:**

- [x] El organizador (superusuario) edita un tope de jugadores y se guarda.
- [x] Una regla inválida muestra el error junto al campo.
- [x] La identidad del organizador (nombre y color) se edita y aparece en la plantilla base. El logo queda para la fase 5.
- [x] Alguien sin permisos de staff no entra al admin.

**Verificación:** verde, con tests del admin, más una revisión manual en la demo de la nube.

**Depende de:** T1.4.
**Archivos:** `src/torneo/admin.py`, `src/torneo/models/sitio.py`, migración, `tests/torneo/test_admin.py`.
**Tamaño:** M.

## Fase 1b: pantallas propias

> **Aprobada por Sebastian el 2026-10-07.** Reemplaza al admin de Django como pantalla del organizador, siguiendo `docs/DISENO.md` y el prototipo (https://claude.ai/artifact/VacxSHvhh36heQY2xS8Q3a). El admin queda solo para Sebastian, en `/admin/`. No agrega dependencias.

### TU.1 Base visual: tokens, plantilla y navegación

**Descripción:** pasar los tokens de `DISENO.md` a Tailwind (azul marino, dorado, colores de estado, Bebas Neue y Figtree, con las fuentes copiadas en `static/` y sin Google). Armar los parciales de plantilla (sección, lista, fila, chip, botón, pestañas, banda, hoja inferior, aviso y estado vacío) y la plantilla base: barra superior azul, barra inferior en el celular y barra lateral desde 900 px, y modo claro y oscuro. El enlace al admin sale del menú.

**Aceptación:**

- [x] Inicio, login y una página de ejemplo con todos los parciales se ven como el prototipo a 360 px y a 1024 px, en claro y en oscuro (capturas).
- [x] Se navega todo con el teclado, con el foco visible en dorado.
- [x] Ningún color está escrito a mano en las plantillas: todos salen de los tokens.

**Verificación:** verde, más capturas a 360 y 1024 px.
**Depende de:** nada.
**Archivos:** `frontend/tailwind.css`, `src/torneo/static/fuentes/`, `src/torneo/templates/base.html`, `src/torneo/templates/parciales/`, `tests/torneo/test_base.py`.
**Tamaño:** M.

### TU.2 Roles: Organización y Mesa de control

**Descripción:** crear los grupos "Organización" (todo) y "Mesa de control" (equipos, listas, verificar y ver el calendario) con sus permisos, en una migración de datos. Agregar un control de acceso para las vistas, que muestra "Solo la organización puede…" en lugar de un error genérico. `crear_usuario` recibe `--rol organizacion|mesa`. La pantalla "Más" muestra las personas y su rol.

**Aceptación:**

- [x] La mesa no entra a crear torneo, reglas ni programar: ve el aviso del rol y recibe un 403.
- [x] La organización entra a todo.
- [x] `crear_usuario --rol mesa` crea un usuario sin staff y dentro de su grupo.

**Verificación:** verde, con tests de permisos por vista.
**Depende de:** TU.1.
**Archivos:** migración de datos, `src/torneo/permisos.py`, `crear_usuario.py`, vistas y plantilla de "Más", `tests/torneo/test_roles.py`.
**Tamaño:** M.

### TU.3 Reglas del torneo con interruptores

**Descripción:** cada campo de `dominio.config.Reglas` recibe un título, una ayuda en español y su P#, como metadatos del modelo de Pydantic. Con eso, un formulario de Django se arma solo: interruptores para los sí/no, botones + y − para los números y listas para las opciones. Reemplaza el JSON del admin.

**Aceptación:**

- [x] Todas las reglas se editan sin JSON, con su explicación y su P#.
- [x] Un valor inválido muestra el error en el campo, y no se guarda nada.
- [x] Agregar una regla nueva al dominio la hace aparecer en la pantalla sin tocar la plantilla.

**Verificación:** verde, más una captura.
**Depende de:** TU.2.
**Archivos:** `src/dominio/config.py`, `src/torneo/forms/reglas.py`, la vista y plantilla de reglas, `tests/torneo/test_reglas_pantalla.py`.
**Tamaño:** M.

### TU.4 Crear torneo con el asistente

**Descripción:** el asistente de 4 pasos del prototipo (datos, categorías, canchas y horarios, y reglas) parte de la plantilla `jmp_cup_2026.json` y termina llamando al servicio `cargar_configuracion`. Reemplaza el comando de terminal para el organizador.

**Aceptación:**

- [x] Con la plantilla y sin cambiar nada, crea lo mismo que `cargar_config`: 23 categorías-nivel, 5 canchas y 15 franjas.
- [x] Destildar una categoría o cambiar un horario se refleja en el torneo creado.
- [x] Volver atrás no pierde lo cargado en los pasos anteriores.

**Verificación:** verde, con un test de punta a punta del asistente.
**Depende de:** TU.3.
**Archivos:** las vistas, formularios y plantillas del asistente, `tests/torneo/test_asistente.py`.
**Tamaño:** M.

### TU.5 Inicio y Torneo

**Descripción:** Inicio muestra el torneo activo, los **pendientes** (sin barra de avance; por ahora, lo que se puede saber sin equipos: categorías sin equipos o preguntas P sin responder que afectan la programación) y los accesos. Torneo muestra el selector de categoría y las pestañas: Equipos (vacío hasta la fase 2), Fixture y Posiciones (vacíos) y Ajustes (la configuración de la categoría, editable solo por la organización).

**Aceptación:**

- [x] Sin torneo creado, Inicio invita a crearlo (estado vacío).
- [x] Cambiar de categoría actualiza la pantalla sin recargarla (HTMX), y la URL lo refleja.
- [x] La mesa ve los ajustes, pero no los puede cambiar.

**Verificación:** verde, más capturas.
**Depende de:** TU.2.
**Archivos:** `src/torneo/views/inicio.py`, `src/torneo/views/torneo.py`, sus plantillas y parciales, y tests.
**Tamaño:** M.

### TU.6 Página pública (base)

**Descripción:** `/t/<torneo>/` sin login: el encabezado del torneo, el selector de categoría y las pestañas Partidos, Posiciones y Equipos, con estados vacíos. Se llenan en las fases 3 a 5. Solo se ven los torneos marcados como públicos. Las vistas públicas no cargan nunca Persona, Jugador ni Profe.

**Aceptación:**

- [x] Se abre sin login. Un torneo no público da 404.
- [x] Un test recorre las plantillas públicas y falla si alguna usa datos personales.
- [x] Se ve bien a 360 px.

**Verificación:** verde, más capturas.
**Depende de:** TU.1.
**Archivos:** `src/torneo/views/publico.py`, plantillas públicas, `tests/torneo/test_publico.py`.
**Tamaño:** M.

### TU.7 Datos de la escuela

**Descripción:** pantalla para editar el nombre y los colores del organizador, sin admin. Los colores pintan la interfaz: el principal reemplaza al azul marino de los tokens y se agrega un color de acento para el dorado, con esos dos como valores por defecto (hoy el color guardado por defecto es el verde rechazado, y TU.1 dejó de usarlo; R4 en `docs/REVISAR.md`). El logo y los patrocinadores esperan a que haya imágenes y un lugar donde guardarlas.

**Aceptación:**

- [x] La organización cambia el nombre y aparece en todas las pantallas y en la página pública.
- [x] Un color inválido muestra el error en el campo.

**Verificación:** verde.
**Depende de:** TU.2.
**Archivos:** la vista, formulario y plantilla de la escuela, y su test.
**Tamaño:** S.

## Fase 2: inscripción

> Se avanza con la autorización general del 2026-10-07 (planificado el mismo día). Nueva dependencia: `faker`, aprobada en el plan general para esta fase. Reglas del catálogo: INS-01 a INS-12.

### T2.1 Dominio: normalización de documentos (INS-04)

**Descripción:** crear `dominio/documentos.py`, que convierte lo que escribe la organización en un documento normalizado: tipo (CI, CI de extranjero o pasaporte), número, complemento, sigla de departamento y una **clave de comparación**. La clave se arma con el número, el complemento y el prefijo "E-"; la sigla se guarda, pero no se compara (supuesto de PROGRESO).

**Aceptación:**

- [x] Una tabla de casos reales de formato (sin datos reales) da la clave esperada: `1234567 SC`, `1234567-1E`, `E-1234567`, `1.234.567 lp`, `1234567SC` y el pasaporte `AB123456`.
- [x] `1234567 SC` y `1234567 LP` tienen la misma clave. `1234567` y `1234567-1E`, no.
- [x] Un texto vacío o sin dígitos da "sin documento", no un error. Un texto con basura da un error con un mensaje claro.

**Verificación:** verde, con mypy estricto.
**Depende de:** nada.
**Archivos:** `src/dominio/documentos.py`, `tests/dominio/test_documentos.py`.
**Tamaño:** S.

### T2.2 Dominio: validaciones de inscripción (INS-02, 03, 05 a 10)

**Descripción:** crear `dominio/inscripcion.py`, con funciones puras que reciben datos simples (fechas, cantidades, roles, los equipos donde ya está una persona) y la configuración, y devuelven una lista de **hallazgos**. Cada hallazgo tiene un nivel (error o aviso), el ID de la regla y un mensaje en español. Ninguna función accede a la base.

**Aceptación:**

- [x] INS-02: un jugador mayor que su categoría es un error. Uno menor se acepta, con un aviso si son más de `aviso_anios_menor` años. Sub 17 acepta los dos años de nacimiento.
- [x] INS-03: no se puede pasar del máximo de jugadores, y por debajo del mínimo hay aviso.
- [x] INS-05 a 07: una persona en otro equipo del mismo club y otra categoría da aviso; en otro club o en la misma categoría, error. Un profe en varios equipos está permitido. Jugador en un equipo y profe en otro, según la regla.
- [x] INS-08 a 10: hasta 3 en el cuerpo técnico, con un solo entrenador; dorsal único dentro del equipo; falta de CI o de dorsal es aviso hasta el primer partido.

**Verificación:** verde. Cada test lleva el ID de su regla en el nombre.
**Depende de:** T2.1.
**Archivos:** `src/dominio/inscripcion.py`, `tests/dominio/test_inscripcion.py`.
**Tamaño:** M.

### T2.3 Modelos de inscripción, y datos personales fuera de los logs

**Descripción:** crear los modelos Club (con alias), Equipo, Persona, Jugador y Profe, y su migración. Persona es la única tabla con datos personales, y su clave de CI es única cuando existe. Además, el pendiente obligatorio de la revisión de la fase 0: un **filtro de logs** que no deje pasar el texto de los errores de la base, porque una violación de unicidad del CI escribiría el número en el log. Agregar el admin de Club.

**Aceptación:**

- [x] Restricciones en la base: CI único si existe, dorsal único por equipo si existe, una persona una sola vez por equipo y un equipo por club + categoría-nivel + nombre visible.
- [x] Un test provoca un `IntegrityError` con un CI repetido y comprueba que el log no contiene el número.
- [x] El admin de Club permite cargar alias, y el catálogo de clubes de 2023 (6.2, solo nombres) se carga con un comando.

**Verificación:** verde, más `makemigrations --check`.
**Depende de:** T2.1.
**Archivos:** `src/torneo/models/inscripcion.py`, migración, `src/rondo/logs.py`, `src/torneo/admin.py`, `tests/torneo/test_modelos_inscripcion.py`.
**Tamaño:** M.

### T2.4 Servicio de inscripción

**Descripción:** crear `servicios/inscripcion.py`, que agrega un jugador o un profe a un equipo. Normaliza el documento, busca a la Persona por su clave (o la crea), arma la entrada del dominio con los equipos donde ya está esa persona, y guarda solo si no hay errores, en una transacción. Devuelve los hallazgos para mostrarlos.

**Aceptación:**

- [x] Agregar a alguien que ya está en otro equipo del mismo club, en otra categoría, guarda y devuelve el aviso de INS-05.
- [x] Con un error (por ejemplo, edad o el máximo), no se guarda nada.
- [x] La misma persona escrita como `1234567 SC` y `1234567` es una sola Persona.

**Verificación:** verde.
**Depende de:** T2.2 y T2.3.
**Archivos:** `src/torneo/servicios/inscripcion.py`, `tests/torneo/test_servicio_inscripcion.py`.
**Tamaño:** M.

### T2.5 Pantallas: equipos

**Descripción:** con `frontend-ui-engineering`, armar la lista de equipos por categoría-nivel (con conteo de jugadores y avisos), el alta de un equipo (club del catálogo, sin texto libre) y la ficha del equipo con su plantel y su cuerpo técnico. Todo pensado primero para el celular.

**Aceptación:**

- [x] El organizador crea un equipo eligiendo club, categoría-nivel, nombre visible y colores.
- [x] La lista muestra cuántos jugadores tiene cada equipo y marca los que están por debajo del mínimo.
- [x] Se ve bien a 360 px.

**Verificación:** verde, con tests de vistas, más capturas a 360 px.
**Depende de:** T2.3.
**Archivos:** `src/torneo/views/inscripcion.py`, `src/torneo/forms/inscripcion.py`, plantillas, `tests/torneo/test_vistas_equipos.py`.
**Tamaño:** M.

### T2.6 Pantallas: jugadores y cuerpo técnico, con avisos en vivo

**Descripción:** el formulario para agregar un jugador o un profe a un equipo, que usa el servicio de T2.4. Con HTMX, los avisos aparecen al salir de cada campo, antes de guardar (por ejemplo, "esta persona ya está en Sub 11 Avanzado de este club"). La mesa de control marca a cada jugador como "verificado" desde la ficha.

**Aceptación:**

- [x] Los criterios de inscripción de la sección 10 del contexto se cumplen desde la pantalla.
- [x] Los avisos no bloquean el guardado; los errores sí.
- [x] El formulario con datos personales es sensible: no aparece en los logs.

**Verificación:** verde, con tests de vistas, más una prueba manual en el celular.
**Depende de:** T2.4 y T2.5.
**Archivos:** vistas, formularios y parciales HTMX de inscripción, `tests/torneo/test_vistas_jugadores.py`.
**Tamaño:** M.

### T2.7 Generador de datos de demo

**Descripción:** crear `manage.py generar_demo`, que arma un torneo inventado del tamaño de 2023, con los clubes de 6.2 y las categorías nuevas. Los jugadores tienen nombres, CI y fechas inventados con `faker` (semilla fija), y algunos son de menor edad o no tienen CI ni dorsal, para mostrar los avisos. Los profes y los jugadores compartidos siguen los patrones de 6.4. **Se niega a correr** si la base tiene datos que no son de demo.

**Aceptación:**

- [x] Genera unos 80 equipos, con planteles dentro de los topes y los 7 jugadores compartidos de 6.4.
- [x] Correrlo dos veces no duplica nada.
- [x] Sin la bandera `--soy-la-demo`, no hace nada.

**Verificación:** verde, más correrlo contra la rama `demo` de Neon (lo hace Sebastian).
**Depende de:** T2.4.
**Archivos:** `src/torneo/management/commands/generar_demo.py`, `src/torneo/servicios/demo.py`, `tests/torneo/test_generar_demo.py`.
**Tamaño:** M.

## Fase 3: fixture y verificador

> Planificada el 2026-10-07 con `planning-and-task-breakdown`. Se avanza con la autorización general del mismo día (sin visto bueno entre fases; dudas en `docs/REVISAR.md`). Sin dependencias nuevas: el flujo máximo de la capacidad usa OR-Tools (`SimpleMaxFlow`). Reglas del catálogo: FIX-01 a FIX-09, VER-01, PRO-01 a PRO-07 (las que el verificador puede comprobar) y PRO-14.

### T3.1 Formatos como datos (FIX-01, FIX-02, FIX-07)

**Descripción:** pasar la tabla 4.5 a `datos/config/formatos.json` y validarla en `dominio/formatos.py` (Pydantic): para cada cantidad de equipos, la fase de grupos (todos contra todos, con ida y vuelta o no; series con sus tamaños; cruzadas o dentro de cada serie) y los partidos de eliminación (copa, ronda, clave y referencias de sus participantes: "1.º A", "ganador de la semi 1 de Oro", "mejor perdedor", "mejor 3.º"…). Con 2 equipos, ida y vuelta. Con más de 10, un error claro de "falta el formato" (P27, P54).

**Aceptación:**

- [x] De 3 a 10 equipos, el formato da 8, 10, 12, 14, 17, 18, 22 y 27 partidos; con 2, da 2.
- [x] Una referencia a un partido o a una serie que no existe hace fallar la validación, con un mensaje que dice cuál.
- [x] Con 11 equipos, `formato_para(11)` lanza `FormatoFaltante`, que menciona P27.

**Verificación:** verde, con mypy estricto.
**Depende de:** nada.
**Archivos:** `datos/config/formatos.json`, `src/dominio/formatos.py`, `tests/dominio/test_formatos.py`.
**Tamaño:** M.

### T3.2 Dominio: cruces de la fase de grupos (FIX-03, FIX-04, FIX-05)

**Descripción:** `dominio/cruces.py`: todos contra todos por el método del círculo (con ida y vuelta), series cruzadas (cada equipo de A contra cada uno de B, y con 4 y 3 descansa uno de A en cada fecha) y todos contra todos dentro de cada serie. Después, las fechas se reordenan para que los equipos del mismo club se enfrenten en la fecha 1 (si la regla está encendida). Trabaja con identificadores, no con modelos.

**Aceptación:**

- [x] Para 2 a 10 equipos y cada tipo de grupo, ningún cruce se repite (dos veces exactas con ida y vuelta) y nadie juega dos veces en la misma fecha (test de propiedad con hypothesis).
- [x] Con series de 4 y 3 cruzadas hay 4 fechas y en cada una descansa un equipo de A.
- [x] Dos equipos del mismo club que se cruzan juegan en la fecha 1.

**Verificación:** verde, con mypy estricto.
**Depende de:** T3.1.
**Archivos:** `src/dominio/cruces.py`, `tests/dominio/test_cruces.py`.
**Tamaño:** M.

### T3.3 Dominio: sorteo de series y fixture completo (FIX-06, FIX-08)

**Descripción:** `dominio/fixture.py`: el sorteo de series con una semilla, que separa a los equipos del mismo club cuando se puede (FIX-06), y el armado del fixture de una categoría: cruces de grupos más los partidos de eliminación del formato, con participantes "por definir" (FIX-08).

**Aceptación:**

- [x] La misma semilla da el mismo sorteo; con dos equipos de un club y dos series, quedan en series distintas.
- [x] El fixture de N equipos tiene la cantidad de partidos del formato, y los de eliminación llevan referencias y no equipos.
- [x] Con series ya elegidas a mano, el fixture las respeta.

**Verificación:** verde, con mypy estricto.
**Depende de:** T3.2.
**Archivos:** `src/dominio/fixture.py`, `tests/dominio/test_fixture.py`.
**Tamaño:** M.

### T3.4 Modelos Serie y Partido, y servicio de fixture (FIX-09)

**Descripción:** crear los modelos Serie (categoría, nombre y equipos) y Partido (categoría, fase, copa, ronda, clave, fecha, serie, local y visitante o sus referencias, estado, cancha, inicio y fijado), y su migración. El servicio `generar_fixture(categoria, semilla)` sortea las series si no hay, arma el fixture con el dominio y lo guarda. Rehacerlo borra el anterior, solo si la regla lo permite y no hay partidos jugados (FIX-09). `generar_fixture_de_todas` lo hace para cada categoría con equipos.

**Aceptación:**

- [x] Generar el fixture de una categoría de 6 equipos guarda 2 series de 3 y 14 partidos, 5 de ellos "por definir".
- [x] Rehacerlo no duplica; con un partido jugado, o con la regla apagada, se niega con un mensaje.
- [x] Con más de 10 equipos devuelve el aviso de P27 y no guarda nada.

**Verificación:** verde, más `makemigrations --check`.
**Depende de:** T3.3.
**Archivos:** `src/torneo/models/fixture.py`, migración, `src/torneo/servicios/fixture.py`, `tests/torneo/test_servicio_fixture.py`.
**Tamaño:** M.

### T3.5 Pantallas: series y fixture

**Descripción:** en Torneo → Fixture: las series (editables antes de generar, moviendo equipos de serie), el botón para generar o rehacer el fixture (solo la organización) y los partidos por fecha, con los de eliminación "por definir". En Inicio, un pendiente por las categorías con equipos y sin fixture, y "Generar todos los fixtures". La pestaña Partidos de la página pública muestra el fixture, sin datos personales.

**Aceptación:**

- [x] La organización genera el fixture de una categoría y lo ve por fecha; la mesa lo ve, pero no lo genera (403 con el aviso del rol).
- [x] Mover un equipo de serie antes de generar cambia los cruces.
- [x] La página pública muestra los cruces de la categoría.

**Verificación:** verde, más capturas a 360 px.
**Depende de:** T3.4.
**Archivos:** `src/torneo/views/fixture.py`, plantillas de Torneo y públicas, `tests/torneo/test_vistas_fixture.py`.
**Tamaño:** M.

### T3.6 Dominio: verificador de choques (VER-01, PRO-01 a PRO-07) y prueba 2023

**Descripción:** `dominio/verificador.py` recibe cualquier calendario (partidos con equipos, cancha, inicio y turno), las canchas físicas, la compatibilidad, las franjas, los pares de equipos que comparten profes o jugadores, los bloqueos y las reglas. Devuelve los choques: un par de partidos (o un partido solo, si es de franja o de compatibilidad) con la lista de motivos y su tipo (cancha, equipo, persona, compatibilidad, franja o bloqueo). La prueba usa el calendario de 6.3 (`datos/pruebas/calendario_2023.csv`, solo nombres de equipos), los grupos de 6.4 de `datos/demo/equipos.json` y las canchas de 2023 (6.1).

**Aceptación:**

- [x] Prueba 2023: exactamente 2 choques de personas (los de River Plate), 3 de cancha y 0 de compatibilidad, como dice la SPEC.
- [x] Cada tipo tiene un caso mínimo propio: equipo sin turno libre en el día, máximo de partidos por día, profe que cambia de cancha sin margen, franja y bloqueo.
- [x] Un par de partidos con varios motivos cuenta como un solo choque.

**Verificación:** verde, con mypy estricto.
**Depende de:** nada (recibe cualquier calendario).
**Archivos:** `src/dominio/verificador.py`, `datos/pruebas/calendario_2023.csv`, `tests/dominio/test_verificador.py`.
**Tamaño:** M.

### T3.7 Capacidad con flujo máximo (PRO-14) y pantalla "Programar"

**Descripción:** `dominio/capacidad.py` calcula, por grupo de canchas conectadas por la compatibilidad, las horas que piden los partidos contra las que dan las franjas, en todo el torneo y desde el fin de semana de la eliminación (P33). Usa un flujo máximo de OR-Tools: un partido en una mitad ocupa media cancha. La pantalla `/torneos/<id>/programar/` (solo la organización) muestra "¿Entra todo?" con barras, como el prototipo; el botón de programar llega en la fase 4.

**Aceptación:**

- [x] Con la demo, se ve la capacidad de C1 y C2 y la de C3, en grupos y en eliminación, y avisa cuando la eliminación no entra (H4).
- [x] Un caso chico calculado a mano da el mismo resultado que el flujo.
- [x] La mesa ve el aviso del rol.

**Verificación:** verde, más una captura.
**Depende de:** T3.4.
**Archivos:** `src/dominio/capacidad.py`, `src/torneo/servicios/capacidad.py`, la vista y plantilla de programar, `tests/dominio/test_capacidad.py`, `tests/torneo/test_programar.py`.
**Tamaño:** M.

## Fase 4: programador

> Planificada el 2026-10-07 con `planning-and-task-breakdown`. Se avanza con la autorización general del mismo día. Sin dependencias nuevas (OR-Tools CP-SAT ya está). Reglas del catálogo: PRO-01 a PRO-10, PRO-12 (en parte) y PRO-14. El objetivo de agrupar por club (PRO-11, P20) es lo primero que se recorta si no alcanza el tiempo (ARQUITECTURA 12).

### T4.1 Pares de equipos que comparten personas

**Descripción:** `servicios/personas.py` calcula, desde Persona, los pares de equipos que no pueden jugar a la vez y por qué ("profe" o "jugador"; jugador en uno y profe en otro cuenta como profe). Al dominio le llegan solo identificadores de equipo y el motivo, nunca nombres ni CI (ARQUITECTURA 6).

**Aceptación:**

- [x] Con la demo salen los pares de 6.4: 7 jugadores compartidos y los profes compartidos (River Plate, Crack FC, etc.).
- [x] Un profe en tres equipos da los tres pares.
- [x] La salida no tiene nombres ni documentos.

**Verificación:** verde.
**Depende de:** nada.
**Archivos:** `src/torneo/servicios/personas.py`, `tests/torneo/test_pares_de_personas.py`.
**Tamaño:** S.

### T4.2 Dominio: modelo CP-SAT, restricciones de cancha, franja y equipo

**Descripción:** `dominio/programador/modelo.py` en pasos de 5 minutos. Cada partido elige un inicio dentro de las franjas (el partido termina adentro, P48) y una cancha compatible, o queda sin ubicar. Las canchas físicas no se pisan (C1 ocupa C1A y C1B). Cada equipo no se pisa y deja los turnos libres del día (P17), y no pasa del máximo por día (P47). Los partidos fijados o jugados no se mueven (PRO-10). Objetivo: ubicar la mayor cantidad posible.

**Aceptación:**

- [x] Un caso chico se programa entero y el verificador no encuentra choques.
- [x] Con más partidos que lugares, los que sobran quedan sin ubicar y el resto sigue sin choques.
- [x] Un partido fijado queda donde estaba.

**Verificación:** verde, con mypy estricto.
**Depende de:** nada (usa el verificador de T3.6 en los tests).
**Archivos:** `src/dominio/programador/modelo.py`, `tests/dominio/test_programador.py`.
**Tamaño:** M.

### T4.3 Dominio: personas, bloqueos, orden y eliminación

**Descripción:** sumar al modelo los pares de personas (jugador: no se pisan; profe: además, el margen para cambiar de cancha, P35, aplicado siempre, que es más estricto que la regla), los bloqueos de la ACF, el orden de las fechas de cada equipo (P19, dura) y la eliminación: después de toda la fase de grupos de su categoría, después de los partidos a los que se refiere, y desde el fin de semana de P33. Objetivo secundario: cada fecha cerca de su fin de semana, para repartir la carga (PRO-12).

**Aceptación:**

- [x] Dos equipos con un profe en común no quedan a la vez ni en canchas distintas sin margen.
- [x] La final queda después de sus semis, y las semis después de los grupos de su categoría.
- [x] La fecha 2 de un equipo queda después de su fecha 1.

**Verificación:** verde, con mypy estricto.
**Depende de:** T4.2.
**Archivos:** `src/dominio/programador/modelo.py`, `tests/dominio/test_programador.py`.
**Tamaño:** M.

### T4.4 Dominio: por qué no entra un partido (PRO-14)

**Descripción:** `dominio/programador/motivos.py`: para cada partido sin ubicar, prueba sus inicios y canchas posibles contra el calendario resultante y resume por qué no sirve ninguno: no hay cancha libre, choque de equipo, de profe o jugador, bloqueo u orden (por ejemplo, la eliminación no tiene lugar después de los grupos).

**Aceptación:**

- [x] Un partido sin lugar por falta de cancha dice "No queda ningún turno libre en C3…".
- [x] Uno que solo choca con un profe dice eso.
- [x] Cada partido sin ubicar tiene un motivo.

**Verificación:** verde, con mypy estricto.
**Depende de:** T4.3.
**Archivos:** `src/dominio/programador/motivos.py`, `tests/dominio/test_motivos.py`.
**Tamaño:** S.

### T4.5 Corrida y servicio de programación

**Descripción:** modelo Corrida (tipo, parámetros, estado, resultado, duración y usuario) y `servicios/programador.py`: arma la entrada desde la base, corre el solver con un límite de tiempo configurable (`PROGRAMADOR_SEGUNDOS`, 60 por defecto), guarda inicio, cancha y estado de cada partido, verifica el resultado con el verificador y guarda la Corrida antes de responder. Un bloqueo en la base impide dos programaciones a la vez.

**Aceptación:**

- [x] Programar el torneo guarda los partidos programados y una Corrida con cuántos se ubicaron, los que no (con su motivo) y los choques que encontró el verificador (0).
- [x] Mientras corre una programación, otra se rechaza con un mensaje.
- [x] Los partidos jugados o fijados no cambian.

**Verificación:** verde, más `makemigrations --check`.
**Depende de:** T4.1, T4.4.
**Archivos:** `src/torneo/models/corrida.py`, migración, `src/torneo/servicios/programador.py`, `tests/torneo/test_servicio_programador.py`.
**Tamaño:** M.

### T4.6 Pantallas: programar y calendario por día y cancha

**Descripción:** el botón de la pantalla Programar se activa: corre la programación (con la pantalla en espera, HTMX) y muestra el resultado ("187 de 191 programados, sin choques" y la lista "Sin lugar" con sus motivos). La pestaña Calendario muestra un día por cancha (C1 con sus mitades), con hora, categoría y cruce, y un selector de días. La página pública suma el día y la hora a los partidos.

**Aceptación:**

- [x] La organización programa y ve el resultado; la mesa ve el calendario pero no programa.
- [x] El calendario de un día muestra cada cancha con sus partidos en orden.
- [x] Se ve bien a 360 px.

**Verificación:** verde, más capturas.
**Depende de:** T4.5.
**Archivos:** `src/torneo/views/programar.py`, `src/torneo/views/calendario.py`, plantillas, `tests/torneo/test_vistas_calendario.py`.
**Tamaño:** M.

### T4.7 El torneo de demo programado, y limpieza de la espiga

**Descripción:** un test (marcado `lento`) programa la demo completa y comprueba con el verificador que quedan 0 choques duros, y que todo lo que no entró tiene motivo. Se mide el tiempo en local. Se borran la espiga de T0.6 (`dominio/programador/espiga.py`, `probar_solver` y su test), como estaba previsto al cerrar la fase 4. La página de prueba del PNG queda hasta que la fase 5 la reemplace.

**Aceptación:**

- [x] La demo queda programada con 0 choques duros según el verificador.
- [x] Lo que no entra se lista con su motivo.
- [x] La espiga ya no está en el repo.

**Verificación:** `uv run pytest -m lento`, más verde.
**Depende de:** T4.6.
**Archivos:** `tests/torneo/test_programar_demo.py`, borrado de la espiga.
**Tamaño:** S.

## Fase 5: reprogramación y calendario

> Planificada el 2026-10-07 con `planning-and-task-breakdown`. Se avanza con la autorización general del mismo día. Sin dependencias nuevas de Python. La fuente Arvo del PNG (OFL) se copia en `static/fuentes`, como las otras. Reglas: PRO-07, PRO-10, PRO-13 y el criterio 6 (PNG sin datos personales). Si no alcanza el tiempo, se recorta en este orden: vistas por club y por categoría (T5.7), tercera propuesta y franjas entre semana (T5.5).

### T5.1 Bloqueos de la ACF (PRO-07)

**Descripción:** modelo Bloqueo (equipos, inicio, fin y motivo) y su migración. El servicio de programación los pasa al solver y al verificador. Pantalla "Partido de la ACF" (solo la organización): se eligen los equipos, el día y el horario, y la app muestra al instante (HTMX) qué partidos programados chocan.

**Aceptación:**

- [x] Un bloqueo guardado hace que programar no ponga partidos de ese equipo en ese horario.
- [x] Al cargarlo, la pantalla lista los partidos que chocan, con día, hora y cancha.
- [x] La mesa ve el aviso del rol.

**Verificación:** verde, más `makemigrations --check`.
**Depende de:** fase 4.
**Archivos:** `src/torneo/models/bloqueo.py`, migración, `src/torneo/servicios/programador.py`, la vista y plantilla de la ACF, `tests/torneo/test_bloqueos.py`.
**Tamaño:** M.

### T5.2 Dominio: propuestas de reprogramación (PRO-13)

**Descripción:** `dominio/programador/reprogramar.py`: parte del calendario actual y de un bloqueo nuevo. Solo pueden moverse los partidos de ese fin de semana y del siguiente (el resto queda fijo). El objetivo es mover la menor cantidad de partidos, afectar a la menor cantidad de equipos y preferir el mismo fin de semana. Para dar 2 o 3 propuestas distintas, después de cada solución se prohíbe repetir el mismo conjunto de movimientos. Cada propuesta pasa por el verificador.

**Aceptación:**

- [x] Un bloqueo sobre un partido programado da 2 o 3 propuestas válidas (0 choques), ordenadas por cuántos partidos mueven.
- [x] Ninguna propuesta mueve partidos jugados, fijados ni de otros fines de semana.
- [x] Las propuestas son distintas entre sí.

**Verificación:** verde, con mypy estricto.
**Depende de:** T5.1.
**Archivos:** `src/dominio/programador/reprogramar.py`, `tests/dominio/test_reprogramar.py`.
**Tamaño:** M.

### T5.3 Pantalla de propuestas, aplicar e historial

**Descripción:** después de cargar un bloqueo con choques, la pantalla muestra las propuestas como en el prototipo (la primera, recomendada; cada movimiento "antes → después"). Aplicar una guarda los partidos y un Cambio por movimiento (partido, antes, después, usuario, fecha, motivo y corrida), en una Corrida de tipo reprogramar. El historial de cambios se ve en "Más".

**Aceptación:**

- [x] Con la demo programada, un bloqueo ACF da 2 o 3 propuestas ordenadas, y aplicar una deja el calendario sin choques.
- [x] Cada movimiento queda en el historial con quién y cuándo.
- [x] Aplicar una propuesta vieja (si el calendario cambió después) se rechaza con un mensaje.

**Verificación:** verde, más capturas.
**Depende de:** T5.2.
**Archivos:** `src/torneo/models/cambio.py`, migración, `src/torneo/servicios/reprogramar.py`, vistas y plantillas, `tests/torneo/test_reprogramar_pantalla.py`.
**Tamaño:** M.

### T5.4 Cambio manual verificado

**Descripción:** desde el calendario, la organización mueve un partido a otro día, hora y cancha. El verificador lo revisa antes de guardar: si crea un choque duro, se muestra y no se guarda. Si no, queda fijado (PRO-10) y en el historial.

**Aceptación:**

- [x] Mover un partido a un turno libre lo guarda, fijado y con su Cambio.
- [x] Moverlo encima de otro partido muestra el choque y no guarda nada.
- [x] La mesa no puede mover partidos.

**Verificación:** verde.
**Depende de:** T5.3.
**Archivos:** vistas, formulario y plantilla del cambio, `tests/torneo/test_cambio_manual.py`.
**Tamaño:** S.

### T5.5 Suspender un día y agregar un día entre semana

**Descripción:** "Suspender" un día (por ejemplo, por lluvia): sus partidos quedan sin programar y la app ofrece reprogramarlos con propuestas. "Agregar un día entre semana" crea una franja de tipo entre semana, que el programador y las propuestas pueden usar.

**Aceptación:**

- [x] Suspender un día deja sus partidos pendientes y las propuestas los ubican en otros días, sin choques.
- [x] Una franja entre semana nueva aparece en el calendario y se usa al reprogramar.

**Verificación:** verde.
**Depende de:** T5.3.
**Archivos:** servicio y vistas de suspensión y franjas, `tests/torneo/test_suspender.py`.
**Tamaño:** M.

### T5.6 PNG del día por cancha (criterio 6)

**Descripción:** una imagen de 1220 × 690 por cancha y por día, con el diseño de 2025 (`docs/prototipo/fixture-png.html`): fondo azul marino, filas doradas (categoría, escudo, equipo, equipo, escudo y hora), panel con "CANCHA N" y la edición, y franja de patrocinadores (con lugar reservado hasta que haya imágenes). Se comparte desde el calendario con la Web Share API, o se descarga. Reemplaza la página de prueba de T0.7.

**Aceptación:**

- [x] Desde el calendario de un día, "Compartir" genera una imagen por cancha.
- [x] Un test comprueba que la plantilla del PNG no usa datos personales.
- [x] La página de prueba del PNG ya no está.

**Verificación:** verde, más una captura del PNG.
**Depende de:** fase 4.
**Archivos:** `src/torneo/templates/calendario/png.html`, `src/torneo/static/js/exportar.js`, `src/torneo/static/fuentes/`, `tests/torneo/test_png.py`.
**Tamaño:** M.

### T5.7 Vistas por categoría y por club

**Descripción:** el calendario se filtra por categoría y por club: la lista de partidos con día, hora y cancha. Es lo primero que se recorta si falta tiempo.

**Aceptación:**

- [x] Por club: todos los partidos de sus equipos, en orden.
- [x] Por categoría: sus partidos, en orden.

**Verificación:** verde.
**Depende de:** fase 4.
**Archivos:** vistas y plantillas del calendario, `tests/torneo/test_vistas_por_club.py`.
**Tamaño:** S.

### T5.8 Instalación en el celular (PWA) y ensayo de la demo

**Descripción:** manifest e íconos (generados, sin imágenes del organizador) para instalar la app en el celular; funciona solo con conexión (decisión del 2026-10-06), así que el service worker no guarda datos. Guion de la demo en `docs/DEMO.md` y un test de punta a punta: demo → fixtures → programar → bloqueo ACF → propuesta → aplicar → PNG.

**Aceptación:**

- [x] El manifest se sirve y la app se puede instalar (Chrome la reconoce como PWA).
- [x] El test de punta a punta pasa.
- [x] `docs/DEMO.md` tiene el guion, con las preguntas prioritarias para el organizador (P13, P33, P35, P44, P46 y P50).

**Verificación:** verde, `pytest -m lento`.
**Depende de:** T5.3, T5.6.
**Archivos:** manifest, service worker, íconos, `docs/DEMO.md`, `tests/torneo/test_demo_de_punta_a_punta.py`.
**Tamaño:** M.

## Fase 6: producción 2026

> Planificada el 2026-10-08. La fase tiene dos partes:
>
> - **A, se puede avanzar sin Sebastian** (con la autorización general del 2026-10-07): T6.1 a T6.4.
> - **B, necesita a Sebastian**, porque toca producción, la nube, costos o respuestas del organizador (SPEC, "Límites"): T6.5 a T6.7. Quedan escritas para su vuelta.

### T6.1 Asignar a mano los participantes de la eliminación (P50)

**Descripción:** en Torneo → Fixture, cada partido de eliminación "por definir" tiene un selector de local y de visitante, con los equipos de la categoría. El organizador los asigna cuando conoce las posiciones (la app no calcula la tabla: puntos y desempate quedan fuera hasta que se especifiquen). Desde ahí, el programador y el verificador cuentan con esos equipos.

**Aceptación:**

- [x] La organización asigna local y visitante a una semifinal; la referencia ("1.º A") queda a la vista.
- [x] No se puede asignar el mismo equipo a los dos lados ni un equipo de otra categoría.
- [x] Un partido asignado ya no está "por definir" en el fixture, el calendario ni el PNG.

**Verificación:** verde.
**Archivos:** vista, formulario y plantilla del fixture, `tests/torneo/test_asignar_eliminacion.py`.
**Tamaño:** S.

### T6.2 Personas: invitar, cambiar el rol y la contraseña

**Descripción:** en "Más", la organización crea un usuario con su rol (la app genera una contraseña temporal que se muestra una sola vez para entregarla en persona) y cambia el rol de los demás. Cada persona cambia su contraseña desde "Más" (R6).

**Aceptación:**

- [x] La organización crea un usuario de mesa; la contraseña temporal se ve una vez y nunca se guarda en claro ni va al log.
- [x] La organización cambia el rol de alguien; la mesa no puede.
- [x] Cualquiera cambia su propia contraseña.

**Verificación:** verde.
**Archivos:** vistas y plantillas de personas, `tests/torneo/test_personas.py`.
**Tamaño:** M.

### T6.3 Revisión de seguridad

**Descripción:** revisión con `security-and-hardening` sobre toda la app: encabezados (CSP, Referrer-Policy, Permissions-Policy), sesiones, límite de intentos de login sin dependencias nuevas, permisos de cada vista, datos personales en logs y respuestas, y `manage.py check --deploy`. Se corrige lo que se encuentre, con su test.

**Aceptación:**

- [x] Un test recorre todas las URLs y confirma que piden login (salvo las públicas y la PWA) y que las de la organización dan 403 a la mesa.
- [x] Hay CSP y los demás encabezados, y la app sigue funcionando (HTMX, PNG).
- [x] Muchos intentos fallidos de login desde la misma IP se frenan por un rato.

**Verificación:** verde, más `check --deploy` sin advertencias.
**Archivos:** `src/rondo/settings.py`, middleware o vistas del login, `tests/torneo/test_seguridad.py`, PROGRESO.md.
**Tamaño:** M.

### T6.4 Retención de datos (P49)

**Descripción:** `manage.py anonimizar_torneo <id> --confirmo` borra los datos personales de un torneo terminado: nombres, documentos y fechas de nacimiento de las personas que no estén en otro torneo. Quedan los planteles como "Jugador 1, 2…" con su dorsal. Por defecto de P49, se corre a fin de año.

**Aceptación:**

- [x] Después de correrlo no queda ningún nombre, documento ni fecha de nacimiento del torneo.
- [x] Sin `--confirmo` no hace nada; con un torneo en curso se niega.
- [x] Los equipos, partidos y el calendario quedan intactos.

**Verificación:** verde.
**Archivos:** `src/torneo/management/commands/anonimizar_torneo.py`, `src/torneo/servicios/retencion.py`, `tests/torneo/test_anonimizar.py`.
**Tamaño:** S.

### T6.5 Producción separada de la demo (necesita a Sebastian)

> **Reemplazada por T7.10** (pedido del 2026-10-12: Render Standard y Neon Launch).

**Descripción:** rama `production` de Neon y un servicio aparte (Render Starter o Cloud Run, según H6 y la cuenta de Google Cloud), con su `SECRET_KEY`, backups y el límite del programador acorde a su CPU. Usuarios reales creados por Sebastian. Todo queda en `docs/DESPLIEGUE.md`.

**Por qué espera:** desplegar a producción, crear servicios y tocar la nube con costo piden a Sebastian (SPEC, "Límites").

### T6.6 Configuración con las respuestas del organizador (necesita a Sebastian)

> **Reemplazada por T7.4 y T7.5** (convocatoria 2026). Las respuestas que lleguen después se cargan como configuración, sin tocar el código.

**Descripción:** con las respuestas de la demo (P13, P33, P35, P44, P46, P50 y las demás), ajustar `jmp_cup_2026.json`, `formatos.json` (P54) y las reglas, y anotarlo en PROGRESO.md.

**Por qué espera:** no se inventan reglas (CLAUDE.md); hacen falta las respuestas.

### T6.7 Carga de las listas reales y publicación (necesita a Sebastian)

**Descripción:** la organización carga las listas 2026 en producción (nunca en el repo ni en la demo), genera los fixtures, programa y publica la página pública. Si cargar a mano no alcanza (P51), se suma pegar filas copiadas de Excel.

**Por qué espera:** son datos reales de menores, y solo van a producción.

> **Desde el 2026-10-12:** va después de T7.8 (pegar listas) y de T7.10 (producción). El pegado desde Excel ya está en T7.7 a T7.9.

## Fase 7: pedido 2026, bloque A (calendario y carga de listas)

> Planificada el 2026-10-12 desde `docs/PEDIDO_CLAUDE_CODE.md`, bloque A (fecha pedida: miércoles 14/10). Fuentes: `docs/REVISION_RONDO_FASE4.md` (puntos 1 y 2), `docs/CONVOCATORIA_2026_PARA_RONDO.md` y `docs/PREGUNTAS_JMP_CUP_2026.md` (fuente de las P a partir de ahora). Los ajustes del pedido mandan sobre la convocatoria.
>
> - **Preguntas sin respuesta:** no frenan. Cada una queda configurable, con el valor por defecto de PREGUNTAS y un `TODO(P#)` en el código.
> - **Dependencias:** ninguna nueva en esta fase.
> - **Fusiones:** durante la prueba del martes 13/10, ninguna fusión a `main` hasta que Sebastian avise. Nunca `generar_demo` en la demo.
> - **Ya resueltos de la revisión externa:** punto 3 (T6.1), punto 7 (T6.3). El punto 6 entra en T7.10; el 8, en T7.10 (límite de workers) y T8.11 (caché). El punto 4 (huecos en la cancha) queda fuera de este pedido: se anota como pendiente.
> - **"Posiciones" no se oculta:** la pestaña queda, y en la fase 8 se llena con la tabla.

### T7.1 La eliminación respeta el turno libre (P17), en el modelo y en el verificador

**Descripción:** cada participante referido de una llave (ganador, perdedor, mejor perdedor o una posición de grupo) se trata como un equipo virtual. Si la llave que lo define y la que lo usa caen el mismo día, la segunda empieza a partir de `inicio + turno × (1 + turnos_libres_mismo_dia)`. Lo mismo entre el último partido de grupos de la categoría y las llaves que toman posiciones. El verificador detecta los mismos casos y cuenta los partidos del día del equipo virtual para el máximo de P47.

**Aceptación:**

- [x] Con 4 equipos y una sola franja, la final no queda a menos de semi + 2 turnos.
- [x] El verificador marca el caso de Sub 15 Avanzado de la revisión (semi a las 17:10 y final a las 18:20 en C3).
- [x] Con la demo programada, ninguna llave encadenada queda sin descanso (test lento).

**Verificación:** verde, más `pytest -m lento`.
**Depende de:** nada.
**Archivos:** `src/dominio/programador/modelo.py`, `src/dominio/verificador.py`, `tests/dominio/test_programador.py`, `tests/dominio/test_verificador.py`.
**Tamaño:** M.

### T7.2 Profes: seguidos en la misma cancha, y el choque solo para el entrenador (P18, P35, P57)

**Descripción:** en `personas()`, el margen de P35 se pide solo si los dos partidos son en canchas distintas: `NoOverlap` sin margen y, para cada par de partidos del profe, una separación condicionada a que las canchas difieran. Regla nueva `choque_de_profes` (P57): "Solo el entrenador" (por defecto) o "Todo el cuerpo técnico", en la pantalla de reglas; el modelo, el verificador y los pares de T4.1 la usan.

**Aceptación:**

- [x] Un profe compartido puede tener dos partidos seguidos en la misma cancha (5 minutos entre uno y otro); en canchas distintas, con 5 minutos, se rechaza.
- [x] Con el valor por defecto, un asistente o un delegado compartido no genera choque; al prender su rol en las reglas, sí.
- [x] El verificador y el modelo dan lo mismo en esos casos.

**Verificación:** verde.
**Depende de:** T7.1 (mismo archivo; evita conflictos).
**Archivos:** `src/dominio/config.py`, `src/dominio/programador/modelo.py`, `src/dominio/verificador.py`, `src/torneo/servicios/programador.py`, tests de dominio.
**Tamaño:** M.

### T7.3 Objetivo blando: menos espera de los profes (PRO-11)

**Descripción:** penalizar los minutos de espera de un profe entre sus partidos del mismo día, con menos peso que ubicar partidos (peso en `pesos`). Si el modelo se vuelve lento con el tamaño de 2026, se mide y se avisa antes de recortar.

**Aceptación:**

- [x] Con dos partidos de un profe en un día con lugar libre, el solver los pone seguidos.
- [x] Ubicar un partido más pesa siempre más que cualquier espera.
- [x] En la demo, se informa la espera mediana de los profes (objetivo: menos de 30 minutos): 5 a 10 min (H7).

**Verificación:** verde, más `pytest -m lento`.
**Depende de:** T7.2.
**Archivos:** `src/dominio/programador/modelo.py`, `src/dominio/config.py` (peso), `tests/dominio/test_programador.py`.
**Tamaño:** S.

### T7.4 Fútbol 6 y plantilla 2026 (convocatoria)

**Descripción:** agregar `F6` a `Modalidad` y a las opciones del modelo, con su migración. En `jmp_cup_2026.json`: torneo del 24/10 al 15/11 (11 días, sin el viernes 23), eliminación desde el 4.º fin de semana, `cierre_inscripcion` el 21/10 a las 12:00 (hora de Bolivia), Sub 5 y Sub 6 en F6 y en C1A y C1B (P63), Sub 10 y Sub 11 Avanzado en F8 (P60). En el asistente, Sub 15 Femenino queda destildada pero disponible (P61). "Agregar un día entre semana" propone el jueves.

**Aceptación:**

- [x] El asistente sin cambios crea el torneo 2026 con 11 días de juego y la eliminación en el 4.º fin de semana.
- [x] Sub 5 y Sub 6 son F6 y solo tienen C1A y C1B; Sub 15 Femenino no se crea salvo que se tilde.
- [x] Al agregar un día entre semana, la fecha propuesta es el jueves de esa semana.

**Verificación:** verde, más `cargar_config` en una base vacía.
**Depende de:** nada.
**Archivos:** `src/dominio/config.py`, `src/torneo/models/configuracion.py` y su migración, `datos/config/jmp_cup_2026.json`, `src/torneo/servicios/asistente.py`, la vista de suspender o agregar día, tests.
**Tamaño:** M.

### T7.5 Copa de Bronce con interruptor (P62)

**Descripción:** regla `copa_bronce_con_10` en la pantalla de reglas, apagada por defecto. Con la regla apagada, el formato de 10 equipos no genera la final de Bronce. Actualizar el criterio de la sección 10 de 27 a 26 partidos, con la regla anotada.

**Aceptación:**

- [x] Con 10 equipos y la regla apagada salen 26 partidos; prendida, 27.
- [x] Cambiar la regla con fixtures de 10 equipos ya generados los deja marcados como desactualizados (el aviso es de T7.11).

**Verificación:** verde.
**Depende de:** nada.
**Archivos:** `src/dominio/config.py`, `src/dominio/fixture.py` o `formatos.py`, `datos/config/formatos.json`, tests de fixture.
**Tamaño:** S.

### T7.6 Fecha de nacimiento: alcanza con el año

**Descripción:** la persona guarda el año de nacimiento siempre, y el día y el mes si se conocen. La regla de edad (INS-02) usa solo el año. Con solo el año se muestra "fecha incompleta", como aviso y no como error. Migración que copia el año de las fechas que ya existen.

**Aceptación:**

- [x] Un jugador con solo "2014" se guarda en Sub 12 y muestra "fecha incompleta".
- [x] Un año fuera de la categoría sigue dando el mismo error que una fecha completa.
- [x] La anonimización (T6.4) también borra el año.

**Verificación:** verde.
**Depende de:** nada.
**Archivos:** `src/torneo/models/inscripcion.py` y su migración, `src/dominio/inscripcion.py`, formularios y plantillas de jugador, `src/torneo/servicios/retencion.py`, tests.
**Tamaño:** M.

### T7.7 Dominio: leer filas pegadas

**Descripción:** funciones puras que reciben el texto pegado (separado por tabuladores, como lo copian Excel, Word y las hojas de cálculo) y devuelven filas y columnas. Proponen qué es cada columna (nombres, apellidos, nombre completo, fecha o año, documento, dorsal, rol o ignorar), separan el nombre completo (las dos últimas palabras como apellidos), leen fechas (dd/mm/aaaa, número de fecha de Excel, "12 de marzo 2014" y solo el año) y detectan una lista entera en mm/dd/aaaa cuando el segundo número pasa de 12. Reconocen el rol del cuerpo técnico escrito de distintas formas ("D.T", "DT", "Director técnico").

**Aceptación:**

- [x] Las cinco formas de lista de 2023 (CONTEXTO 6.5), recreadas con datos inventados, se leen bien.
- [x] Una lista en mm/dd/aaaa se detecta y se corrige entera; una con fechas ambiguas no se toca.
- [x] Tests de propiedad (hypothesis) sobre fechas y nombres.

**Verificación:** verde.
**Depende de:** T7.6 (fecha con solo el año).
**Archivos:** `src/dominio/pegado.py`, `tests/dominio/test_pegado.py`.
**Tamaño:** M.

### T7.8 Pantalla: pegar la lista de jugadores

**Descripción:** en la ficha del equipo, "Pegar lista": un área para pegar, después las primeras filas con un selector por columna (con la propuesta de T7.7) y la vista previa con los errores y avisos de cada fila, los mismos que la carga a mano (`revisar_*` de T2.4). Se guardan las filas sin errores en una sola transacción; las que tienen error quedan marcadas para corregirlas, sin perderlas.

**Aceptación:**

- [x] Pegar 20 filas con 2 errores guarda 18 y deja las 2 a la vista para corregir.
- [x] Un jugador repetido o que pasa el máximo del plantel se marca como en la carga a mano.
- [x] Ningún dato pegado va al log ni queda en la sesión después de guardar (formulario sensible).

**Verificación:** verde, más una prueba a mano a 360 px.
**Depende de:** T7.7.
**Archivos:** vista, formulario y plantillas de pegado, `src/torneo/servicios/inscripcion.py`, `tests/torneo/test_pegar_lista.py`.
**Tamaño:** M.

### T7.9 Pantalla: pegar el cuerpo técnico

**Descripción:** lo mismo que T7.8 en la pestaña Cuerpo técnico, con la columna de rol.

**Aceptación:**

- [x] Pegar "D.T", "Asistente" y "Delegado" carga los tres roles.
- [x] Un segundo entrenador o un cuarto profe se marca como error (INS-08).

**Verificación:** verde.
**Depende de:** T7.8.
**Archivos:** las mismas de T7.8, `tests/torneo/test_pegar_profes.py`.
**Tamaño:** S.

### T7.10 Producción preparada (T6.5, necesita a Sebastian para desplegar)

**Descripción:** todo listo para que Sebastian cree producción: servicio aparte en Render Standard (1 CPU) **sin despliegue automático**, Neon de producción en N. Virginia (plan Launch, historia de 7 días), `RONDO_PROGRAMADOR_SEGUNDOS=120`, los workers de CP-SAT acordes a la CPU (revisión, punto 8), `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` por variable (dominio propio opcional) y usuarios reales con `crear_usuario`. Corregir el test que falla en un clon nuevo por `assets/` (revisión, punto 6). Los pasos de Sebastian quedan en `docs/DESPLIEGUE.md`.

**Aceptación:**

- [x] Con las variables de producción, `check --deploy` pasa sin advertencias y el test de `assets/` pasa en un clon nuevo.
- [x] La cantidad de workers del solver sale de una variable, con un valor por defecto para 1 CPU.
- [x] `docs/DESPLIEGUE.md` tiene los pasos de Render, Neon, variables, primer usuario y cómo desplegar a mano.

**Verificación:** verde, más un clon limpio.
**Depende de:** nada. El despliegue lo hace Sebastian.
**Archivos:** `src/rondo/settings.py`, `src/torneo/servicios/programador.py`, `docs/DESPLIEGUE.md`, `tests/rondo/test_settings.py`.
**Tamaño:** S.

### T7.11 Borrador del calendario y fixture desactualizado

**Descripción:** mientras la página pública esté apagada, el calendario interno y el PNG dicen "Borrador". Si se agrega o se saca un equipo de una categoría que ya tiene fixture, la categoría muestra "El fixture de esta categoría está desactualizado" y ofrece rehacerlo. Rehacer y volver a programar se puede todas las veces que haga falta mientras no haya partidos jugados (P44).

**Aceptación:**

- [x] Con la página pública apagada, el calendario y el PNG dicen "Borrador"; prendida, no.
- [x] Agregar o sacar un equipo después del fixture muestra el aviso en la categoría y en Inicio.
- [x] Rehacer el fixture borra los partidos viejos y su programación; con un partido jugado, no se puede.

**Verificación:** verde.
**Depende de:** nada.
**Archivos:** `src/torneo/servicios/fixture.py`, `src/torneo/servicios/pendientes.py`, plantillas del calendario y del PNG, tests.
**Tamaño:** M.

### T7.12 Medir la programación 2026 con 1 CPU

**Descripción:** con la plantilla 2026 y la demo, programar en un contenedor limitado a 1 CPU (como Render Standard) y anotar en PROGRESO.md (H7): partidos ubicados, tiempo, estado del solver, espera de los profes (mediana, media, máxima, esperas de más de 2 h, seguidos en la misma cancha) y llaves encadenadas sin descanso.

**Aceptación:**

- [x] H7 en PROGRESO.md con los cinco datos y la comparación con la revisión externa.
- [x] Si no entra todo o no baja de 30 minutos la espera, se explica por qué y qué pregunta lo destraba (P13, P33).

**Verificación:** la medición, repetible con un comando o un script fuera del repo, anotado en H7.
**Depende de:** T7.1 a T7.5.
**Archivos:** `docs/PROGRESO.md`.
**Tamaño:** S.

```
T7.1 → T7.2 → T7.3 ─┐
T7.4, T7.5 ─────────┴→ T7.12
T7.6 → T7.7 → T7.8 → T7.9
T7.10 y T7.11 (independientes)
T7.8 + T7.10 → T6.7 (carga real, en producción)
```

**Checkpoint de la fase 7:**

- [x] Verde, más `pytest -m lento`.
- [x] La demo programada con la plantilla 2026: sin choques, sin llaves encadenadas sin descanso, y la medición en H7.
- [x] Una lista de 2023 recreada con datos inventados se pega en menos de un minuto.
- [x] `docs/DESPLIEGUE.md` listo para que Sebastian cree producción.
- [x] Revisión con `code-review-and-quality`, PROGRESO.md al día y las P que quedaron como TODO.
- [x] Visto bueno de Sebastian y aviso de qué probar.

## Fase 8: pedido 2026, bloque B (reemplazar a Copa Fácil)

> Planificada el 2026-10-12 desde `docs/PEDIDO_CLAUDE_CODE.md`, bloque B (fecha pedida: antes del viernes 23/10). Si algo no llega, la 1.ª fecha va en Copa Fácil (P77). Orden del pedido: B1 → B2 → B3 → B4 → B6 → B5 → B7 → B8.
>
> - **Dependencias aprobadas:** `django-storages[s3]` (con `boto3`) y `Pillow`. Cualquier otra se pregunta.
> - **Reglas nuevas** (resultados, tabla, tarjetas y suspensiones): van al catálogo de SPEC.md con su ID y a la configuración, con su P#.
> - **Imágenes:** las fijas del diseño del PNG van en el repo (`src/torneo/static/png/`); escudos, fotos, logo del organizador y patrocinadores van al almacenamiento (Cloudflare R2), subidos desde la app.

### T8.1 Almacenamiento de imágenes conectable (B1)

**Descripción:** `django-storages` con S3 apuntando a Cloudflare R2, con bucket privado y URL firmadas que vencen. Se activa con `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` y `R2_BUCKET`. Sin ellas: disco local en desarrollo y tests; en producción o en la demo, los botones de subir se ven desactivados con "Falta conectar el almacenamiento de imágenes". La CSP permite las imágenes del host de R2.

**Aceptación:**

- [x] Con las cuatro variables, los archivos van a R2 (probado con un almacenamiento falso en los tests) y las URL vencen.
- [x] Sin ellas y con `DEBUG=False`, ningún formulario acepta imágenes y se ve el aviso.
- [x] `check --deploy` sigue sin advertencias.

**Verificación:** verde.
**Depende de:** nada.
**Archivos:** `pyproject.toml`, `uv.lock`, `src/rondo/settings.py`, `src/rondo/encabezados.py`, un contexto o etiqueta para el aviso, tests.
**Tamaño:** M.

### T8.2 Procesar la imagen al subirla

**Descripción:** con Pillow, al subir: solo imágenes (se abre y se verifica, no se confía en la extensión), tamaño máximo configurable, se achica a unos 800 px (fotos) o 400 px (escudos y logos), se guarda en WebP y **se borran los metadatos (EXIF, incluida la ubicación GPS)**. Nombre de archivo al azar, sin el nombre de la persona.

**Aceptación:**

- [ ] Una foto con GPS en el EXIF sale sin ningún metadato.
- [ ] Un archivo que no es imagen, o que pasa el máximo, se rechaza con un mensaje junto al campo.
- [ ] La imagen guardada no pasa del tamaño pedido y su nombre no tiene datos personales.

**Verificación:** verde.
**Depende de:** T8.1.
**Archivos:** `src/torneo/servicios/imagenes.py`, `tests/torneo/test_imagenes.py`.
**Tamaño:** S.

### T8.3 Escudo del club, logo del organizador y patrocinadores (B2, P68, P69)

**Descripción:** escudo en el Club (uno por club), logo en Datos de la escuela y patrocinadores por torneo (imagen, nombre y orden) en una pantalla de la organización. Donde hoy se dibuja la sigla con el color, se muestra el escudo si existe.

**Aceptación:**

- [ ] La organización sube el escudo de un club y aparece en todos sus equipos.
- [ ] Se agregan, ordenan y sacan patrocinadores de un torneo; la mesa no puede.
- [ ] Sin escudo, se sigue viendo la sigla con el color.

**Verificación:** verde, más una prueba a mano a 360 px.
**Depende de:** T8.2.
**Archivos:** `src/torneo/models/inscripcion.py`, `src/torneo/models/sitio.py`, modelo Patrocinador y migración, vistas y plantillas, tests.
**Tamaño:** M.

### T8.4 Foto de la persona y autorización (B2, P66, P67, P75)

**Descripción:** la organización o la mesa sube la foto de una persona (sirve para jugador y profe). Casilla por jugador "autoriza foto y nombre", apagada por defecto; al subir la foto, el formulario pregunta si la familia la mandó para publicarla. Sin autorización, la foto no sale en ningún lado público. Borrar la foto la borra del almacenamiento.

**Aceptación:**

- [ ] Una foto sin autorización se ve en la ficha interna y en ninguna página pública (test).
- [ ] Al subir, la pregunta de autorización está y queda registrada con quién y cuándo.
- [ ] Borrar la foto la saca del almacenamiento.

**Verificación:** verde.
**Depende de:** T8.2.
**Archivos:** `src/torneo/models/inscripcion.py` y migración, vistas y plantillas del jugador y del profe, tests.
**Tamaño:** M.

### T8.5 Resultado y eventos del partido (dominio y modelo, B3)

**Descripción:** estado del partido (por jugar, en juego, terminado), eventos (gol, gol en contra sin jugador (P72), amarilla, roja), mejor jugador (P70), W.O. con el marcador de P23 y penales en la eliminación. Cada evento guarda quién y cuándo. El marcador sale de los eventos. Deshacer el último evento. Permisos: organización y mesa (P64).

**Aceptación:**

- [ ] Dos goles y un gol en contra dan el marcador correcto; deshacer quita solo el último.
- [ ] Un W.O. da el marcador de P23; un empate en la eliminación pide penales.
- [ ] Un jugador de otro equipo no puede figurar en un evento.

**Verificación:** verde.
**Depende de:** nada (se puede empezar en paralelo a T8.1).
**Archivos:** `src/torneo/models/fixture.py`, modelo Evento y migración, `src/torneo/servicios/partido.py`, `src/dominio/config.py` (reglas nuevas), tests.
**Tamaño:** M.

### T8.6 Ficha del partido en el celular (B3)

**Descripción:** pantalla para cargar el partido en vivo: botones grandes "Gol", "Amarilla" y "Roja", que abren la lista del equipo con dorsal y nombre; gol en contra, deshacer, mejor jugador, W.O., penales y cambio de estado. Si un jugador suspendido figura en el partido, se ve el aviso (cuando exista T8.9).

**Aceptación:**

- [ ] Se carga un partido completo desde un celular a 360 px, con un toque por evento más la elección del jugador.
- [ ] La mesa puede cargar; un usuario sin rol no.
- [ ] El partido terminado ya no se mueve en la reprogramación (PRO-10).

**Verificación:** verde, más una prueba a mano a 360 px.
**Depende de:** T8.5.
**Archivos:** vista, plantillas y JS mínimo de la ficha, `tests/torneo/test_ficha_partido.py`.
**Tamaño:** M.

### T8.7 Tabla de posiciones (B4, P26, P28, P34)

**Descripción:** en el dominio, tabla por categoría y serie: 3, 1 y 0 puntos; desempate en el orden de CONTEXTO 4.6, configurable; entre equipos que no jugaron entre sí, P34; mejor perdedor y mejor 3.º, P26; fair play desde las tarjetas; sorteo registrado por la organización (P28). Se muestra en la pestaña "Posiciones" interna.

**Aceptación:**

- [ ] Un test por criterio de desempate, en orden, incluido el caso de series cruzadas (H5).
- [ ] Un empate total muestra "Falta sorteo" hasta que la organización lo registra.
- [ ] La tabla de 6 y 7 equipos elige al mejor perdedor y al mejor 3.º según P26.

**Verificación:** verde.
**Depende de:** T8.5.
**Archivos:** `src/dominio/tabla.py`, `src/torneo/servicios/tabla.py`, plantilla de Posiciones, tests.
**Tamaño:** M.

### T8.8 Cruces de la eliminación desde la tabla (B6, P50)

**Descripción:** al terminar la fase de grupos de una categoría, la app propone los equipos de cada llave desde la tabla. Se pueden corregir a mano (T6.1) y se verifican antes de guardar, mostrando los choques si los hay.

**Aceptación:**

- [ ] Con la fase de grupos terminada, las llaves se proponen según la tabla 4.5.
- [ ] Con un sorteo pendiente o un partido sin jugar, no se propone nada y se dice por qué.
- [ ] Una propuesta que choca muestra el choque antes de guardar.

**Verificación:** verde.
**Depende de:** T8.7.
**Archivos:** `src/torneo/servicios/fixture.py`, vista del fixture, tests.
**Tamaño:** S.

### T8.9 Suspensiones (B5, P29, P74)

**Descripción:** en Sub 10 a Sub 17, la doble amarilla es roja, con la casilla "pagó Bs 30"; si no pagó, el jugador queda suspendido para el próximo partido. Roja directa y acumuladas: configurables, por defecto sin suspensión automática (P29). La organización puede marcar una suspensión a mano. Las categorías y el monto salen de la configuración.

**Aceptación:**

- [ ] Doble amarilla en Sub 12 sin pago: suspendido en el próximo partido; con pago, no.
- [ ] Doble amarilla en Sub 8 no suspende.
- [ ] Una suspensión a mano aparece en la ficha del partido siguiente.

**Verificación:** verde.
**Depende de:** T8.5.
**Archivos:** `src/dominio/suspensiones.py`, modelo y servicio, `src/dominio/config.py`, tests.
**Tamaño:** M.

### T8.10 Página pública en vivo: partidos, posiciones, goleadores y ficha (B7, P65, P71)

**Descripción:** como Copa Fácil: resultados del día en vivo, tabla de cada categoría y serie, goleadores por categoría y ficha del partido con goles, tarjetas y mejor jugador. Se actualiza sola cada minuto (HTMX). Jugadores como "Nombre I." con dorsal; nunca CI ni fecha de nacimiento.

**Aceptación:**

- [ ] Un gol cargado aparece en la página pública en el siguiente refresco.
- [ ] El test de privacidad recorre las páginas nuevas y no encuentra apellidos completos, CI ni fechas.
- [ ] Las vistas siguen importando solo modelos de la lista permitida.

**Verificación:** verde.
**Depende de:** T8.7.
**Archivos:** vistas y plantillas públicas, `tests/torneo/test_publico*.py`.
**Tamaño:** M.

### T8.11 Página pública: equipo, patrocinadores y caché (B7)

**Descripción:** página del equipo con escudo y plantel ("Nombre I." y dorsal), con foto solo si hay autorización; patrocinadores al pie. Cachear las páginas públicas unos 30 a 60 segundos (caché en memoria del proceso), con URL firmadas que duran más que la caché.

**Aceptación:**

- [ ] La foto de un jugador sin autorización no aparece; con autorización, sí.
- [ ] La segunda visita dentro del minuto no consulta la base (test con `django_assert_num_queries`).
- [ ] Las páginas internas no se cachean.

**Verificación:** verde, más una prueba de carga simple con 100 pedidos concurrentes contra un contenedor de 1 CPU, anotada en PROGRESO.md.
**Depende de:** T8.3, T8.4, T8.10.
**Archivos:** vistas y plantillas públicas, `src/rondo/settings.py` (caché), tests.
**Tamaño:** M.

### T8.12 PNG del fixture con el diseño 2026 (B8)

**Descripción:** el PNG del día por cancha con el diseño 2026: fondo, copa y adornos desde `src/torneo/static/png/`; escudos desde el club; patrocinadores desde el torneo; día, cancha, categorías, equipos y horas los pone la app. Para que `modern-screenshot` pueda leer las imágenes de R2, se sirven desde el mismo origen o con CORS en el bucket (paso en DESPLIEGUE.md).

**Aceptación:**

- [ ] El PNG se genera con las imágenes del diseño, los escudos y los patrocinadores, sin datos personales.
- [ ] Con un club sin escudo o un torneo sin patrocinadores, el PNG sale igual, sin huecos rotos.
- [ ] Sebastian lo comparte desde su Android (R45).

**Verificación:** verde, más la prueba en el celular.
**Depende de:** T8.3 y las imágenes del PSD (Sebastian).
**Archivos:** `src/torneo/static/png/`, `src/torneo/templates/calendario/png.html`, `src/torneo/views/png.py`, `tests/torneo/test_png.py`.
**Tamaño:** M.

```
T8.1 → T8.2 → T8.3 ─┬──────────→ T8.12
          └──→ T8.4 ┤
T8.5 → T8.6         │
  ├──→ T8.7 → T8.8  │
  │      └──→ T8.10 ┴→ T8.11
  └──→ T8.9
```

**Checkpoint de la fase 8:**

- [ ] Verde, más `pytest -m lento`.
- [ ] Un partido se carga desde el celular y aparece en la página pública, con la tabla y los goleadores al día.
- [ ] Ninguna página pública muestra CI, fecha de nacimiento, apellido completo ni fotos sin autorización.
- [ ] Revisión con `code-review-and-quality` y con `security-and-hardening` (subida de imágenes).
- [ ] PROGRESO.md al día, visto bueno de Sebastian y aviso de qué probar.

## Fase 9: pedido 2026, bloque C (durante el torneo)

> Planificada el 2026-10-12 desde `docs/PEDIDO_CLAUDE_CODE.md`, bloque C.

### T9.1 Retención: anonimizar también borra las fotos (P49, P76)

**Descripción:** `anonimizar_torneo` borra del almacenamiento las fotos de las personas que anonimiza (las que no están en otro torneo), y deja la autorización en falso.

**Aceptación:**

- [ ] Después de anonimizar, el almacenamiento no tiene ninguna foto de esas personas.
- [ ] Las fotos de quien sigue en otro torneo quedan.

**Verificación:** verde.
**Depende de:** T8.4.
**Archivos:** `src/torneo/servicios/retencion.py`, `tests/torneo/test_anonimizar.py`.
**Tamaño:** S.

### T9.2 Pantalla de suspendidos para la mesa

**Descripción:** lista de suspendidos de cada fecha (día de juego): jugador ("Nombre I." y dorsal), equipo, motivo y el partido que no puede jugar. Visible para la organización y la mesa.

**Aceptación:**

- [ ] Un jugador suspendido aparece en la lista del día de su próximo partido y desaparece después.
- [ ] La lista sale de las mismas reglas que T8.9.

**Verificación:** verde.
**Depende de:** T8.9.
**Archivos:** vista y plantilla, tests.
**Tamaño:** S.

**Checkpoint de la fase 9:**

- [ ] Verde, revisión con `code-review-and-quality`, PROGRESO.md al día y visto bueno de Sebastian.
