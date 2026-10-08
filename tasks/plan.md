# Plan de implementación: app de la JMP CUP

> **Estado: aprobado por Sebastian el 2026-10-06, con las dependencias listadas.** Se basa en [SPEC.md](../SPEC.md) (aprobada) y en [docs/ARQUITECTURA.md](../docs/ARQUITECTURA.md) (aprobada). Las tareas están en [todo.md](todo.md).

## Resumen

Las fases 0 y 1 están detalladas tarea por tarea. Las fases 2 a 6 quedan como índice y se detallan al llegar a ellas, con lo que se haya aprendido hasta ahí.

En la fase 0 se atacan primero los tres riesgos técnicos:

1. que el deploy en Cloud Run con Neon funcione y se pueda repetir;
2. que OR-Tools corra en Cloud Run a una velocidad aceptable;
3. que el PNG se genere y se comparta desde el celular.

Si alguno falla, se cambia el plan el día 1 y no el día 4.

## Decisiones para este plan

- **Dependencias.** Se piden al aprobar este plan:
  - **Producción:** `django`, `django-htmx`, `whitenoise`, `gunicorn`, `psycopg[binary]`, `dj-database-url`, `pydantic` y `ortools`.
  - **Desarrollo:** `pytest`, `pytest-django`, `hypothesis`, `mypy`, `django-stubs` y `ruff`.
  - **Más adelante:** `faker`, recién en la fase 2.
  - **En el navegador,** copiadas dentro del repo sin CDN: `htmx` y `modern-screenshot`. Tailwind CSS v4 se compila con su ejecutable propio, sin Node.
- **Configuración por variables de entorno:** `DATABASE_URL`, `SECRET_KEY`, `DEBUG` y `ALLOWED_HOSTS`. En local salen de `.env`; en Cloud Run, de Secret Manager.
- **Migraciones en la nube:** se corren como un Cloud Run Job antes de cada deploy, no al arrancar el contenedor. Así nunca hay dos migraciones a la vez.
- **Usuarios iniciales:** un comando `crear_usuario` que toma la contraseña de una variable de entorno y no la imprime nunca.
- **Pruebas de riesgo:** viven detrás del login, en `/diagnostico/`, solo para staff. Se borran al cerrar la fase 4.

## Índice de tareas

### Fase 0: cimientos (día 1, mañana)

- [x] T0.1 Proyecto Python con herramientas de calidad
- [x] T0.2 Proyecto Django con settings por entorno
- [x] T0.3 Login y plantilla base para el celular
- [x] T0.4 Guardas del repo: dominio sin Django y chequeo antes de cada commit
- [x] T0.5 Deploy repetible en Render con Neon (demo) *(necesita pasos tuyos)*
- [x] T0.6 Prueba de riesgo: OR-Tools en Render
- [ ] T0.7 Prueba de riesgo: PNG y compartir desde el celular

**Checkpoint de la fase 0:**

- [x] Tests, mypy y ruff en verde.
- [x] Entras con login a la URL de la demo (Render) desde el celular.
- [x] Están medidos los tiempos del solver con los límites de Render (H6 en PROGRESO.md).
- [ ] El PNG se compartió por WhatsApp desde tu celular. Si falla, se pasa al plan B con Pillow.
- [x] Revisión con `code-review-and-quality` (ver PROGRESO.md).
- [ ] Tu visto bueno.

### Fase 1: configuración (día 1, tarde)

- [x] T1.1 Dominio: modelos de configuración y reglas (CAT-01 a CAT-03)
- [x] T1.2 Dominio: franjas con fechas concretas y compatibilidad resuelta (CAT-04)
- [x] T1.3 Modelos Django de configuración
- [x] T1.4 Comando `cargar_config` con la configuración 2026
- [x] T1.5 Admin de la configuración e identidad del organizador

**Checkpoint de la fase 1:**

- [ ] El torneo 2026 está cargado en la demo, con 23 categorías-nivel, 5 canchas (incluidas C1A y C1B) y 15 franjas. *(Probado en local; en la demo lo corre Sebastian.)*
- [x] Se edita en el admin, y una regla inválida se rechaza con un mensaje junto al campo.
- [x] Cada regla CAT tiene su test.
- [x] Revisión con `code-review-and-quality` (ver PROGRESO.md).
- [ ] Tu visto bueno.

### Fase 1b: pantallas propias (antes de la inscripción)

> Aprobada por Sebastian el 2026-10-07. Reemplaza al admin como pantalla del organizador, según `docs/DISENO.md`. El detalle está en [todo.md](todo.md).

- [x] TU.1 Base visual: tokens, plantilla y navegación
- [x] TU.2 Roles: Organización y Mesa de control
- [x] TU.3 Reglas del torneo con interruptores
- [x] TU.4 Crear torneo con el asistente
- [x] TU.5 Inicio y Torneo
- [x] TU.6 Página pública (base)
- [x] TU.7 Datos de la escuela

**Checkpoint de la fase 1b:**

- [x] El organizador crea el torneo 2026 y edita sus reglas sin tocar el admin ni la terminal.
- [x] La mesa entra con su rol y ve los avisos donde no tiene permiso.
- [x] La página pública se abre sin login y no muestra datos personales.
- [x] Revisión con `code-review-and-quality` (ver PROGRESO.md).
- [ ] Tu visto bueno (pendiente a tu vuelta: REVISAR.md).

