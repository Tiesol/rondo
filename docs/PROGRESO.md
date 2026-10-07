# PROGRESO: app de la JMP CUP

Bitácora para retomar el trabajo si una sesión se corta. Las reglas del negocio están en [CONTEXTO_JMP_CUP.md](CONTEXTO_JMP_CUP.md). Las preguntas P1 a P32 están en su sección 9; las nuevas siguen desde P33.

## Estado

- **Fase:** 1b, pantallas propias. Aprobada; TU.1 a TU.6 listas.
- **Siguiente paso:** TU.7 (datos de la escuela). Sebastian autorizó seguir fase tras fase sin su visto bueno (solo esta vez); las dudas van a [REVISAR.md](REVISAR.md), con el supuesto que se tomó.

## Para retomar (actualizado el 2026-10-07)

- **Dónde estamos:** las fases 0 y 1 están terminadas y revisadas. Falta solo el visto bueno formal de Sebastian. Está planificada la **fase 1b, pantallas propias** (TU.1 a TU.7 en `tasks/todo.md`), que va antes de la inscripción.
- **Próxima acción:** si Sebastian aprueba la fase 1b, empezar con **TU.1**, la base visual. Si no la aprobó, preguntarle antes de implementar.
- **Diseño:** seguir `docs/DISENO.md`. El prototipo aprobado, sin barra de avance, está en https://claude.ai/artifact/VacxSHvhh36heQY2xS8Q3a (copia en `docs/prototipo/prototipo-rondo.html`). La réplica del PNG está en https://claude.ai/artifact/H9uyeRSzhDwFj7CbfEMSKv.
- **Demo:** https://rondo-demo.onrender.com. Se despliega sola con cada merge a `main`. El repo es https://github.com/Tiesol/rondo.
- **Esperando a Sebastian (no bloquea la fase 1b):** respuesta a P54 (grupos con muchos equipos); correr `cargar_config` en la demo (DESPLIEGUE.md, 3b); capturas de la página de Copa Fácil. Las imágenes (logo, patrocinadores y escudos) quedan para después, junto con el PNG.

## Hecho

