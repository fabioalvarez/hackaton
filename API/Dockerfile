# Imagen del servicio Nodo Ruta (A8: versión fija por etiqueta de imagen).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias primero para aprovechar la caché de capas.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código de la aplicación.
COPY app ./app

# Versión de la imagen; se sobreescribe al construir: --build-arg APP_VERSION=v2
ARG APP_VERSION=v1
ENV APP_VERSION=${APP_VERSION}

# Usuario sin privilegios (buena práctica; CT-01).
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# El almacenamiento de datos se monta desde fuera (EFS en AWS, volumen en local)
# en DATA_FILE=/data/pedidos.json por defecto, en solo lectura.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
