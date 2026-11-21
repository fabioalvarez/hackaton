"""Configura el entorno antes de importar la app en los tests."""
import os
from pathlib import Path

# Apunta el servicio al archivo de datos del repo (en lugar de /data en el
# contenedor) y fija un ID de instancia estable para las aserciones.
RAIZ = Path(__file__).resolve().parent.parent
os.environ.setdefault("DATA_FILE", str(RAIZ / "data" / "pedidos.json"))
os.environ.setdefault("INSTANCE_ID", "test-instance")