- 2026-10-06: lectura completa del contexto.
- 2026-10-06: contraste del calendario 2023 (6.3) con las reglas 4.4, 5 y 6.4, con un script descartable que quedó fuera del repo. Resultados en H1, H2 y H3.
- 2026-10-06: estimación de capacidad para 2026 con la configuración por defecto (H4).
- 2026-10-06: revisión de los planes gratuitos vigentes (tabla al final).
- 2026-10-06: propuesta de arquitectura, mapa de módulos y fases en [ARQUITECTURA.md](ARQUITECTURA.md). Aprobada.
- 2026-10-06: borrador de [SPEC.md](../SPEC.md), con el catálogo de reglas.
- 2026-10-06: Sebastian crea el proyecto `rondo-jmp` en Neon (São Paulo, Postgres 18, sin Neon Auth).
- 2026-10-06: repo privado en GitHub (`Tiesol/rondo`) con la documentación inicial en `main`.
- 2026-10-06: SPEC.md aprobada. Plan de las fases 0 y 1 en `tasks/`, pendiente de aprobación.
- 2026-10-06: T0.1 lista: uv con Python 3.14.7, Django 6.1.2, Pydantic 2.13 y Postgres 18.6 local. Pasan los tests, mypy y ruff.
- 2026-10-06: T0.2 lista: proyecto Django con settings por variables de entorno. `check --deploy` sin advertencias en modo producción, y sin `SECRET_KEY` no arranca.
- 2026-10-06: T0.3 lista: login obligatorio en toda la app, plantilla base con Tailwind 4.3 y HTMX 2.0.4, y comando `crear_usuario`, que valida la clave y no la muestra. Login revisado a 360 px. Falta mirar el inicio en un celular real.
- 2026-10-07: PR #1 a #4 (T0.1 a T0.4) fusionados en `main` con merge commits. `main` queda con la fase 0 hasta T0.4.
- 2026-10-07: T0.5 lista: la demo está en https://rondo-demo.onrender.com (Render gratis, Virginia), con Neon N. Virginia en la rama `demo`. Se despliega sola en cada merge a `main`. Sebastian entró con su usuario.
- 2026-10-07: el login no distingue mayúsculas en el usuario, porque el teclado del celular pone la primera sola. `crear_usuario` guarda los nombres en minúsculas.
- 2026-10-07: T0.6 lista. Medición del solver en un contenedor limitado como Render (0,1 CPU y 512 MB); ver H6.
- 2026-10-07: T0.7 lista para probar: `/diagnostico/png/` (solo staff) genera el PNG de un calendario de prueba de 1080 px con `modern-screenshot` 4.7.0, y lo comparte con la Web Share API o lo descarga. Falta la prueba de Sebastian en su Android.
- 2026-10-07: T1.1 lista: `dominio/config.py` (Pydantic, inmutable y sin claves desconocidas) y `datos/config/jmp_cup_2026.json` (4.1 y los valores por defecto). Pasan CAT-01 (años de nacimiento) y CAT-03 (turnos de 40, 50, 60 y 70), y se rechazan las configuraciones inválidas.
- 2026-10-07: T1.2 lista: `dominio/franjas.py` (15 franjas en UTC para 2026) y `dominio/canchas.py` (compatibilidad con la regla por categoría por encima de la de modalidad, y canchas físicas: C1 ocupa C1A y C1B). Todas las categorías-nivel de 2026 tienen alguna cancha.
- 2026-10-07: T1.3 lista: modelos Torneo, CategoriaNivel (con sus canchas compatibles), Cancha (con sus mitades) y Franja, y su migración. Las reglas y el cuerpo técnico se validan con el dominio en cada `save()`. Las restricciones (unicidad, máximo ≥ mínimo, fin > inicio) viven en la base.
- 2026-10-07: T1.4 lista: `manage.py cargar_config` pasa el JSON validado a la base en una transacción. Es idempotente: no borra categorías ni canchas, regenera las franjas regulares y conserva las de entre semana. Probado en local (23 categorías-nivel, 5 canchas y 15 franjas).
- 2026-10-07: T1.5 lista: admin de Torneo (con canchas y franjas en línea), CategoriaNivel (con canchas compatibles y turno) y Organizador (uno solo, con nombre y color). Las reglas inválidas muestran el error junto al campo. Se sacó "JMP" de las plantillas: ahora sale del Organizador.
- 2026-10-07: revisiones de cierre de las fases 0 y 1, y fase 2 planificada (T2.1 a T2.7 en `tasks/todo.md`), pendiente de aprobación.
- 2026-10-07: Sebastian aprueba la fase 1b.
- 2026-10-07: TU.1 lista: tokens de DISENO.md en `frontend/tailwind.css` (claro y oscuro), Bebas Neue y Figtree servidas desde la app, plantilla base con barra superior azul, barra inferior en el celular y lateral desde 900 px, y 13 parciales con su muestrario en `/diagnostico/componentes/`. El admin salió del menú. Capturas a 360 y 1024 px, en claro y en oscuro.
- 2026-10-07: TU.2 lista: grupos Organización y Mesa de control con permisos propios de Torneo (migraciones 0004 y 0005), decorador `requiere` que muestra "Solo la organización puede…" con un 403, `403.html` con el mismo diseño, `crear_usuario --rol`, el rol en la barra y la pantalla "Más" con las personas y su rol.
- 2026-10-07: TU.3 lista: cada regla de `dominio.config.Reglas` trae título, ayuda, grupo, P# e ID de regla; `describir_reglas()` deduce el tipo (sí/no, número con sus límites, opción, fecha o par) y el formulario se arma solo. Pantalla `/torneos/<id>/reglas/`, solo para la organización, con interruptores, contadores y listas.
- 2026-10-07: TU.4 lista: asistente de 4 pasos en `/torneos/nuevo/` (datos, categorías, horarios y reglas). Parte de `datos/config/jmp_cup_2026.json` (setting `PLANTILLA_TORNEO`), guarda las respuestas en la sesión, arma la configuración con `servicios/asistente.armar()`, la valida con el dominio y la carga con `cargar_configuracion`. Sin cambios crea lo mismo que `cargar_config`. No pisa un torneo con el mismo nombre y año.
- 2026-10-07: TU.5 lista: Inicio con el torneo activo (`Torneo.activo()`: el más reciente), sus pendientes (`servicios/pendientes.py`) y accesos, o la invitación a crearlo. Torneo en `/torneo/<categoría>/<pestaña>/`, con selector de categoría y pestañas por HTMX (solo se reemplaza `#categoria` y la URL cambia). Ajustes de la categoría (plantel, minutos, convocados y canchas), editables solo por la organización.
- 2026-10-07: TU.6 lista: página pública en `/t/<torneo>/<categoría>/<pestaña>/` (Partidos, Posiciones y Equipos, por ahora vacías), sin login y solo para torneos con `publico` encendido (migración 0006). La organización la enciende y apaga desde "Más". Tests que fallan si una plantilla pública nombra datos personales o si la vista importa un modelo que no está en la lista permitida.
- 2026-10-06: T0.4 lista: test de arquitectura (el dominio no importa Django) y hook antes del commit que rechaza listas reales y `.env`, y corre ruff y los tests rápidos. Las dos guardas se probaron con archivos trampa.

