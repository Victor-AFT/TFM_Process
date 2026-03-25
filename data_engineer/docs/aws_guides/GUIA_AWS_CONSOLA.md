# 🖥️ Guía: Medallion Architecture desde la Consola AWS

> Paso a paso para implementar Bronze → Silver → Gold desde la interfaz web de AWS.
> Cada sección incluye una explicación sencilla de **por qué** se hace cada paso.

---

## 1️⃣ Bronze Layer — S3 (Almacenamiento de Audio)

### 🧠 ¿Qué es y para qué sirve?

Imagina que tienes grabaciones de audio de pacientes hablando. Antes de poder analizarlas con inteligencia artificial, necesitas **guardarlas en un sitio seguro y accesible**. Amazon S3 es como un "disco duro en la nube" donde almacenamos los archivos originales sin modificar.

La capa **Bronze** es el "almacén de datos crudos". Aquí guardamos todo tal cual llega, sin procesar. Es como guardar los ingredientes frescos en la nevera antes de cocinar.

### Crear Buckets S3

1. Ir a **S3** → **Create bucket**
2. Crear los siguientes buckets (región: `eu-central-1` Frankfurt):

| Bucket | Propósito |
|--------|-----------|
| `tfm-dementia-bronze` | Audio crudo (.wav) — los datos originales |
| `tfm-dementia-silver` | Features extraídas (JSON) — datos procesados |
| `tfm-dementia-gold` | Datos optimizados (Parquet) — listos para análisis |
| `tfm-dementia-athena-results` | Resultados de consultas SQL |

3. **Configuración de cada bucket**:
   - ✅ Encryption: **SSE-S3 (AES-256)** — los datos se cifran automáticamente
   - ✅ Versioning: **Enabled** (solo Bronze) — para no perder datos por error
   - ✅ Block all public access: **ON** — datos médicos, deben ser privados

### Subir Audios al Bronze

Existen varias formas de ingerir los audios a Bronze:
- **Opción Web App (Recomendada)**: Ejecutar `streamlit run cloud/0_bronze/app.py` en tu PC. Permite grabar o subir audios que irán automáticamente a `raw/`.
- **Opción API Drive**: Usar la Lambda `01_lambda_bronze.py` para descargarlos de Google Drive.
- **Opción Script Local**: Usar el script `local/02_upload_audios_to_s3.py`.
- **Opción Manual desde la Consola**:
  1. Ir a **S3** → `tfm-dementia-bronze`
  2. Crear la estructura de carpetas: `raw/dementia/` y `raw/nodementia/`
  3. Entrar en la carpeta deseada → **Upload** → arrastrar archivos `.wav`

> ⚠️ Todos los archivos recién llegados deben terminar en la carpeta **`raw/`**.
> Gracias a los scripts de **cloud_normalizer**, una vez que el audio llega a la carpeta `raw/`, una Lambda oculta lo limpia, lo normaliza (RMS 0.1) y genera una copia final en la carpeta **`norm/`**. A medianoche, el audio original en `raw/` se congelará en S3 Glacier.

---

## 2️⃣ Silver Layer — ECR + SageMaker Processing

### 🧠 ¿Qué es y para qué sirve?

Ahora que tenemos los audios guardados, necesitamos **extraer información útil de ellos**. Un audio en bruto no nos dice mucho; necesitamos convertirlo en números que un modelo de IA pueda entender: tono de voz, velocidad del habla, pausas, etc.

La capa **Silver** es donde transformamos los ingredientes crudos en ingredientes preparados. Es como pelar, cortar y medir los ingredientes antes de cocinar.

Para esto usamos **SageMaker**, que es un servicio de AWS que ejecuta nuestro código de procesamiento en máquinas potentes en la nube. Necesitamos empaquetar nuestro código en un **contenedor Docker** (como una "caja" con todo lo necesario para ejecutar el programa).

### 2a. Crear Repositorio ECR

> **ECR** (Elastic Container Registry) es donde guardamos nuestra "caja" Docker. Piensa en ello como un almacén de aplicaciones empaquetadas.

