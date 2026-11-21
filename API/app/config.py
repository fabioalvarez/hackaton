"""Configuración del servicio, tomada desde variables de entorno.

Toda la configuración viene de fuera de la imagen (A7, CT-01): no hay valores
sensibles ni rutas fijas dentro del código ni del repositorio.
"""
import os
import socket


def _as_bool(valor: str) -> bool:
    return valor.strip().lower() in ("1", "true", "yes", "si", "sí")


class Settings:
    def __init__(self) -> None:
        # ID de la instancia que atiende la solicitud (RF-05, A4).
        # En ECS/Fargate se inyecta el ID de la tarea; si no, se usa el hostname
        # del contenedor, que es único por instancia.
        self.instance_id: str = os.getenv("INSTANCE_ID") or socket.gethostname()

        # Archivo de datos en el almacenamiento compartido (EFS en AWS),
        # montado en solo lectura. El servicio no guarda estado propio (A5).
        self.data_file: str = os.getenv("DATA_FILE", "/data/pedidos.json")

        # Versión de la imagen del servicio (A8). Útil para el rollback (QA-04).
        self.app_version: str = os.getenv("APP_VERSION", "v1")

        # Interruptor para simular una versión defectuosa: hace que /health
        # falle y así el despliegue pueda volver a la versión anterior
        # (A9, QA-04, prueba PR-05).
        self.fail_health: bool = _as_bool(os.getenv("FAIL_HEALTH", "false"))


settings = Settings()
