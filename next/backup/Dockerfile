# Backup watcher: plain Python files with no dependencies. It is the only service that writes to the data volume.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY src .

CMD ["python", "main.py"]