1. Ir a **Amazon ECR** → **Repositories** → **Create repository**
2. Nombre: `tfm-audio-processing`
3. Tipo: **Private**
4. Click **Create repository**

### 2b. Subir Imagen Docker a ECR

> ⚠️ Este paso requiere la **línea de comandos** (no se puede hacer 100% desde la UI).
> Estamos empaquetando nuestro programa de procesamiento de audio y subiéndolo al almacén de AWS.

```bash
# Login a ECR (autenticarse con AWS)
aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.eu-central-1.amazonaws.com

# Construir la "caja" con nuestro código
docker build -t tfm-audio-processing:latest -f Dockerfile.sagemaker .

# Etiquetar y subir a AWS
docker tag tfm-audio-processing:latest <ACCOUNT_ID>.dkr.ecr.eu-central-1.amazonaws.com/tfm-audio-processing:latest
docker push <ACCOUNT_ID>.dkr.ecr.eu-central-1.amazonaws.com/tfm-audio-processing:latest
```

### 2c. Crear IAM Role para SageMaker

> **IAM Role** es un "permiso" que le damos a SageMaker para que pueda acceder a nuestros datos en S3. Sin este permiso, SageMaker no podría leer los audios ni guardar los resultados.

1. Ir a **IAM** → **Roles** → **Create role**
2. **Trusted entity/Entidad de confianza**: AWS service → **SageMaker**
3. **Permissions**: Adjuntar estas políticas:
   - `AmazonSageMakerFullAccess` — permite usar SageMaker
   - `AmazonS3FullAccess` — permite leer/escribir en S3
4. **Role name**: `SageMakerExecutionRole`
5. Click **Create role**

### 2d. Crear Processing Job en SageMaker

> Aquí es donde lanzamos el procesamiento real. SageMaker arrancará una máquina virtual, ejecutará nuestro código, procesará todos los audios y guardará los resultados automáticamente en S3.

1. Ir a **Amazon SageMaker** → **Processing** → **Processing jobs**
2. Click **Create processing job**
3. Configuración:

| Campo | Valor | Explicación |
|-------|-------|-------------|
| Job name | `tfm-audio-processing-YYYYMMDD` | Nombre descriptivo con fecha |
| IAM role | `SageMakerExecutionRole` | El permiso que creamos antes |
| Container image | `<ACCOUNT_ID>.dkr.ecr.eu-central-1.amazonaws.com/tfm-audio-processing:latest` | Nuestra "caja" Docker |
| Instance type | `ml.m5.xlarge` | Máquina con 4 CPUs y 16 GB RAM |
| Instance count | `1` | Una sola máquina es suficiente |
| Volume size | `30 GB` | Espacio de disco temporal |

4. **Input configuration** (de dónde lee):
   - Source: `s3://tfm-dementia-bronze/norm/`
   - Destination: `/opt/ml/processing/input`

5. **Output configuration** (dónde guarda resultados):
   - Source: `/opt/ml/processing/output`
   - Destination: `s3://tfm-dementia-silver/features/`

6. Click **Create** → Esperar a que termine (~15-30 min)

---

## 3️⃣ Gold Layer — AWS Glue

### 🧠 ¿Qué es y para qué sirve?

Ya tenemos las features extraídas en formato JSON. Pero JSON no es el formato más eficiente para hacer análisis masivos. Necesitamos convertirlo a **Parquet**, un formato columnar optimizado que permite hacer consultas SQL muy rápidas.

La capa **Gold** es el "plato terminado". Los datos están listos para servir: limpios, organizados y en el formato perfecto para que cualquiera pueda consultarlos.

**AWS Glue** se encarga de esta transformación. Es como un "chef" automatizado que convierte los datos de un formato a otro.

### 3a. Crear Base de Datos en Glue

> La base de datos es un "catálogo" que organiza nuestras tablas para poder consultarlas después con SQL.

1. Ir a **AWS Glue** → **Databases** → **Add database**
2. Nombre: `tfm_dementia_db`
3. Click **Create**

### 3b. Crear Glue Job (ETL)

