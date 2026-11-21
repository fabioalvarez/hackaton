Nodo Ruta — Persistencia, Backup y Restauración

Proyecto: Hackatón Nodo Ruta
Responsable: DBA — Persistencia y Recuperación de Datos
Tecnologías: Python, Amazon EFS, Amazon S3, AWS IAM, boto3
Estado: Implementación inicial — pendiente de pruebas e integración AWS

⸻

1. Objetivo

Implementar un mecanismo de persistencia, respaldo y recuperación de datos que permita garantizar que los pedidos almacenados por la aplicación Nodo Ruta sobrevivan a la recreación de sus instancias y puedan restaurarse ante pérdidas o alteraciones.

El sistema debe cumplir los siguientes requisitos:

* QA-02 — Recoverability: restaurar y verificar los datos en un tiempo máximo de 5 minutos.
* QA-03 — Durability: mantener los datos fuera de las instancias de la aplicación.
* QA-01 — Availability: permitir que las dos instancias consulten la misma fuente de datos.

La solución utiliza archivos JSON sobre Amazon EFS y respaldos versionados en Amazon S3.

2. Arquitectura de almacenamiento

Amazon EFS — Persistencia principal

Amazon Elastic File System proporciona almacenamiento persistente y compartido.

El archivo pedidos.json se almacena en EFS y ambas tareas de ECS Fargate lo consultan mediante montajes de solo lectura.

Esto permite que los pedidos sobrevivan a la destrucción o recreación de una instancia de la aplicación.

Amazon S3 — Respaldos

Amazon S3 mantiene copias independientes del archivo de pedidos.

Cada respaldo contiene:

* El contenido JSON original.
* La versión de los datos.
* La fecha y hora del respaldo en el nombre del objeto.
* Un hash SHA-256 almacenado como metadata.

El bucket debe tener habilitado el versionado.

Flujo de recuperación

1. El archivo original se encuentra en EFS.
2. backup.py crea un respaldo en S3.
3. Ante una alteración o pérdida, se selecciona un respaldo válido.
4. restore.py descarga y valida su contenido.
5. El archivo recuperado reemplaza al archivo de trabajo en EFS.
6. verify.py comprueba que versión y contenido coinciden.

3. Estructura del módulo

hackaton/
│
├── data/
│   └── pedidos.json
│
├── scripts/
│   ├── backup.py
│   ├── restore.py
│   └── verify.py
│
└── README-DBA.md

Descripción de los archivos

Archivo	Responsabilidad
data/pedidos.json	Contiene los pedidos y su versión
scripts/backup.py	Crea respaldos en Amazon S3
scripts/restore.py	Restaura respaldos desde S3 hacia EFS
scripts/verify.py	Comprueba versión e integridad
README-DBA.md	Documenta los procedimientos del DBA

4. Requisitos previos

Para utilizar los scripts se necesita:

* Python 3.9 o superior.
* Librería boto3.
* Un sistema de archivos Amazon EFS configurado.
* Un bucket Amazon S3 con versionado habilitado.
* Permisos IAM adecuados.
* Acceso al directorio donde se encuentra pedidos.json.

Instalar la dependencia:

pip install boto3

Los scripts utilizan las credenciales proporcionadas por el entorno AWS o por un perfil configurado localmente.

No se deben almacenar claves de acceso dentro del código ni del repositorio.

5. Variables de entorno

Los scripts utilizan dos variables principales.

Variable	Descripción
DATA_FILE	Ruta del archivo JSON activo
S3_BACKUP_BUCKET	Nombre del bucket que almacena los respaldos

Ejemplo en Linux:

export DATA_FILE="/data/pedidos.json"
export S3_BACKUP_BUCKET="nombre-del-bucket"

El valor del bucket es ilustrativo y debe reemplazarse por el nombre real configurado por infraestructura.

Para pruebas locales, DATA_FILE puede apuntar a un archivo del proyecto.

6. Procedimiento de backup

Archivo responsable: scripts/backup.py

Objetivo

Crear una copia versionada de los datos antes de realizar modificaciones.

Funcionamiento

1. Comprueba que pedidos.json existe.
2. Lee y valida su contenido JSON.
3. Obtiene el identificador de versión.
4. Calcula el hash SHA-256.
5. Genera una clave de respaldo con fecha UTC.
6. Guarda el contenido y su metadata en Amazon S3.
7. Registra la ubicación y el hash del respaldo.

Ejecución

python scripts/backup.py

Resultado esperado

El script registra la clave de un objeto similar a:

backups/pedidos-v1-20261121T140000000000Z.json

La clave debe conservarse para poder seleccionar ese respaldo durante la restauración.

Política inicial: realizar un respaldo antes de cada cambio de versión de los datos. La programación automática de respaldos no forma parte de los scripts actuales.

7. Procedimiento de restauración

Archivo responsable: scripts/restore.py

Objetivo

Recuperar un respaldo previamente almacenado en S3 y devolverlo a EFS.

Funcionamiento

1. Recibe la clave del respaldo seleccionado.
2. Descarga el archivo desde Amazon S3.
3. Valida su estructura JSON.
4. Comprueba que la versión coincide con la metadata.
5. Compara el SHA-256.
6. Crea un archivo temporal en EFS.
7. Reemplaza el archivo activo mediante una operación atómica.
8. Verifica el archivo restaurado.
9. Registra el tiempo total de recuperación.

