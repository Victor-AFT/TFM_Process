# 📘 Guía Básica — AWS Consola paso a paso

> Esta guía te dice **exactamente qué hacer** en la consola de AWS para montar
> la arquitectura Medallion (Bronze → Silver → Gold). Cada paso tiene el
> servicio, dónde hacer click, y qué escribir.

---

## 🗺️ Mapa general

```
Paso 1: S3           → Crear 3 buckets (bronze, silver, gold)
Paso 2: IAM          → Crear un role para las Lambdas
Paso 3: Ingesta      → Web App, Drive Lambda, o Manual a la carpeta raw/
Paso 4: Bronze       → Desplegar Lambda Normalizer (raw/ -> norm/) y Glacier
Paso 5: SageMaker    → Crear Notebook para procesar audios de la carpeta norm/
Paso 6: Lambda Gold  → Crear Lambda Gold (filtrar variables)
```

---

## Paso 1 — Crear los buckets S3

**Servicio**: S3 → https://s3.console.aws.amazon.com

Repite esto **3 veces**, una por cada bucket:

| Bucket | Nombre |
|--------|--------|
| Bronze | `tfm-dementia-bronze` |
| Silver | `tfm-dementia-silver` |
| Gold   | `tfm-dementia-gold` |

**Clicks**:
1. **S3** → **Create bucket**
2. Nombre: pegar el nombre de la tabla de arriba
3. Región: `eu-central-1` (Frankfurt)
4. Dejar todo lo demás por defecto
5. Click en **Create bucket**

> 💡 **Para qué sirve cada uno**: Bronze guarda audios raw, Silver guarda
> los JSON con features extraídas, Gold guarda el JSON limpio para ML.

---

## Paso 2 — Crear el IAM Role para Lambda

**Servicio**: IAM → https://console.aws.amazon.com/iam

**Clicks**:
1. **IAM** → Panel izquierdo → **Roles** → **Create role**
2. Trusted entity: **AWS service**
3. Use case: **Lambda**
4. Click **Next**
5. Buscar y marcar estas 2 políticas:
   - `AWSLambdaBasicExecutionRole` ✅
   - `AmazonS3FullAccess` ✅
6. Click **Next**
7. Role name: `tfm-lambda-role`
8. Click **Create role**

> 💡 **Para qué sirve**: Le da permiso a la Lambda para escribir logs
> y acceder a S3 (leer y escribir archivos).

---

## Paso 3 — Configurar Bronze (Ingesta y Normalizador)

La capa Bronze tiene ahora automatismos que procesan el audio entre carpetas.

### 3.1 Opción Ingesta Manual (Web App)
Ejecuta desde tu PC:
```bash
streamlit run cloud/0_bronze/app.py
```
Permite grabar y mandar audios directamente a la carpeta `raw/`.

### 3.2 Desplegar Lambda Normalizador (Imprescindible)
Detecta los audios en `raw/`, los normaliza automáticamente y los envía a `norm/`.

1. Crea el IAM Role `tfm-lambda-s3-role` con `AWSLambdaBasicExecutionRole` y `AmazonS3FullAccess`.
2. Lanza el script:
```bash
python cloud/1_bronze/cloud_normalizer/02_deploy_lambda_normalizer.py
```
3. Opcional: Para ahorrar en almacenamiento lanza el script de ciclo de vida Glacier:
```bash
python cloud/1_bronze/cloud_normalizer/03_setup_s3_lifecycle.py
```

### 3.3 Añadir Ingesta Lambda Drive (Opcional alternativa)

Si prefieres la ingesta en bloque desde Google Drive:

Ejecuta desde tu PC:
```bash
python cloud/1_bronze/cloud_drive/02_deploy_lambda_bronze.py
```
Te pedirá la ruta al JSON del Service Account. El script hace todo automáticamente.

### 3.2 Opción manual: Crear desde la consola AWS