> **ETL** = Extract, Transform, Load. Extraemos datos de Silver (JSON), los transformamos a Parquet, y los cargamos en Gold.

1. Ir a **AWS Glue** → **ETL Jobs** → **Script editor**
2. Engine: **Spark**
3. El script debe:
   - Leer JSON desde `s3://tfm-dementia-silver/features/`
   - Transformar a formato Parquet (columnar, comprimido)
   - Guardar en `s3://tfm-dementia-gold/parquet/`
4. Configuración del Job:

| Campo | Valor | Explicación |
|-------|-------|-------------|
| Name | `tfm-silver-to-gold-etl` | Nombre del trabajo |
| IAM Role | `AWSGlueServiceRole` | Permisos para Glue |
| Worker type | `G.1X` | Tipo de máquina (básica) |
| Workers | `2` | Número de máquinas paralelas |

### 3c. Crear Glue Crawler

> El **Crawler** es un "explorador" que analiza automáticamente los archivos Parquet y crea una tabla en el catálogo. Así no tenemos que definir manualmente las columnas.

1. Ir a **AWS Glue** → **Crawlers** → **Create crawler**
2. Nombre: `tfm-gold-crawler`
3. **Data source**: `s3://tfm-dementia-gold/parquet/`
4. **IAM role**: `AWSGlueServiceRole`
5. **Database**: `tfm_dementia_db`
6. **Table prefix**: `gold_`
7. Click **Create** → **Run crawler**
8. Verificar en **Tables** que aparece la tabla `gold_parquet`

---

## 4️⃣ Consumo — Amazon Athena

### 🧠 ¿Qué es y para qué sirve?

Athena es el paso final: nos permite hacer **consultas SQL** directamente sobre los datos en S3, sin necesidad de montar un servidor de base de datos. Es como tener Excel con superpoderes: puedes hacer preguntas complejas sobre millones de registros en segundos.

Aquí es donde los investigadores, médicos o data scientists pueden **explorar los datos** y obtener insights sobre las diferencias entre pacientes con y sin demencia.

### Configurar Athena

1. Ir a **Amazon Athena** → **Settings**
2. **Query result location**: `s3://tfm-dementia-athena-results/`
3. Click **Save**

### Ejecutar Queries

1. Ir a **Athena** → **Query editor**
2. Seleccionar database: `tfm_dementia_db`
3. Ejemplos de consultas:

```sql
-- Ver todas las features extraídas
SELECT * FROM gold_parquet LIMIT 10;

-- ¿Cuántos pacientes hay por categoría?
SELECT category, COUNT(*) as total
FROM gold_parquet
GROUP BY category;

-- Comparar características de voz entre grupos
-- (¿hablan diferente los pacientes con demencia?)
SELECT category,
       AVG(mfcc_mean_0) as avg_mfcc0,
       AVG(pitch_mean) as avg_pitch,
       AVG(speech_rate) as avg_speech_rate
FROM gold_parquet
GROUP BY category;
```

---

## 📊 Resumen Visual del Flujo

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│  S3 Bronze  │────▶│  SageMaker   │────▶│  Glue ETL   │────▶│  Athena  │
│  (.wav)     │     │  Processing  │     │  + Crawler   │     │  Queries │
│  Datos      │     │  Extrae      │     │  Convierte   │     │  Analiza │
│  crudos     │     │  features    │     │  a Parquet   │     │  con SQL │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────┘
     Bronze              Silver               Gold            Consumo
   "Nevera"           "Preparar"           "Plato listo"    "Servir mesa"
```

---

## 💡 Tips Importantes

| Tip | Detalle |
|-----|---------|
| 💰 **Costos** | Apagar instancias SageMaker cuando no se usen. Athena cobra por datos escaneados |
| 📊 **Monitoring** | Usar **CloudWatch** para ver logs de jobs |
| 🔐 **Permisos** | Si algo falla, verificar los permisos del IAM Role |
| 🌍 **Región** | Siempre estar en `eu-central-1` (Frankfurt) |
| 🔄 **Parquet** | Es ~10x más eficiente que JSON para consultas SQL |
