# ==========================================
# Etapa 1: Constructor (Builder Nativo)
# ==========================================
FROM python:3.13-slim AS builder

# Evitar la generación de archivos .pyc en la etapa de compilación
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Binario de 'uv' directamente desde imagen oficial
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Sincronización dependencias usando la caché nativa de uv.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
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

# Instalación de dependencias básicas (ffmpeg requerido por yt-dlp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Creación de usuario, grupo sin privilegios y directorio de persistencia unificado
RUN groupadd -r appuser -g 1000 && \
    useradd -r -u 1000 -g appuser appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app && \
    chmod 755 /app/data

# Copiar el entorno virtual asignando la propiedad al usuario ejecutor
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copiar el código fuente garantizando que appuser sea el propietario
COPY --chown=appuser:appuser main.py /app/main.py
COPY --chown=appuser:appuser app/ /app/app/

# Cambiamos al usuario no root por seguridad
USER appuser

# Declarar el punto de entrada invocando el intérprete del entorno virtual
CMD ["python", "main.py"]