Ejecución

python scripts/restore.py \
  --backup-key "backups/pedidos-v1-20261121T140000000000Z.json"

La clave mostrada es un ejemplo. Debe utilizarse la del respaldo real.

Consideraciones

La restauración modifica el archivo activo.

Por esta razón debe ejecutarse mediante un proceso administrativo autorizado, con permisos de escritura sobre EFS, y no desde las tareas de consulta de la aplicación.

Antes de ejecutar una restauración se debe confirmar que se seleccionó la versión correcta.

8. Verificación de integridad

Archivo responsable: scripts/verify.py

Objetivo

Comprobar independientemente que el archivo activo en EFS coincide con el respaldo seleccionado en S3.

Funcionamiento

1. Lee el archivo activo.
2. Descarga el respaldo.
3. Valida ambos archivos JSON.
4. Comprueba la versión registrada.
5. Calcula los hashes SHA-256.
6. Compara los resultados.
7. Informa si la verificación fue exitosa.

Ejecución

python scripts/verify.py \
  --backup-key "backups/pedidos-v1-20261121T140000000000Z.json"

Códigos de salida

Código	Significado
0	Verificación exitosa
1	Diferencias o error durante la verificación

Nota: el hash SHA-256 permite verificar la igualdad de los bytes y su coincidencia con la metadata registrada. No demuestra por sí solo que el respaldo sea auténtico frente a una modificación maliciosa de ambos elementos.

9. Prueba de recuperación — QA-02

Objetivo

Demostrar que los datos originales pueden recuperarse y verificarse en un máximo de 300 segundos.

Escenario de prueba

Estado inicial: archivo JSON con seis pedidos y versión v1.

Incidente simulado: modificación o alteración controlada del archivo activo.

Acción correctiva: restauración desde un respaldo válido almacenado en S3.

Procedimiento

1. Comprobar que el archivo original contiene los pedidos esperados.
2. Ejecutar backup.py.
3. Registrar la clave del respaldo creado.
4. Alterar el archivo activo de forma controlada.
5. Ejecutar verify.py y comprobar que detecta diferencias.
6. Iniciar la medición de recuperación.
7. Ejecutar restore.py usando el respaldo original.
8. Ejecutar nuevamente verify.py.
9. Consultar la API desde las dos instancias.
10. Registrar los resultados y el tiempo transcurrido.

Criterios de aceptación

* El respaldo original existe en S3.
* Los seis pedidos originales se recuperaron.
* La versión recuperada coincide con la esperada.
* Los hashes SHA-256 de EFS y S3 coinciden.
* Las instancias de la API pueden consultar los datos restaurados.
* La recuperación y verificación se completan dentro del límite establecido.

La medición integrada de la prueba debe incluir las comprobaciones necesarias para demostrar QA-02, no únicamente la descarga del archivo.

10. Permisos y seguridad

Permisos de respaldo

El proceso de backup necesita:

* Lectura del archivo en EFS.
* Permiso IAM s3:PutObject sobre los objetos de respaldo.

Permisos de restauración

El proceso de restore necesita:

* Permiso IAM s3:GetObject.
* Escritura sobre el directorio correspondiente de EFS.

Permisos de verificación

El proceso de verificación necesita:

* Lectura del archivo en EFS.
* Permiso IAM s3:GetObject.

Restricciones

* Las tareas ECS de consulta deben montar los datos en solo lectura.
* Los procesos administrativos deben utilizar permisos separados.
* No se deben publicar credenciales AWS.
* Los respaldos no deben exponerse públicamente.
* No se deben eliminar respaldos durante las pruebas sin verificar previamente su necesidad.

11. Integración con infraestructura

El responsable de Terraform deberá coordinar con el DBA la creación y configuración de:

* Amazon EFS y sus puntos de montaje.
* Bucket Amazon S3 y su versionado.
* Políticas y roles IAM.
* Montaje EFS de solo lectura en las dos tareas ECS.
* Acceso administrativo para backup y restore.

La ubicación exacta de los archivos y la región AWS se confirmarán durante la integración.

12. Estado de implementación

Componente	Estado
Definición inicial del JSON	Preparado, pendiente de validar con API
Script de backup	Código preparado
Script de restauración	Código preparado
Script de verificación	Código preparado
Documentación DBA	Preparada
Integración con EFS	Pendiente
Integración con S3	Pendiente
Permisos IAM	Pendiente
Pruebas automatizadas	Pendiente
Validación QA-02 en AWS	Pendiente

13. Resultado esperado

Al completar la integración y las pruebas, el módulo DBA deberá demostrar:

Persistencia: los datos sobreviven a la recreación de las instancias.

Respaldo: existe una copia independiente, versionada y recuperable en S3.

Restauración: el archivo original puede recuperarse después de una alteración.

Integridad: la versión y el contenido restaurados coinciden con el respaldo seleccionado.

Recuperabilidad: el procedimiento completo cumple el objetivo de recuperación de cinco minutos.

⸻

Responsable técnico: DBA — Hackatón Nodo Ruta

Nota: esta documentación describe la implementación propuesta. Su cumplimiento efectivo deberá confirmarse mediante pruebas reproducibles y evidencias de ejecución.
