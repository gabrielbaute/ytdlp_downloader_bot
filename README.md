# DOWNLOADER TELEGRAM BOT CON YTDLP

Este bot es una utilería para poder usar yt-dlp fuera la consola. Tiene sus limitaciones, la API de telegram no nos permite enviar archivos de más de 50mb (gratis que yo sepa) como mensajes para los bots. Pero para enviar reels, shorts, algunos tik-toks y videos cortos (que es el objetivo de este bot), así como el audio simplemente de los videos, va a funcionar.

El bot tiene un sistema de administración, de tal forma que solo los ID's autorizados por el administrador pueden realizar descargas. La persistencia de esos id's se hace mediante el PicklePersistence, que almacena los chats de forma segura en binario.

---

## ⚙️ Configuración y Variables de Entorno

La aplicación utiliza `pydantic-settings` para gestionar la configuración de manera centralizada. Dependiendo del entorno de ejecución, los directorios base de persistencia (donde se guardan los logs, el estado del bot mediante `PicklePersistence` y el binario descargado de `yt-dlp`) se adaptan automáticamente.

### Archivo `.env`
Crea un archivo `.env` en la raíz de tu proyecto basándote en la siguiente plantilla (o copia y modifica el .env.example):

```env
# ------------ TELEGRAM CONFIG ------------
TELEGRAM_BOT_TOKEN=tu_bot_token_de_botfather
TELEGRAM_CHAT_ID=tu_id_de_usuario_administrador

# ------------ TIMEOUTS CONFIG ------------
CONNECT_TIMEOUT=60
READ_TIMEOUT=60

```

* Ten en cuenta que la variable **`TELEGRAM_CHAT_ID`** actúa como la cuenta de administración principal. Solo este ID (y los chats explícitamente autorizados por él) podrán interactuar con el bot. Esto es para evitar que el bot sea en sí mismo público.

---

## 🖥️ Modos de Ejecución

El proyecto está diseñado de forma híbrida y puede operar de dos maneras distintas:

1. **Modo Escritorio / Local (Windows/Linux con GUI):** Al ejecutar el ciclo local o empaquetado, la aplicación levanta una interfaz gráfica basada en `tkinter` (`SettingsGUI`) para parametrizar las credenciales iniciales de forma visual, almacenando las rutas en la carpeta `~/.botdownloader` del usuario.
2. **Modo Servidor / Headless (Docker):** Al desplegarse en servidores de producción (como Ubuntu Server), el módulo gráfico se ignora perezosamente mediante un bloque de contingencia para evitar dependencias de ventanas (X11). Toda la persistencia es delegada a un volumen Docker montado de manera estricta.

---

## 🐋 Despliegue con Docker Compose (Recomendado)

El método de despliegue recomendado es usar el docker-compose que hemos colocado en este repositorio, sin embargo puedes construir el tuyo propio a conveniencia. Asegúrate además de copiar el archivo .env.example y adaptarlo con tu chat id y el token de tu bot.

### Requisitos Previos

Asegúrate de tener instalados en tu servidor Ubuntu:

* Docker Engine (v20.10+)
* Docker Compose v2

#### `docker-compose.yml`
Este compose te permitirá construir la imagen localmente.
```yaml
services:
  botdownloader:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: botdownloader
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - PYTHONUNBUFFERED=1
      - HOME_DIR=/app/data
      - UID=1000
      - GID=1000
    volumes:
      - ./data:/app/data
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    networks:
      - downloaderbot_net

networks:
  downloaderbot_net:
    name: downloaderbot_net
    driver: bridge
```

### Comandos para el Despliegue

1. **Ajustar permisos del directorio en el Host:**
Para asegurar que el contenedor (que corre internamente con el UID `1000`) pueda escribir sin problemas en la carpeta compartida, otorga la propiedad del directorio raíz de la aplicación a dicho usuario:
```bash
cd /opt
sudo git clone https://github.com/gabrielbaute/ytdlp_downloader_bot.git
cd ytdlp_downloader_bot
sudo chown -R 1000:1000 /opt/ytdlp_downloader_bot
```
2. **Construir e iniciar el contenedor en segundo plano:**
```bash
docker compose up -d --build
```
3. **Monitorear los logs en tiempo real (Bootstrap de la aplicación):**
```bash
docker compose logs -f
```

*Nota: Durante el primer arranque, verás cómo el bot autodetecta la ausencia de `yt-dlp`, descargando de forma automática el binario oficial ejecutable directamente dentro de tu volumen persistente (`./data/bin/yt-dlp`).*
4. **Detener el servicio:**
```bash
docker compose down
```

5. **Usar la imagen generada en github**
Si no deseas construir tu propia imagen, sino usar la última generada, puedes simplemente ejecutar este otro compose:
```yaml
services:
  botdownloader:
    # Apunta a la imagen oficial empaquetada en GitHub Packages (GHCR)
    image: ghcr.io/gabrielbaute/ytdlp_downloader_bot:latest
    container_name: botdownloader
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - PYTHONUNBUFFERED=1
      - HOME_DIR=/app/data
      - UID=1000
      - GID=1000
    volumes:
      - ./data:/app/data
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    networks:
      - downloaderbot_net

networks:
  downloaderbot_net:
    name: downloaderbot_net
    driver: bridge
```
---

## 🤖 Comandos del Bot en Telegram

El bot implementa un middleware de seguridad restringido. Al iniciar, solo el usuario configurado en `TELEGRAM_CHAT_ID` tiene acceso completo. Los comandos disponibles interactuando en el chat privado son:

### Comandos de Usuario / Descarga

* `/start` - Verifica el estado del sistema, comprueba la correcta inicialización del bot y da la bienvenida mostrando el nombre del usuario si cuenta con autorización.
* **Envío de Enlace (Texto plano):** Al enviar cualquier enlace válido (YouTube, Twitter/X, Instagram, TikTok, etc.), el bot interceptará el mensaje de forma asíncrona y desplegará un menú interactivo (`InlineKeyboardMarkup`) consultando el formato de salida deseado:
* 🎬 **Video**: Descarga el flujo completo en la mejor calidad disponible con audio integrado.
* 🎵 **Solo Audio**: Extrae la pista de audio y la convierte de manera nativa a formato `.mp3` usando FFmpeg.

### Comandos de Administración (Exclusivos)

* `/authorize <chat_id>` - Autoriza de forma persistente a un nuevo usuario o grupo para utilizar las funciones de descarga del bot. El identificador se guardará inmediatamente en el archivo persistente `bot_data.pickle`.
* `/install` - Fuerza una instalación limpia o reinstalación del binario ejecutable de `yt-dlp` directamente desde el repositorio oficial de sus desarrolladores.
* `/update` - Realiza una verificación *in-place* y actualiza el binario existente de `yt-dlp` a la última versión disponible lanzada por la comunidad, notificando el resultado en el chat.
* `/version` - Devuelve la versión actual instalada y operativa de `yt-dlp` corriendo en el entorno del servidor.