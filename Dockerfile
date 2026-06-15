# ==========================================
# Etapa 1: Constructor (Builder Nativo)
# ==========================================
FROM python:3.13-slim AS builder

# Evitar la generación de archivos .pyc en la etapa de compilación
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copiamos el binario de 'uv' directamente desde su imagen oficial optimizada
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Sincronizar dependencias usando la caché nativa de uv.
# Al no usar flags de cross-compilation, uv compilará de forma óptima para el host de Dokploy.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# ==========================================
# Etapa 2: Imagen Final de Producción
# ==========================================
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Inyectar el entorno virtual generado directamente al PATH
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Instalar dependencias del sistema operativo (FFmpeg es requerido por yt-dlp)
# Se limpia la caché de apt inmediatamente para reducir el espacio en disco
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar el entorno virtual aislado generado en la etapa anterior
COPY --from=builder /app/.venv /app/.venv

# Copiar el código fuente de la aplicación
COPY main.py /app/main.py
COPY app/ /app/app/

# Crear un usuario del sistema sin privilegios por seguridad (No-Root)
RUN useradd -u 8888 appuser && chown -R appuser:appuser /app
USER appuser

# Declarar el punto de entrada invocando el intérprete del entorno virtual
CMD ["python", "main.py"]