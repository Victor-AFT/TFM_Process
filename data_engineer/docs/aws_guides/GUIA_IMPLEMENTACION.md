# 🚀 Guía Rápida de Implementación

Esta guía te ayudará a implementar la arquitectura completa paso a paso.

---

## 📋 Pre-requisitos

1. **AWS CLI configurado**
   ```bash
   aws configure
   # - Region: eu-central-1
   # - Access Key ID: Tu key
   # - Secret Access Key: Tu secret
   ```

2. **Python dependencies**
   ```bash
   pip install boto3 sagemaker tqdm
   ```

3. **Docker instalado** (para Silver Layer)

---

## 🥉 Paso 1: Bronze Layer (5 minutos)

```bash
# 1.1 Desplegar Lambda Normalizador (Imprescindible)
python cloud/1_bronze/cloud_normalizer/02_deploy_lambda_normalizer.py

# 1.2 Levantar la Web App para subir/grabar audios
streamlit run cloud/0_bronze/app.py

# 1.3 (Opcional) Si quieres subir desde Drive
python cloud/1_bronze/cloud_drive/02_deploy_lambda_bronze.py

# 1.4 Verificar
aws s3 ls s3://tfm-dementia-bronze/ --recursive
```

**✅ Checkpoint:** Deberías ver ~100 archivos .wav en S3

---

## 🥈 Paso 2: Silver Layer (30-60 minutos)

```bash
cd ../silver

# 2.1 Ejecutar script automático
python run_sagemaker_processing.py

# Este script hace:
# - Construye imagen Docker
# - Sube a Amazon ECR
# - Crea SageMaker Processing Job
# - Ejecuta procesamiento
# - Guarda JSONs en S3 Silver
```

**⏳ Duración:** ~30-45 minutos (dependiendo del número de audios)

**✅ Checkpoint:** Verifica JSONs en S3
```bash
aws s3 ls s3://tfm-dementia-silver/features/
```

---

## 🥇 Paso 3: Gold Layer (15 minutos)

```bash
cd ../gold

# 3.1 Crear Glue Job
python create_glue_job.py

# 3.2 Ejecutar ETL
aws glue start-job-run --job-name tfm-json-to-parquet --region eu-central-1

# 3.3 Monitorear job
# https://console.aws.amazon.com/glue/home?region=eu-central-1#/jobs

# 3.4 Configurar Crawler
python create_glue_crawler.py

# 3.5 Verificar Parquet
aws s3 ls s3://tfm-dementia-gold/dataset/ --recursive
```

**✅ Checkpoint:** Deberías ver archivos .parquet particionados

---

## 📊 Paso 4: Queries con Athena (5 minutos)

```bash
# 4.1 Ir a Athena Console
# https://console.aws.amazon.com/athena/home?region=eu-central-1

# 4.2 Seleccionar database: tfm_dementia_db

# 4.3 Ejecutar queries del archivo athena_queries.sql
```

**Queries importantes:**
- Contar registros: `SELECT COUNT(*) FROM dataset;`
- Ver distribución: `SELECT category, COUNT(*) FROM dataset GROUP BY category;`
- Estadísticas de features nuevas

---

## 🐛 Troubleshooting

### Error: "access denied" en S3
```bash
# Verificar que tu usuario tiene permisos
aws sts get-caller-identity
```

### Error: Docker no encontrado
```bash
# Instalar Docker
# Windows: https://docs.docker.com/desktop/install/windows-install/
```

### Error: Glue Job falla
```bash
# Ver logs en CloudWatch
aws logs tail /aws-glue/jobs/output --follow
```

---

## 💰 Monitorear Costos

```bash
# Ver costos acumulados
aws ce get-cost-and-usage \
  --time-period Start=2026-02-01,End=2026-02-04 \
  --granularity DAILY \
  --metrics BlendedCost
```

---

## 📝 Checklist de Implementación

- [ ] Bronze: Buckets creados
- [ ] Bronze: Audios subidos
- [ ] Silver: Docker image en ECR
- [ ] Silver: SageMaker job completado
- [ ] Silver: JSONs disponibles en S3
- [ ] Gold: Glue Job creado
- [ ] Gold: ETL ejecutado
- [ ] Gold: Parquet generado
- [ ] Catalog: Crawler ejecutado
- [ ] Catalog: Tablas en Glue
- [ ] Athena: Queries funcionando

---

## ✅ Siguiente Paso: Machine Learning

Una vez tengas los datos en Gold:

1. **Exportar dataset**
   ```sql
   -- En Athena
   SELECT * FROM vw_ml_features;
   ```

2. **Entrenar modelos** (local o SageMaker)
   - Random Forest
   - XGBoost
   - Neural Networks

3. **Desplegar** (opcional)
   - SageMaker Endpoint
   - Lambda + API Gateway