Si prefieres hacerlo desde la consola:

1. **Crear el ZIP** en tu PC:
```bash
pip install google-auth --target ./package
cd package && zip -r ../lambda_bronze.zip . && cd ..
zip lambda_bronze.zip lambda_function.py
```
   (donde `lambda_function.py` es una copia de `1_bronze/cloud/01_lambda_bronze.py`)

2. **Lambda** → **Create function**
3. Function name: `tfm-bronze-ingest`
4. Runtime: `Python 3.12`
5. Execution role: **Use an existing role** → `tfm-lambda-role`
6. Click **Create function**
7. En la pestaña **Code** → **Upload from** → **.zip file** → subir `lambda_bronze.zip`

### 3.3 Configurar variables de entorno

1. Pestaña **Configuration** → **Environment variables** → **Edit**
2. Añadir estas variables:

| Key | Value |
|-----|-------|
| `S3_BUCKET` | `tfm-dementia-bronze` |
| `GOOGLE_CREDENTIALS_JSON` | *(pegar TODO el contenido del JSON del Service Account)* |
| `DEMENTIA_FOLDER_ID` | `1GKlvbU57g80-ofCOXGwatDD4U15tpJ4S` |
| `NODEMENTIA_FOLDER_ID` | `1jm7w7J8SfuwKHpEALIK6uxR9aQZR1q8I` |

3. Click **Save**

### 3.4 Aumentar el timeout

1. Pestaña **Configuration** → **General configuration** → **Edit**
2. Timeout: `5 min 0 sec`
3. Memory: `512 MB`
4. Click **Save**

### 3.5 Probar la Lambda

1. Pestaña **Test** → **Create new event**
2. Event name: `test_bronze`
3. Pegar este JSON:
```json
{
  "max_files": 2
}
```
4. Click **Test**
5. Deberías ver los audios descargándose en los logs

---

## Paso 4 — Crear SageMaker Notebook (Silver)

**Servicio**: SageMaker AI → https://console.aws.amazon.com/sagemaker

### 4.1 Crear IAM Role para SageMaker

1. **IAM** → **Roles** → **Create role**
2. Trusted entity: **AWS service**
3. Use case: **SageMaker**
4. Click **Next**
5. Buscar y marcar:
   - `AmazonSageMakerFullAccess` ✅
   - `AmazonS3FullAccess` ✅
6. Role name: `tfm-sagemaker-notebook-role`
7. Click **Create role**

### 4.2 Crear el Notebook Instance

1. **SageMaker** → Panel izquierdo → **Notebook** → **Notebook instances**
2. Click **Create notebook instance**
3. Nombre: `tfm-audio-processing`
4. Tipo de instancia: `ml.t3.medium` (el más barato, ~$0.05/hora)
5. IAM role: elegir `tfm-sagemaker-notebook-role`
6. Disco: `10 GB`
7. Click **Create notebook instance**
8. Esperar 3-5 min hasta que el estado sea **InService**

### 4.3 Abrir y configurar el Notebook

1. Cuando esté **InService**, click en **Open JupyterLab**
2. Crear un nuevo notebook: **File** → **New** → **Notebook** (kernel: Python 3)
3. En la primera celda, instalar dependencias:
```python
!pip install librosa soundfile opensmile openai-whisper spacy ffmpeg-python scipy tqdm
!python -m spacy download en_core_web_md
```
4. Ejecutar la celda (Shift + Enter)

### 4.4 Procesar los audios

