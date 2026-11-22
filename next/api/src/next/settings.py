"""Configuration, read only from environment variables (no secrets)."""

import socket
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment variables: DATA_PATH, INSTANCE_ID, SERVICE_NAME, PORT, LOG_LEVEL."""

    data_path: Path = Path("/data/orders.json")

    instance_id: str = Field(default_factory=socket.gethostname)
    
    service_name: str = "Next"
    
    port: int = 8080
    
    log_level: str = "info"
