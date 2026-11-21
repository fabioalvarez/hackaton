FROM python:3.12-slim
ARG SIMULAR_FALLA=0
WORKDIR /app
COPY app.py /app/app.py
COPY pedidos.json /data/pedidos.json
ENV DATA_PATH=/data/pedidos.json PYTHONUNBUFFERED=1 SIMULAR_FALLA=${SIMULAR_FALLA}
USER 10001
EXPOSE 8080
CMD ["python", "app.py"]
