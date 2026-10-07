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