## Pendiente

- [ ] T0.1 a T0.7 (fase 0) y T1.1 a T1.5 (fase 1).
- [ ] Para la fase 0: facturación activa en la cuenta de Google Cloud de Sebastian, y el proyecto `rondo-jmp` en Neon (región São Paulo, sin las integraciones de GitHub ni de Vercel).
- [ ] Mandar al organizador las preguntas P33 a P51.

## Decisiones

| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-10-06 | Django 6.1 + HTMX, un solo servicio. El núcleo de dominio va en Python puro y tipado | El solver (OR-Tools CP-SAT) es nativo de Python: un backend en Python evita un segundo servicio solo para el solver. Las pantallas son formularios, tablas y un calendario para pocos usuarios, y eso no necesita una SPA; el contexto lo dice. Django trae login, admin, formularios y migraciones. Que Sebastian quiera practicar Python no fue un criterio |
| 2026-10-06 | Cloud Run y Neon, los dos en São Paulo | CPU real para el solver (2 vCPU) y requests de hasta 60 minutos, dentro de la capa gratuita. Pide tarjeta |
| 2026-10-06 | La prueba de 6.4 se separa por tipo de choque: personas 2, canchas 3 y compatibilidad 0 (con las canchas de 2023) | Ver H1, H2 y H3 |
| 2026-10-06 | La app se usa en el torneo 2026 | Suma la fase 6 (producción) después de la demo, con backups, usuarios y separación entre demo y producción |
| 2026-10-06 | Es una app web instalable en el celular (PWA). Funciona solo con conexión | Hay buena señal en la cancha, según Sebastian. Así los datos personales no quedan guardados en los teléfonos |
| 2026-10-06 | Todo va en cuentas de Sebastian: un proyecto dedicado en Google Cloud, con su tarjeta, y un proyecto en Neon. Se traspasan a JMP si compra la app | La idea es venderle la app a JMP; así el traspaso no obliga a volver a desplegar |
| 2026-10-06 | No se usa la configuración de Neon para Node (`neon link`, `neon.ts`, `neon deploy`) ni su MCP | La app es Python en Cloud Run: de Neon solo hace falta la cadena de conexión |
| 2026-10-06 | Sin crédito de prueba de Google Cloud. El tope de gasto aceptado es de unos 5 USD al mes | Sebastian ya usó Google Cloud. La capa gratuita vale igual para las cuentas pagas |
| 2026-10-06 | Tailwind CSS v4 en lugar de Pico CSS | Que la interfaz se vea bien es una prioridad, y Tailwind da control total del diseño, incluido el que pase el organizador (P32). Se compila sin Node |
| 2026-10-06 | Tailwind se compila con `django-tailwind-cli`, que descarga el ejecutable oficial (sin Node). El CSS generado no entra al repo: se compila en local y en el Docker | Aprobado por Sebastian |
| 2026-10-07 | Las imágenes (logo, patrocinadores y escudos) y el PNG definitivo quedan para después | Prioridad de Sebastian: avanzar con las pantallas |
| 2026-10-07 | Sin barra de avance en Inicio (configurado, inscripción, etc.); se quedan los pendientes | No le gustó a Sebastian |
| 2026-10-07 | Antes de la inscripción va una fase de pantallas propias (1b) que reemplaza al admin | La interfaz es una prioridad, y la inscripción se construye sobre esas pantallas |
| 2026-10-07 | La página pública entra en la demo, en una versión simple: partidos por día, posiciones y equipos, sin login y sin datos personales (P53) | Sebastian quiere que familias y clubes la vean como en Copa Fácil |
| 2026-10-07 | Interfaz con la identidad de la JMP CUP (azul marino y dorado), listas en lugar de tarjetas y contrato de diseño en `docs/DISENO.md` | El prototipo 1 se rechazó por feo, por tener demasiadas tarjetas y por usar un verde inventado |
| 2026-10-07 | El logo del organizador queda para la fase 5, con el diseño del PNG (P32) | El disco de Render gratis se borra en cada reinicio: una imagen subida se perdería. Hay que guardarla en la base o en un almacenamiento externo |
| 2026-10-07 | El organizador se crea como superusuario (`crear_usuario --admin`) | Un staff sin permisos no ve nada en el admin. Los roles finos (mesa sin staff) quedan para antes de la fase 6 |
| 2026-10-07 | `cargar_config` no corre al arrancar el contenedor: se corre a mano | Cada arranque pisaría lo que se edite en el admin |
| 2026-10-07 | Render gratis sirve para la demo. El programador real usa varios workers de CP-SAT. Antes de la fase 6 se revisa si hace falta más CPU | Medición T0.6 (H6) |
| 2026-10-07 | Claude hace `push` por HTTPS con las credenciales de `gh`, configurado solo en este repo | La clave SSH de Sebastian tiene contraseña, y así Claude puede trabajar solo sin pedirla |
| 2026-10-07 | Claude fusiona los PR con `gh` sin preguntar, si pasan los tests | Autorizado por Sebastian, para no frenar el avance |
| 2026-10-07 | Los PR se fusionan con merge commit, no con squash | Los PR van encadenados; con squash, el siguiente choca con las líneas que tocaron los dos |
| 2026-10-07 | El proyecto de Google Cloud `rondo-jmp` queda sin organización | Para traspasarlo a JMP alcanza con agregarlos como dueños y cambiar la facturación |
| 2026-10-07 | La demo va en Render (gratis, Virginia), y la base se rehace en Neon N. Virginia | La cuenta de facturación de Google Cloud quedó cerrada y bloqueada por un cobro rechazado de la tarjeta, y reabrirla requiere soporte. Render no pide tarjeta. La app y la base van en la misma región. Cloud Run sigue como destino cuando la cuenta esté en regla: es la misma imagen Docker |
| 2026-10-07 | Las migraciones corren al arrancar el contenedor, no como un Job aparte | Hay una sola instancia, y el plan gratuito de Render no tiene comando previo al deploy |
| 2026-10-07 | Seguir con todas las fases sin esperar el visto bueno de Sebastian entre fases, con las dudas en `docs/REVISAR.md` y supuestos mientras tanto | Pedido de Sebastian, solo por esta vez. Los límites de SPEC.md siguen valiendo |
| 2026-10-07 | Los tokens viven en `@theme` de Tailwind y el modo oscuro sigue al sistema. Las pestañas son enlaces, y la hoja inferior es un `<dialog>` | La URL refleja la pestaña, y `<dialog>` da el foco y el Esc sin código |
| 2026-10-07 | Los colores del organizador se conectan a los tokens en TU.7 | Hoy el color guardado por defecto es el verde rechazado |
| 2026-10-07 | Los roles son grupos de Django con permisos propios de Torneo (configurar, programar, inscribir y verificar). Solo el superusuario es staff y entra al admin | La organización y la mesa usan las pantallas propias. Reemplaza la decisión de crear al organizador como superusuario. Los usuarios que ya existían sin grupo pasaron a Organización |
| 2026-10-06 | Una instalación por cliente: si otra organización compra la app, tiene su propio proyecto en Google Cloud y en Neon, con su facturación y el mismo código. La base no separa clientes | Por ahora el único cliente es JMP. Así el modelo de datos queda simple y cada cliente queda aislado. Nada propio de JMP va en el código: nombre, logo y colores van en la configuración |

