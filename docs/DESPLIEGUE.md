# Despliegue

La demo corre en **Render, en el plan gratuito**, con la base en **Neon**. Es temporal, mientras la cuenta de Google Cloud está bloqueada (ver PROGRESO.md, decisión del 2026-10-07). La imagen Docker es la misma que se va a usar en Cloud Run.

| Pieza | Dónde | Región |
|---|---|---|
| App (`rondo-demo`) | Render, plan gratuito, Docker | Virginia (EE. UU.) |
| Base | Neon, proyecto `rondo-jmp`, rama `demo` | AWS us-east-1 (N. Virginia) |

La app y la base van en la misma región para que cada consulta tarde milisegundos, no 120 ms.

## Una sola vez

### 1. Base en Neon

1. Borra el proyecto `rondo-jmp` de São Paulo, que está vacío. Neon no deja cambiar la región de un proyecto.
2. Crea un proyecto nuevo:
   - Nombre: `rondo-jmp`.
   - Región: **AWS US East 1 (N. Virginia)**.
   - Postgres 18.
   - Base: `rondo`.
   - Neon Auth: apagado.
3. En **Branches**, crea la rama **`demo`** a partir de `production`. `production` queda para los datos reales (fase 6).
4. En **Connect**, elige la rama `demo`, la base `rondo` y **desactiva "Connection pooling"**. Django mantiene sus propias conexiones. Copia esa cadena, que empieza con `postgresql://`. **No la pegues en el chat ni en el repo:** va solo en el paso 2.

### 2. Servicio en Render

1. En Render: **New → Blueprint**. Conecta el repo `Tiesol/rondo`; Render lee `render.yaml`.
2. Te pide `DATABASE_URL`: pega ahí la cadena de la rama `demo`. `SECRET_KEY` la genera Render.
3. **Apply**. El primer build tarda unos minutos. Al arrancar, el contenedor corre las migraciones.

A partir de ahí, cada merge a `main` despliega solo (`autoDeploy`).

### 3. Primer usuario

El plan gratuito de Render no tiene consola, así que el usuario se crea desde tu máquina contra la base de Neon. Los `read -s` evitan que la cadena y la contraseña queden en el historial de la terminal:

```bash
read -rs -p "Cadena de conexión de la rama demo: " DATABASE_URL; echo
read -rs -p "Contraseña para el usuario: " RONDO_CLAVE_USUARIO; echo
DATABASE_URL="$DATABASE_URL" RONDO_CLAVE_USUARIO="$RONDO_CLAVE_USUARIO" \
  RONDO_ENV_FILE= DEBUG=true SECRET_KEY=local \
  uv run python manage.py crear_usuario sebastian --admin
unset DATABASE_URL RONDO_CLAVE_USUARIO
```

Para las demás personas, lo mismo con su rol en lugar de `--admin`: `crear_usuario ana --rol organizacion` o `crear_usuario mesa1 --rol mesa`. Solo `--admin` entra al admin de Django; los demás usan las pantallas de la app.

### 3b. Configuración del torneo 2026

Igual que el usuario: desde tu máquina, contra la rama `demo`. Se puede repetir sin duplicar nada. Pero ojo: **pisa lo que se haya editado en el admin** en categorías, canchas y reglas. Las franjas de entre semana se conservan.

```bash
read -rs -p "Cadena de conexión de la rama demo: " DATABASE_URL; echo
DATABASE_URL="$DATABASE_URL" RONDO_ENV_FILE= DEBUG=true SECRET_KEY=local \
  uv run python manage.py cargar_config datos/config/jmp_cup_2026.json
unset DATABASE_URL
```

### 3c. Clubes y datos de demo

Desde tu máquina, contra la rama `demo` (necesita las dependencias de desarrollo, por `faker`; `uv sync` las instala). `generar_demo` arma 93 equipos con jugadores y profes **inventados**, con la forma de 2023. Se puede repetir: borra y rehace solo los datos de demo. Se niega si la base tiene equipos o personas de un torneo que no es de demo.

```bash
read -rs -p "Cadena de conexión de la rama demo: " DATABASE_URL; echo
DATABASE_URL="$DATABASE_URL" RONDO_ENV_FILE= DEBUG=true SECRET_KEY=local \
  uv run python manage.py generar_demo --soy-la-demo
unset DATABASE_URL
```

Carga también el catálogo de clubes (`cargar_clubes`) y la configuración 2026, y deja el torneo marcado como de demo y con su página pública encendida.

### 3d. Fin de año: datos personales (P49)

Cuando el torneo termina, sus datos personales se borran con `anonimizar_torneo <id> --confirmo` (no se puede deshacer). Quedan los planteles como "Jugador 1, 2…" con su dorsal, y los equipos y el calendario intactos. A quien también esté en otro torneo no se lo toca. Se niega con un torneo que todavía no terminó.

### 4. Verificación

Abre `https://rondo-demo.onrender.com` (o la dirección que muestre Render) desde el celular y entra con ese usuario.

## Lo que hay que saber del plan gratuito

- **Se duerme a los 15 minutos sin visitas** y tarda cerca de **1 minuto** en despertar. Antes de mostrar la demo, ábrela un rato antes.
- 512 MB de RAM y 0,1 CPU. La app sola usa unos 70 MB. Falta medir el solver (T0.6).
- 750 horas al mes y 5 GB de tráfico.

## Probar la imagen en local

```bash
docker compose up -d db
docker build -t rondo:local .
docker run --rm --network host -e PORT=8766 -e DEBUG=false \
  -e SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')" \
  -e DATABASE_URL=postgres://rondo:rondo@localhost:5432/rondo rondo:local
# En modo producción redirige a HTTPS; para probar sin proxy:
curl -H 'X-Forwarded-Proto: https' http://localhost:8766/cuentas/login/
```