### Fase 2: inscripción (día 2)

> Se avanza con la autorización general del 2026-10-07 (sin visto bueno entre fases; dudas en `docs/REVISAR.md`). El detalle está en [todo.md](todo.md).

- [x] T2.1 Dominio: normalización de documentos (INS-04)
- [x] T2.2 Dominio: validaciones de inscripción (INS-02, 03, 05 a 10)
- [x] T2.3 Modelos de inscripción, y datos personales fuera de los logs
- [x] T2.4 Servicio de inscripción
- [x] T2.5 Pantallas: equipos
- [x] T2.6 Pantallas: jugadores y cuerpo técnico, con avisos en vivo
- [x] T2.7 Generador de datos de demo

**Checkpoint de la fase 2:**

- [x] Se cumplen los criterios de inscripción de la sección 10, con un test por regla INS.
- [x] La demo tiene unos 80 equipos inventados (93), y ningún dato personal aparece en los logs. *(Probado en local; en la demo lo corre Sebastian: DESPLIEGUE.md, 3c.)*
- [x] Revisión con `code-review-and-quality` (ver PROGRESO.md).
- [ ] Tu visto bueno (pendiente a tu vuelta: REVISAR.md).

### Fase 3: fixture y verificador (día 3)

> Planificada el 2026-10-07. Se avanza con la autorización general del mismo día. El detalle está en [todo.md](todo.md).

- [x] T3.1 Formatos como datos (FIX-01, FIX-02, FIX-07)
- [x] T3.2 Dominio: cruces de la fase de grupos (FIX-03 a FIX-05)
- [x] T3.3 Dominio: sorteo de series y fixture completo (FIX-06, FIX-08)
- [x] T3.4 Modelos Serie y Partido, y servicio de fixture (FIX-09)
- [x] T3.5 Pantallas: series y fixture
- [ ] T3.6 Dominio: verificador de choques y prueba 2023
- [ ] T3.7 Capacidad con flujo máximo y pantalla "Programar"

```
T3.1 → T3.2 → T3.3 → T3.4 → T3.5
                       └──→ T3.7
T3.6 (independiente: recibe cualquier calendario)
```

**Checkpoint de la fase 3:**

- [ ] Cada formato da de 8 a 27 partidos según corresponda, sin cruces repetidos ni equipos dos veces en una fecha.
- [ ] El verificador pasa la prueba 2023 por tipo: 2 de personas, 3 de cancha y 0 de compatibilidad.
- [ ] La capacidad de la demo se ve en pantalla.
- [ ] Revisión con `code-review-and-quality` y tu visto bueno.

### Fases 4 a 6: se detallan al llegar

| Fase | Tareas previstas |
|---|---|
| 2. Inscripción (día 2) | Normalización de CI (INS-04). Validaciones de edad, cantidad, cuerpo técnico, dorsal y CI repetido (INS-02 a INS-10). Modelos y formularios para el celular: club, equipo, jugadores y profes. Avisos en vivo con HTMX. Marca de "verificado". Generador de demo con `faker`, siguiendo los patrones de 6.4 |
| 3. Fixture y verificador (día 3) | `formatos.json` y su intérprete. Todos contra todos. Series cruzadas. Llaves con referencias. Sorteo de series. Persistencia y vista del fixture. Verificador con el caso 2023. Capacidad con flujo máximo |
| 4. Programador (día 4) | Modelo CP-SAT con las restricciones duras. Objetivo. Partidos sin ubicar con motivo. Corrida dentro del request, con bloqueo. Vista básica por día y cancha. Caso del tamaño de 2023 |
| 5. Reprogramación y calendario (día 5) | Bloqueos ACF. Suspensión y franjas entre semana. Propuestas diversas. Cambio manual verificado. Historial. Vistas por categoría y por club. Exportación PNG. PWA. Ensayo de la demo |
| 6. Producción 2026 | Ajustes con las respuestas del organizador. Rama `production` de Neon y servicio aparte. Backups. Usuarios. Revisión de seguridad. Asignación a mano de los cruces de eliminación |

## Grafo de dependencias

```
T0.1 → T0.2 → T0.3 → T0.5 → T0.6
         │             └──→ T0.7
         └→ T0.4
T0.2 → T1.1 → T1.2 → T1.3 → T1.4 → T1.5
```

T0.4 y T1.1 no dependen del deploy. Si el deploy se traba esperando tus cuentas, la fase 1 avanza igual.

## Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| El deploy se traba por permisos o configuración de Google Cloud | Alto | Lo hacemos juntos, paso a paso, y queda documentado en `docs/DESPLIEGUE.md`. Mientras tanto, la fase 1 avanza en local |
| OR-Tools anda lento con 1 vCPU | Medio | Se mide en T0.6. Si hace falta, se usan 2 vCPU, y el peor caso de costo sigue siendo bajo |
| La Web Share API no comparte archivos en algún celular | Medio | T0.7 lo prueba en Android y, si es posible, en un iPhone. El respaldo es la descarga |
| No se cumple el día por tarea | Medio | Se aplica el orden de recorte de ARQUITECTURA.md |

## Preguntas abiertas

- El PNG se prueba solo en Android: no hay un iPhone a mano.
- Las preguntas al organizador (P1 a P51) siguen abiertas. Ninguna bloquea las fases 0 y 1.