## Hallazgos

### H1. La prueba de 6.4 da "exactamente 2 choques" solo con tres condiciones

Con los profes de 6.4, el verificador encuentra los dos choques esperados de River Plate. Pero eso se cumple solo si:

1. **Se cuenta un choque por par de partidos**, no por persona. El del sábado (Sub 11 Av A a las 9:20 en C1 contra Sub 15 a las 10:00 en C3) involucra a dos profes. Contados por persona, serían 3 choques.
2. **"Seguidos" (P18) significa turnos consecutivos.** El domingo, River Plate tiene Sub 6 A a las 9:20 en C1A y Sub 8 Av a las 10:30 en C2: 35 minutos entre el final de uno y el inicio del otro, en canchas distintas. Si "seguidos" significara "sin un turno libre en medio", habría un tercer choque.
3. **La prueba mira solo personas (profes y jugadores).** El verificador completo encuentra además los choques de H2 y H3.

Los jugadores compartidos no agregan choques: los dos de River Plate (Sub 6 y Sub 7) caen en el mismo par de partidos que el profe del domingo.

### H2. El calendario 2023 tiene 3 choques de cancha

Con las duraciones de 4.4 y la regla de que C1 entera ocupa sus dos mitades:

- **Domingo, C1:** Sub 9 Av ocupa la cancha entera de 8:40 a 9:30 (turno), pero en C1A y C1B empiezan dos partidos de Sub 6 A a las 9:20. Son 10 minutos de solape en cada mitad.
- **Domingo, C3:** Sub 15 ocupa la cancha de 8:00 a 9:10 (turno de 70), pero Sub 12 A empieza a las 8:50. Son 20 minutos de solape. El sábado, Sub 15 sí tuvo sus 70 minutos.

