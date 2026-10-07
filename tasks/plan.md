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
- [ ] T0.5 Deploy repetible en Render con Neon (demo) *(necesita pasos tuyos)*
- [ ] T0.6 Prueba de riesgo: OR-Tools en Render
- [ ] T0.7 Prueba de riesgo: PNG y compartir desde el celular

**Checkpoint de la fase 0:**

- [ ] Tests, mypy y ruff en verde.
- [ ] Entras con login a la URL de Cloud Run desde el celular.
- [ ] Están medidos los tiempos del solver con 1 y 2 vCPU, y quedó decidido el tamaño de la instancia.
- [ ] El PNG se compartió por WhatsApp desde tu celular. Si falla, se pasa al plan B con Pillow.
- [ ] Revisión con `code-review-and-quality` y tu visto bueno.

### Fase 1: configuración (día 1, tarde)

- [ ] T1.1 Dominio: modelos de configuración y reglas (CAT-01 a CAT-03)
- [ ] T1.2 Dominio: franjas con fechas concretas y compatibilidad resuelta (CAT-04)
- [ ] T1.3 Modelos Django de configuración
- [ ] T1.4 Comando `cargar_config` con la configuración 2026
- [ ] T1.5 Admin de la configuración e identidad del organizador

**Checkpoint de la fase 1:**

- [ ] El torneo 2026 está cargado en la demo, con 23 categorías-nivel, 5 canchas (incluidas C1A y C1B) y 15 franjas.
- [ ] Se edita en el admin, y una regla inválida se rechaza con un mensaje claro.
- [ ] Cada regla CAT tiene su test.
- [ ] Revisión y tu visto bueno.

### Fases 2 a 6: se detallan al llegar

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
