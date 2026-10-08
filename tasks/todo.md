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
- [ ] Desde la PC, se descarga. (Pendiente de prueba manual: la página ya está en la demo.)
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

- [ ] Suspender un día deja sus partidos pendientes y las propuestas los ubican en otros días, sin choques.
- [ ] Una franja entre semana nueva aparece en el calendario y se usa al reprogramar.

**Verificación:** verde.
**Depende de:** T5.3.
**Archivos:** servicio y vistas de suspensión y franjas, `tests/torneo/test_suspender.py`.
**Tamaño:** M.

### T5.6 PNG del día por cancha (criterio 6)

**Descripción:** una imagen de 1220 × 690 por cancha y por día, con el diseño de 2025 (`docs/prototipo/fixture-png.html`): fondo azul marino, filas doradas (categoría, escudo, equipo, equipo, escudo y hora), panel con "CANCHA N" y la edición, y franja de patrocinadores (con lugar reservado hasta que haya imágenes). Se comparte desde el calendario con la Web Share API, o se descarga. Reemplaza la página de prueba de T0.7.

**Aceptación:**

- [ ] Desde el calendario de un día, "Compartir" genera una imagen por cancha.
- [ ] Un test comprueba que la plantilla del PNG no usa datos personales.
- [ ] La página de prueba del PNG ya no está.

**Verificación:** verde, más una captura del PNG.
**Depende de:** fase 4.
**Archivos:** `src/torneo/templates/calendario/png.html`, `src/torneo/static/js/exportar.js`, `src/torneo/static/fuentes/`, `tests/torneo/test_png.py`.
**Tamaño:** M.

### T5.7 Vistas por categoría y por club

**Descripción:** el calendario se filtra por categoría y por club: la lista de partidos con día, hora y cancha. Es lo primero que se recorta si falta tiempo.

**Aceptación:**

- [ ] Por club: todos los partidos de sus equipos, en orden.
- [ ] Por categoría: sus partidos, en orden.

**Verificación:** verde.
**Depende de:** fase 4.
**Archivos:** vistas y plantillas del calendario, `tests/torneo/test_vistas_por_club.py`.
**Tamaño:** S.

### T5.8 Instalación en el celular (PWA) y ensayo de la demo

**Descripción:** manifest e íconos (generados, sin imágenes del organizador) para instalar la app en el celular; funciona solo con conexión (decisión del 2026-10-06), así que el service worker no guarda datos. Guion de la demo en `docs/DEMO.md` y un test de punta a punta: demo → fixtures → programar → bloqueo ACF → propuesta → aplicar → PNG.

**Aceptación:**

- [ ] El manifest se sirve y la app se puede instalar (Chrome la reconoce como PWA).
- [ ] El test de punta a punta pasa.
- [ ] `docs/DEMO.md` tiene el guion, con las preguntas prioritarias para el organizador (P13, P33, P35, P44, P46 y P50).

**Verificación:** verde, `pytest -m lento`.
**Depende de:** T5.3, T5.6.
**Archivos:** manifest, service worker, íconos, `docs/DEMO.md`, `tests/torneo/test_demo_de_punta_a_punta.py`.
**Tamaño:** M.