O son errores del calendario hecho a mano, que es justo el problema que la app tiene que resolver, o en 2023 las duraciones eran otras. Sirven para la demo.

### H3. La compatibilidad de canchas de 2026 no vale para 2023

En 2023, Sub 10 Avanzado jugó dos partidos en C2. Con la configuración 2026 (F8 solo en C1), el verificador los marca. La prueba con datos de 2023 tiene que usar las canchas de 2023 (tabla 6.1).

### H4. La eliminación no entra en el último fin de semana

**Escenario supuesto:** los equipos de 2023, más Sub 14 Av (5 equipos), Sub 17 Av (4), Sub 15 Femenino (4) y un Inicial de 4 equipos en Sub 12, 13, 14, 15 y 17. En total son 117 equipos y 281 partidos.

| Canchas | Ocupación en todo el torneo | Eliminación | Disponible el último fin de semana |
|---|---|---|---|
| C1 + C2 (F7, F8 y mitades) | 162 h de 200 (81 %) | 55 h | 40 h |
| C3 (F11) | 76 h de 100 (76 %) | 21 h | 20 h |

En todo el torneo entra, pero muy justo. La eliminación no cabe en un solo fin de semana. Con el tamaño de 2023, la eliminación ya ocupa el 88 % de C1 + C2 del último fin de semana, antes de sumar las restricciones de profes y descansos. Hacen falta P13 (¿se parten C2 y C3?) y P33.

### H5. El desempate "solo entre ellos" no funciona en las series cruzadas

Con 6 y 7 equipos, los de una misma serie nunca se enfrentan. Entonces no hay "partidos entre ellos" y cualquier empate va directo a sorteo. Lo mismo pasa al comparar equipos de series distintas (mejor 3.º, mejor perdedor). No afecta a la demo, porque no hay resultados, pero la regla queda incompleta (P34).

### H6. El solver alcanza en Render para la demo, pero no sobra para 2026

Se usó un modelo CP-SAT sintético con la forma del real (T0.6): canchas con mitades, un turno libre entre partidos del mismo equipo, profes compartidos y franjas reales. Solo fase de grupos, con los formatos de 4.5. Se midió en Docker con `--cpus=0.1 --memory=512m`, lo mismo que da Render gratis.

| Instancia | CPU | Workers | Primer calendario válido | Memoria pico |
|---|---|---|---|---|
| Tamaño 2023: 84 equipos, 139 partidos, 4 fines de semana | 0,1 | 1 | 0,4 s | 91 MB |
| La misma, con 3 fines de semana o 36 profes compartidos | 0,1 | 1 | 0,4 a 0,5 s | 94 a 97 MB |
| Estimación 2026: 117 equipos, 191 partidos, 5 fines de semana | 0,1 | 1 | 0,7 s | 73 MB |
| Estimación 2026, en 4 fines de semana | completa | 1 | no encontró en 60 s | — |
| Estimación 2026, en 4 fines de semana | completa | 8 | 2,0 s | — |
| Estimación 2026, en 4 fines de semana | 0,1 | 8 | 94 s | 117 MB |

