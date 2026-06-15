# ==========================================
# Etapa 1: Constructor (Builder Nativo)
# ==========================================
# Forzamos que corra en la plataforma nativa del host del runner para máxima velocidad
FROM --platform=$BUILDPLATFORM ghcr.io/astral-sh/uv:python3.13-slim AS builder

# Evitar la generación de archivos .pyc en la etapa de compilación
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Argumentos automáticos provistos por Docker Buildx durante builds multiplataforma
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# Sincronizar dependencias. Pasamos `--target-platform` a uv para que haga cross-compilation limpia
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --target-platform "$TARGETPLATFORM"

# ==========================================
# Etapa 2: Imagen Final de Producción (Multi-arquitectura)
# ==========================================
# Esta base se descargará en amd64 o arm64 según corresponda
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Inyectar el entorno virtual generado directamente al PATH
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Instalar dependencias del sistema operativo (FFmpeg)
# Se limpia la caché de apt inmediatamente en la misma capa para reducir espacio
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar el entorno virtual aislado generado en la etapa anterior
COPY --from=builder /app/.venv /app/.venv

# Copiar el código fuente de la aplicación
COPY main.py /app/main.py
COPY app/ /app/app/

# Crear un usuario del sistema sin privilegios por seguridad
RUN useradd -u 8888 appuser && chown -R appuser:appuser /app
USER appuser

# Declarar el punto de entrada invocando el intérprete del entorno virtual
CMD ["python", "main.py"]