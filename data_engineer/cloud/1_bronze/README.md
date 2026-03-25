# 🥉 Bronze Layer — Ingesta de Audios

Descarga archivos de audio (.wav) y los almacena en S3 como datos raw (sin procesar).

## Estructura

```
bronze/
├── local/                       # Scripts para subir desde tu PC
│   ├── 01_create_s3_buckets.py  # Crea los buckets S3
│   └── 02_upload_audios_to_s3.py # Sube audios locales
│
├── cloud/                       # Scripts cloud (Lambda Ingesta Inicial)
│   ├── 01_lambda_bronze.py      # Lambda: descarga de Google Drive → S3
│   └── 02_deploy_lambda_bronze.py # Despliega la Lambda en AWS
│
├── cloud_normalizer/            # 🚀 Scripts cloud (Lambda Normalización y Glacier)
│   ├── 01_lambda_normalizer.py  # Normaliza audios de S3 raw/ a norm/ (16kHz RMS 0.1)
│   ├── 02_deploy_lambda_normalizer.py # Despliega la Lambda y su Trigger de S3
│   └── 03_setup_s3_lifecycle.py # Crea regla Glacier para mover raw/ a los 0 días
│
└── README.md
```

## Fuentes de datos

| Categoría | Fuente |
|-----------|--------|
| Dementia | [Google Drive](https://drive.google.com/drive/folders/1GKlvbU57g80-ofCOXGwatDD4U15tpJ4S) |
| No Dementia | [Google Drive](https://drive.google.com/drive/folders/1jm7w7J8SfuwKHpEALIK6uxR9aQZR1q8I) |

## Uso

### Opción 1: Subir desde local
```bash
python local/01_create_s3_buckets.py
python local/02_upload_audios_to_s3.py
```

### Opción 2: Lambda Ingesta Automática desde Google Drive (Opcional)
```bash
python cloud/02_deploy_lambda_bronze.py
```
Después invoca la Lambda con:
```json
{
  "max_files": 2,
  "dementia_folder_id": "1GKlvbU57g80-ofCOXGwatDD4U15tpJ4S",
  "nodementia_folder_id": "1jm7w7J8SfuwKHpEALIK6uxR9aQZR1q8I"
}
```

### Opción 3: Desplegar Lambda Normalizador Automático 
(Detecta subidas de la Web App a la carpeta `raw/` y los normaliza a `norm/`)

> **⚠️ PRE-REQUISITO IMPORTANTE: Crear el Rol IAM**
> 1. Ve a la consola web de AWS -> IAM -> Roles -> **Create role**.
> 2. Tipo de entidad de confianza: **AWS service** -> Casos de uso: **Lambda** -> Siguiente.
> 3. En la barra de búsqueda busca y marca estas 2 políticas: 
>    - `AmazonS3FullAccess` (para leer de raw/ y escribir en norm/)
>    - `AWSLambdaBasicExecutionRole` (para poder escribir logs en CloudWatch)
> 4. Siguiente -> En "Role name" pon exactamente: **`tfm-lambda-s3-role`**
> 5. Dale a **Create role**.

Una vez creado el Rol, **Desde Consola (Terminal) local ejecuta:**
```bash
python cloud_normalizer/02_deploy_lambda_normalizer.py
```

> **⚡️ ¿Cómo funciona la "Magia" (S3 Event Notification)?**
> El script anterior configura automáticamente un "Chivato" (Trigger) en S3 llamado *S3 Event Notification*. 
> Funciona así: 
> 1. El usuario sube un audio a la Web App y ésta lo envía a la carpeta `raw/`.
> 2. S3 detecta una subida nueva y dice: *"¡Alguien ha subido algo a la carpeta raw/ y acaba en .wav!"*
> 3. Al coincidir con la regla, S3 "despierta" inmediatamente a la Lambda.
> 4. La Lambda descarga el audio, lo alinea a RMS 0.1 y lo guarda en la carpeta `norm/` para que SageMaker pueda leerlo mañana muy rápido y con alta calidad.

**Opción Manual en Web AWS:**
1. Crear Lambda en la consola con Python 3.12 y el IAM Role `tfm-lambda-s3-role`
2. Copiar el código de `01_lambda_normalizer.py`
3. Subir la memoria y timeout (Configuration -> General Env -> 512 MB, 3 mins).
4. Agregar Trigger: S3, Evento *All Object Create Events*, prefijo `raw/`, sufijo `.wav`.

### Opción 4: Ahorro de Costes con Glacier (S3 Lifecycle)
Para evitar pagar altas tarifas de almacenamiento, todo el audio original que se guarde en la carpeta `raw/` debe moverse al congelador de S3 (Glacier) una vez que la Lambda ya lo hubiese normalizado.

**Opción Automática desde Consola (Terminal):**
```bash
python cloud_normalizer/03_setup_s3_lifecycle.py
```

**Opción Manual desde la Consola web de AWS:**
1. Ve a Amazon S3 y entra en tu bucket `tfm-dementia-bronze`.
2. Arriba, ve a la pestaña **Administración (Management)**.
3. Baja a **Reglas de ciclo de vida (Lifecycle rules)** -> **Crear regla de ciclo de vida**.
4. Escribe un **Nombre de regla**: `MoveRawToGlacier`.
5. En **Rule scope**, elige *Limitar el ámbito a filtros específicos* y escribe `raw/` en el **Tipo de filtro**. Pulsa Intro.
6. En **Acciones**, marca: *Transición de las versiones actuales de los objetos entre clases de almacenamiento*.
7. Transición a: `Glacier Flexible Retrieval` y pon **Días:** `0`.
8. Baja del todo y dale a **Crear regla**. Todo el contenido de `raw/` pasará a Glacier a medianoche UTC.

## Bucket S3
- **Nombre**: `tfm-dementia-bronze`
- **Región**: `eu-central-1`