- **Para la demo, Render gratis alcanza de sobra.** La memoria nunca pasa de 120 MB.
- **El problema justo (2026 en 4 fines de semana) depende más de la estrategia que de la CPU:** con un solo worker no encuentra solución ni con CPU completa, y con 8 sí. El programador real va a usar varios workers, y además una solución inicial armada a mano como pista (*hint*) o una resolución por fin de semana.
- **Para el torneo real de 2026, 0,1 CPU queda corto** si hay que reprogramar rápido con el calendario lleno. Antes de la fase 6 hay que decidir entre Render Starter (0,5 CPU, de pago) y Cloud Run, si la cuenta queda en regla.
- La imagen pesa 1 GB, por OR-Tools, pandas y numpy. El build de Render tarda más, pero no hay límite que lo impida.

## Comentarios de Sebastian sobre la demo (2026-10-07)

- **PNG:** técnicamente funciona, pero no es el diseño que se quiere. Sebastian va a pasar el diseño de calendario de este año (P32).
- **Interfaz:** fea y poco intuitiva. El admin de Django ("Configuración") no sirve como pantalla del organizador: muestra reglas en JSON, "Usuarios" y "Grupos" sin explicar, y el "Organizador" se confunde con quién organiza. **Hacen falta pantallas propias**, con interruptores y números en lugar de JSON, y un flujo guiado: crear torneo → equipos → fixture → calendario. El admin queda solo como herramienta técnica.
- **Roles:** no está claro quién puede hacer qué. Hay que definir qué hace la organización y qué la mesa de control.
- **Imágenes:** el logo, los escudos de los equipos y quizá fotos de jugadores necesitan un almacenamiento persistente (un bucket). Las fotos de jugadores son datos de menores y no están en el contexto: hay que confirmar si hacen falta (P52).
- **Roles acordados:** Organización puede hacer todo. Mesa de control puede cargar equipos y listas, verificar jugadores y ver o exportar el calendario.
- **Prototipo de interfaz** al estilo de Copa Fácil, con mejoras (asistente para crear el torneo, reglas con interruptores, avisos al cargar listas, capacidad, propuestas de reprogramación): https://claude.ai/artifact/VacxSHvhh36heQY2xS8Q3a. Copia en `docs/prototipo/prototipo-rondo.html`. Pendiente: los comentarios de Sebastian.
- **Diseño del PNG (2026-10-07):** el organizador usa el de 2025, con una imagen por cancha y por día: fondo azul marino, filas amarillas (categoría, escudo, equipo, equipo, escudo, hora), panel dorado con "CANCHA N", la copa y "JMP CUP · N.ª EDICIÓN", y una franja de patrocinadores abajo. Réplica: https://claude.ai/artifact/H9uyeRSzhDwFj7CbfEMSKv (copia en `docs/prototipo/fixture-png.html`). Faltan las imágenes reales: copa o logo, escudos y patrocinadores.
- **Identidad visual:** azul marino y dorado, los colores de la JMP CUP. El prototipo verde no los respetaba.
- **Página pública (cambio de alcance):** Sebastian quiere que quienes entran a mirar (familias y clubes) vean algo como la página de Copa Fácil (https://copafacil.com/-78bk8). El contexto la dejaba para después de la demo (P53).

## Revisión de la fase 0 (2026-10-07, `code-review-and-quality`)

**Veredicto: aprobada.** El código es chico y sigue la spec. Quedan pendientes la prueba del PNG en Android y el visto bueno de Sebastian.

**Corregido en la revisión:**

- **Hook:** ningún test verificaba que `.env.example` pasara. Una mutación que lo bloqueaba seguía en verde, así que se agregó ese test.
- **Settings:** sin `DATABASE_URL`, el error era confuso (`Scheme '://' is unknown`). Ahora dice "Falta la variable de entorno DATABASE_URL", con su test.
- **Mutación comprobada:** quitar el `strip()` del login la detectan los tests.

**Pendiente para fases siguientes:**

- **Datos personales en los logs (fase 2, obligatorio):** los errores de Postgres incluyen los valores. Una violación de unicidad del CI dejaría el número en el log ("Key (ci)=(…) already exists"). Los duplicados de CI se validan antes de guardar, y se agrega un filtro de logs que no deje pasar el texto de errores de la base.
- **Roles (antes de la fase 6):** `crear_usuario` hace staff a todos, y con eso la mesa de control podría editar la configuración en el admin. Hace falta un usuario de mesa sin staff.
- **FYI:** `django-tailwind-cli` descarga el ejecutable oficial de Tailwind desde GitHub durante el build, y nosotros no verificamos su checksum. La imagen pesa 1 GB, por OR-Tools, pandas y numpy.

## Revisión de la fase 1 (2026-10-07, `code-review-and-quality`)

**Veredicto: aprobada.** Falta el visto bueno de Sebastian.

**Mutaciones:** se rompieron a propósito cuatro piezas clave para ver si los tests lo detectan.

| Mutación | Resultado |
|---|---|
| `cargar_config` borra también las franjas de entre semana | Detectada |
| La compatibilidad ignora la regla por categoría | Detectada (3 tests) |
| `Torneo.save()` guarda sin validar las reglas | Detectada |
| El Organizador no fija `pk=1` | **No la detectaba ningún test.** Se agregó uno: guardar otro organizador reemplaza al único |

**FYI:**

- `cargar_config` no borra categorías ni canchas que se saquen del JSON, porque podrían tener equipos. Si hace falta, se borran en el admin.
- El procesador de contexto hace una consulta por página para traer al Organizador. Es despreciable con 2 o 3 usuarios.

## Supuestos

Valores que no están en el contexto. Quedan como configuración:

- **Choque:** un par de partidos que no pueden convivir, con la lista de motivos (cancha, equipo, profe, jugador, bloqueo…). Se cuenta uno por par.
- **Compatibilidad:** la regla por categoría tiene prioridad sobre la regla por modalidad. Por ejemplo, Sub 6 es F7, pero juega en C1A o C1B.
- **CI:** para comparar se usan el número, el complemento y el prefijo "E-". La sigla de departamento se guarda, pero no se compara.
- **Franjas:** el partido tiene que terminar dentro de la franja; el cambio del último partido puede quedar afuera (P48).
- **Tiempo:** se guarda en UTC y se muestra en America/La_Paz (UTC−4, sin horario de verano). El programador trabaja en pasos de 5 minutos.
- **Partidos por día de un equipo:** como máximo 2 (P47).

## Preguntas nuevas para el organizador

| # | Pregunta | Por defecto |
|---|---|---|
| P33 | La eliminación no entra en el último fin de semana (H4). ¿Se pueden adelantar las semis al penúltimo? | Configurable: desde qué fin de semana empieza la eliminación. La app avisa antes de programar si no entra |
| P34 | ¿Cómo se desempata entre equipos que no jugaron entre sí (misma serie en series cruzadas, o mejor 3.º entre series)? | Se usan todos los partidos del grupo, con el mismo orden de criterios |
| P35 | ¿Cuánto tiempo necesita un profe para cambiar de cancha? Esto define "seguidos" en P18 | Al menos 10 minutos entre el final de un partido y el inicio del otro. Así quedan prohibidos los turnos consecutivos en canchas distintas |
| P36 | Jugadores en dos equipos: ¿alcanza con que los partidos no se pisen? | Sí |
| P37 | ¿Alguien puede ser jugador en un equipo y profe en otro (por ejemplo, un Sub 17 que dirige un Sub 6)? | Sí, y esos equipos no juegan a la vez |
| P38 | Bloqueo de la ACF: ¿incluye el traslado? ¿Puede afectar a varios equipos del club? | El organizador carga inicio y fin con el margen que quiera, y un bloqueo puede abarcar varios equipos |
| P39 | ¿Se puede cargar un jugador sin CI? | Sí, con el aviso "documento pendiente". Es obligatorio antes del primer partido |
| P40 | Cuerpo técnico: ¿cuántas personas de cada rol? | Hasta 3 en total, con un solo entrenador, obligatorio antes del primer partido |
| P41 | Sub 15 Femenino: ¿se valida el género? ¿Las chicas pueden jugar en las otras categorías? | No se registra el género; la mesa lo verifica con el documento |
| P42 | Jugar en una categoría mayor (P6): ¿hay un límite de años? | Sin límite, pero la app avisa si son más de 2 años |
| P43 | ¿Los penales de la eliminación necesitan más tiempo en el turno? | No |
| P44 | Un equipo que se inscribe tarde es uno de los problemas del contexto. ¿Se puede rehacer el fixture de una categoría que todavía no empezó? | Sí, mientras no tenga partidos jugados. Se reprograma solo esa categoría |
| P45 | ¿Cómo se arman las series: por sorteo, a mano o separando a los equipos del mismo club? | Sorteo automático que separa a los equipos del mismo club cuando se puede, editable antes de generar el fixture |
| P46 | Todos Santos cae el domingo 1 de noviembre (2.º fin de semana), y el lunes 2 es feriado. ¿Se juega ese fin de semana? ¿Se usa el lunes 2 para reprogramar? | Se juega normal. El lunes 2 se usa solo si se agrega una franja |
| P47 | ¿Cuántos partidos por día puede jugar un equipo como máximo (P17)? | 2 |
| P48 | ¿El último partido tiene que terminar antes del cierre de la franja? | Sí, el partido; el cambio de 5 minutos puede quedar afuera |
| P49 | ¿Cuánto tiempo se guardan los datos de los jugadores después del torneo? | Hasta fin de año; después se anonimizan y quedan los planteles sin nombres ni CI |
| P50 | Resultados y tabla quedan fuera de la demo, pero en 2026 la eliminación necesita saber quién pasa. ¿Cómo se definen los cruces? | El organizador calcula las posiciones como hasta ahora y asigna a mano en la app los participantes de cada partido de eliminación |
| P51 | ¿Cuántas listas se esperan en 2026 y quién las carga? A mano son unos 1.700 jugadores | La organización las carga con el formulario. Si no alcanza el tiempo, se agrega pegar filas copiadas de Excel |
| P52 | ¿Hace falta guardar fotos de los jugadores? Son datos personales de menores | No, hasta que se confirme y se defina quién las ve |
| P53 | ¿La página pública (calendario, fixture y posiciones sin login, como Copa Fácil) entra en la demo o queda para después? | **Respondida por Sebastian:** entra una versión simple, solo de lectura, sin datos personales |
| P54 | Con muchos equipos (por ejemplo, 24 en Sub 15) la categoría se divide en grupos A y B, y los mejores se cruzan después. ¿Desde cuántos equipos se divide, en cuántos grupos y de qué tamaño? ¿Todos contra todos dentro del grupo? ¿Cuántos pasan de cada grupo y cómo sigue (cuartos, semis, final)? | Configurable en `formatos.json`. Mientras no se responda, con más de 10 equipos la app avisa que falta el formato (P27) |

## Planes gratuitos (revisados el 2026-10-06)

| Servicio | Límites que importan |
|---|---|
| Neon (Postgres) | 1 GB por proyecto, según la pantalla de alta de Neon (los artículos de 2026 decían 0,5 GB), y 100 CU-hora por proyecto al mes. Se suspende a los 5 minutos sin uso y despierta solo. Tiene región en São Paulo |
| Supabase (Postgres) | 500 MB. El proyecto se pausa a los 7 días sin uso y hay que reactivarlo a mano |
| Render (web) | 512 MB y 0,1 CPU. Se duerme a los 15 minutos y tarda alrededor de 1 minuto en despertar. Su Postgres gratis vence a los 30 días. No tiene región en Sudamérica |
| Koyeb (web) | 512 MB y 0,1 vCPU. Se duerme tras 1 hora sin tráfico y despierta en 1 a 5 segundos. Regiones: Washington o Frankfurt |
| Google Cloud Run | Gratis cada mes: 180 mil vCPU-segundos, 360 mil GB-segundos y 2 millones de requests. Requests de hasta 60 minutos. La CPU se corta al responder, salvo con facturación por instancia. Tiene región en São Paulo. Pide tarjeta, pero solo para verificar la identidad (es una retención temporal). Las cuentas nuevas reciben 300 USD de crédito por 90 días y, al terminar la prueba, no hay cobro automático: si no se activa la cuenta paga, los servicios se apagan |
| Vercel (Hobby) | 300 segundos por función y 2 GB. Solo uso personal no comercial, y JMP cobra inscripciones |

Versiones: OR-Tools 9.15 tiene wheels para Python 3.14 en Linux x86_64. Django 6.1 (agosto de 2026) soporta Python 3.12 a 3.14 y pide PostgreSQL 15 o superior.
