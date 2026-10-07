# Para que Sebastian revise

El 2026-10-07, Sebastian autorizó seguir con el desarrollo completo, fase tras fase, sin esperar su visto bueno entre fases (solo esta vez). Cada duda se resolvió con un supuesto, que queda anotado acá para revisarlo a la vuelta.

Los límites de SPEC.md siguen valiendo: sin dependencias nuevas fuera de las ya aprobadas, sin producción, sin nada que tenga costo y sin datos reales.

**Cómo leerlo:** cada fila tiene un número (R1, R2…), la tarea donde surgió, qué hay que revisar y el supuesto que se tomó mientras tanto. Si el supuesto está bien, alcanza con borrar la fila. Si no, se cambia y se anota en PROGRESO.md.

## Pendientes de revisión

| # | Tarea | Qué revisar | Supuesto tomado |
|---|---|---|---|
| R1 | TU.1 | Navegar con el teclado y mirar la interfaz en tu celular. Yo lo revisé con capturas de Firefox a 360 y 1024 px, en claro y en oscuro, no en un teléfono real | Los controles son nativos (enlaces, botones, campos y `<dialog>`), así que el teclado funciona sin código extra. El muestrario está en `/diagnostico/componentes/` (solo staff) |
| R2 | TU.1 | El modo oscuro sigue al del sistema. No hay un botón para cambiarlo a mano | Alcanza con seguir al sistema |
| R3 | TU.1 | "Salir" quedó en la barra superior. El prototipo no lo mostraba | Es el lugar más fácil de encontrar en el celular |
| R4 | TU.1 | Los colores del organizador no pintan la interfaz todavía. El color guardado por defecto es el verde que se rechazó | TU.7 los conecta: el color principal reemplaza al azul marino y se agrega un color de acento, con el azul y el dorado como valores por defecto |
| R5 | TU.2 | Los usuarios de la organización ya no son staff: no entran al admin de Django. Solo entra quien se crea con `--admin` (tú) | Con las pantallas propias, el admin queda como herramienta técnica |
| R6 | TU.2 | No hay pantalla para invitar personas ni cambiarles el rol: se hace con `crear_usuario --rol` (DESPLIEGUE.md, paso 3) | Son 2 o 3 personas; una pantalla de invitaciones queda para antes de la fase 6 |
| R7 | TU.2 | Los usuarios que ya existían en la demo sin grupo pasaron a Organización con la migración 0005 | Hasta ahora, `crear_usuario` creaba solo usuarios de la organización |
| R8 | TU.3 | Los títulos y las ayudas de las 17 reglas (pantalla de reglas). Los escribí a partir del catálogo de SPEC.md y de las preguntas P | Textos cortos en español, con "tú". Si uno no se entiende, se cambia en `src/dominio/config.py` y la pantalla lo toma sola |
| R9 | TU.3 | La pantalla de reglas está en `/torneos/<id>/reglas/`. Todavía no hay un enlace desde Inicio: llega en TU.5 | — |
| R10 | TU.4 | El asistente no tiene la opción "desde cero" del prototipo: siempre parte de la plantilla del reglamento 2026 | Para la demo alcanza la plantilla. Desde cero hace falta cargar categorías a mano, y eso es más trabajo que destildar |
| R11 | TU.4 | En el asistente, las canchas no se editan (se muestran como vienen) | Cambiar la división de C1 o C2 rompe la compatibilidad de Sub 5 y Sub 6. Queda para cuando se responda P13 |
| R12 | TU.4 | El asistente no deja crear un torneo con el mismo nombre y año que otro | Así no se pisa uno existente por error |
| R13 | TU.4 | En el celular angosto (menos de 420 px), la barra superior esconde el rol y deja solo el ícono de "Salir" | El título de la pantalla entra entero; el rol se ve en "Más" |
| R14 | TU.5 | El "torneo activo" es el más reciente (por año y fecha de inicio). No hay forma de elegir otro | Hay un torneo por año |
| R15 | TU.5 | Pendientes de Inicio: "N categorías sin equipos" y "16 reglas esperan la respuesta del organizador" (todas las que tienen una P) | No hay registro de qué preguntas ya se respondieron. Cuando lleguen las respuestas, se puede marcar cada regla como confirmada |
| R16 | TU.5 | Los ajustes de una categoría se editan en Torneo → Ajustes: plantel mínimo y máximo, minutos por tiempo, convocados y canchas. La modalidad y la edad no se editan ahí | Cambiar la modalidad o la edad es cambiar de categoría; eso va en el asistente o en el JSON |
| R17 | TU.6 | La página pública está en `/t/<número>/`, no en una dirección con nombre (como `/jmp-cup-2026`) | Alcanza para la demo. Una dirección con nombre se agrega antes de la fase 6 si hace falta |
| R18 | TU.6 | Un torneo nuevo nace sin página pública; la organización la enciende en "Más" | Así nada se publica por accidente |