5. En la siguiente celda, pegar este código para descargar **SÓLO audios normalizados** de S3:
```python
import boto3
from pathlib import Path

s3 = boto3.client('s3')
BUCKET = 'tfm-dementia-bronze'

# Crear carpetas locales
Path('input/dementia').mkdir(parents=True, exist_ok=True)
Path('input/nodementia').mkdir(parents=True, exist_ok=True)

# Listar y descargar archivos NORMALIZADOS
response = s3.list_objects_v2(Bucket=BUCKET, Prefix='norm/')
for obj in response.get('Contents', []):
    key = obj['Key']
    if key.endswith('.wav'):
        # Mapear ruta "norm/dementia/file.wav" a "input/dementia/file.wav"
        local_path = key.replace('norm/', 'input/', 1)
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        s3.download_file(BUCKET, key, local_path)
        print(f'✅ Descargado: {key}')
```

6. En las siguientes celdas, **copiar el código de `process_silver.py`**
   (tu script que ya funciona y que ahora solo recoge de la carpeta `input/`)

7. Al final, subir el JSON resultante a S3 Silver:
```python
import boto3

s3 = boto3.client('s3')
s3.upload_file(
    'ADReSSo21_latest.json',
    'tfm-dementia-silver',
    'features/ADReSSo21_latest.json'
)
print('✅ JSON subido a S3 Silver')
```

> ⚠️ **IMPORTANTE**: Cuando termines, **apaga el Notebook** para no gastar dinero:
> SageMaker → Notebook instances → Seleccionar → **Actions** → **Stop**

---

## Paso 5 — Crear Lambda Gold (Filtrar Variables)

**Servicio**: Lambda → https://console.aws.amazon.com/lambda

### 5.1 Crear la función

1. **Lambda** → **Create function**
2. Function name: `tfm-gold-filter`
3. Runtime: `Python 3.12`
4. Execution role: **Use an existing role** → `tfm-lambda-role`
5. Click **Create function**

### 5.2 Pegar el código

1. Borrar el contenido del editor
2. **Copiar TODO el contenido** del archivo `3_gold/01_lambda_gold.py`
3. Pegarlo en el editor
4. Click **Deploy**

### 5.3 Configurar variables de entorno

1. **Configuration** → **Environment variables** → **Edit**
2. Añadir:

| Key | Value |
|-----|-------|
| `SILVER_BUCKET` | `tfm-dementia-silver` |
| `GOLD_BUCKET` | `tfm-dementia-gold` |

3. Click **Save**

### 5.4 Probar la Lambda

1. Pestaña **Test** → **Create new event**
2. Event name: `test_gold`
3. Pegar:
```json
{
  "silver_key": "features/ADReSSo21_latest.json",
  "gold_key": "features/gold_features.json"
}
```
4. Click **Test**
5. En el resultado deberías ver: `"Gold: 4 registros con 44 variables"`

---

## ✅ Verificar que todo funciona

### Comprobar S3

1. Ir a **S3** → `tfm-dementia-bronze`
   - Deberías ver carpetas `dementia/` y `nodementia/` con audios `.wav`

2. Ir a **S3** → `tfm-dementia-silver`
   - Deberías ver `features/ADReSSo21_latest.json`

3. Ir a **S3** → `tfm-dementia-gold`
   - Deberías ver `features/gold_features.json`
   - Descargar y verificar que tiene ~44 variables planas por registro

---

## 💰 Costos

| Servicio | Uso | Coste |
|----------|-----|-------|
| S3 | 3 buckets, ~25 MB totales | ~$0.01/mes |
| Lambda Bronze | 1 ejecución | $0.00 |
| SageMaker Notebook | 2 horas | ~$0.10 |
| Lambda Gold | 1 ejecución | $0.00 |
| **Total** | | **~$0.11** |

---

## 📋 Resumen rápido

```
1. S3          → 3 buckets (bronze, silver, gold)
2. IAM         → Role para Lambda + Role para SageMaker
3. Lambda      → tfm-bronze-ingest (Google Drive → Bronze)
4. SageMaker   → Notebook para procesar audios → Silver
5. Lambda      → tfm-gold-filter (Silver → Gold limpio)
```

> 🎯 **Resultado final**: Un JSON en S3 Gold con ~44 variables listas
> para alimentar modelos de Machine Learning.
