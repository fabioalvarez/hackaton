# Cómo levantar la API — Nodo Ruta

Guía rápida para poner en marcha el servicio. Todos los comandos se ejecutan
desde la carpeta `API/`.

---

## Opción 1 — Docker Compose (recomendada)

Levanta las **2 instancias + el balanceador**, igual que el diseño en AWS.
Necesitas **Docker Desktop** abierto.

### 1. Entrar a la carpeta

```powershell
cd API
```

### 2. Construir y levantar

```powershell
docker compose up --build -d
```

> `-d` lo deja corriendo en segundo plano. Quita `-d` si quieres ver los logs en vivo.

### 3. Comprobar que responde

```powershell
curl http://localhost:8080/health
curl http://localhost:8080/pedidos
```

Punto de acceso: **http://localhost:8080**

| Ruta | Qué devuelve |
|------|--------------|
| `http://localhost:8080/` | Página de inicio |
| `http://localhost:8080/pedidos` | Los 6 pedidos + versión |
| `http://localhost:8080/health` | Estado del servicio |

### 4. Ver el estado de los contenedores

```powershell
docker compose ps
```

### 5. Ver los logs

```powershell
docker compose logs -f
```

### 6. Apagar

```powershell
docker compose down
```

---

## Opción 2 — Python directo (una sola instancia, para desarrollar)

Sin Docker. Útil para editar el código y ver cambios al instante. Necesitas
**Python 3.12+**.

### 1. Entrar a la carpeta

```powershell
cd API
```

### 2. Crear el entorno virtual e instalar dependencias

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Si PowerShell bloquea el script de activación, ejecuta una vez:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### 3. Levantar el servidor

```powershell
$env:DATA_FILE = ".\data\pedidos.json"
uvicorn app.main:app --reload --port 8000
```

Queda en: **http://localhost:8000** · Documentación OpenAPI: **http://localhost:8000/docs**

### 4. Apagar

Presiona `Ctrl + C` en la terminal.

---

## Probar los escenarios del reto (con Docker)

| Escenario | Comando | Qué deberías ver |
|-----------|---------|------------------|
| **PR-01** Normal | repetir `curl -i http://localhost:8080/pedidos` | el header `X-Instance-Id` alterna entre `instancia-a` e `instancia-b` |
| **PR-02** Caída | `docker compose stop instancia-a` y seguir consultando | el servicio sigue respondiendo con `instancia-b` |
| **PR-03** Recrear | `docker compose up -d --force-recreate instancia-a` | `/pedidos` sigue con los 6 pedidos |
| **PR-05** Defectuosa | `$env:FAIL_HEALTH="true"; docker compose up -d --force-recreate instancia-a` | el `/health` de esa instancia da **503** |

> Para dejar FAIL_HEALTH sin efecto otra vez:
> `$env:FAIL_HEALTH="false"; docker compose up -d --force-recreate instancia-a`

---

## Problemas frecuentes

| Síntoma | Causa / solución |
|---------|------------------|
| `Cannot connect to the Docker daemon` | Docker Desktop no está abierto. Ábrelo y espera a que diga *Running*. |
| `port is already allocated` (8080) | Otro proceso usa el 8080. Apaga lo que lo ocupe o cambia el puerto en `docker-compose.yml`. |
| `/pedidos` da error 500 | No encuentra el archivo de datos. Revisa que exista `data/pedidos.json`. |
| `uvicorn: command not found` | No activaste el entorno virtual (paso 2 de la Opción 2). |

---

## Variables de entorno

Se pasan desde fuera de la imagen (nunca van dentro):

| Variable | Por defecto | Para qué |
|----------|-------------|----------|
| `DATA_FILE` | `/data/pedidos.json` | Ruta del archivo de datos |
| `INSTANCE_ID` | *hostname* | ID de la instancia |
| `APP_VERSION` | `v1` | Versión de la imagen |
| `FAIL_HEALTH` | `false` | `true` simula una versión defectuosa (PR-05) |
