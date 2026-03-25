# Infraestructura como Código (AWS) — TFM Detección de Demencia

Este directorio contiene la infraestructura completa del TFM definida en **Terraform para AWS**.

Es la traducción directa de los scripts boto3 del directorio `cloud/`: cada llamada imperativa a la API de AWS se convierte en un recurso Terraform declarativo. El resultado es **exactamente la misma arquitectura**, pero gestionada como código profesional.

---

## Por qué Terraform en lugar de los scripts boto3

| Característica | Scripts boto3 (`cloud/`) | Terraform (`terraform/AWS/`) |
|---|---|---|
| Estilo | **Imperativo** — describes *cómo* crear el recurso | **Declarativo** — describes *qué* quieres tener |
| Estado | Sin memoria: no sabe qué ya existe | `tfstate`: sabe exactamente qué hay desplegado |
| Idempotencia | try/except BucketAlreadyExists en cada script | Nativa: `apply` siempre converge al estado deseado |
| Rollback | Destruir recursos manualmente uno a uno | `terraform destroy` elimina todo en orden correcto |
| Reproducibilidad | Ejecutar 7 scripts en el orden correcto | Un solo `terraform apply` despliega todo |
| Visibilidad de cambios | Ninguna antes de ejecutar | `terraform plan` muestra el diff antes de aplicar |
| Gestión de dependencias | `time.sleep(10)` para propagación de IAM | Grafos de dependencias automáticos |

---

## Traducción script a script

### `01_create_s3_buckets.py` → `storage.tf`

| Llamada boto3 | Recurso Terraform |
|---|---|
| `s3_client.create_bucket(Bucket='tfm-dementia-bronze')` | `aws_s3_bucket "bronze"` |
| `s3_client.put_bucket_versioning(Status='Enabled')` | `aws_s3_bucket_versioning "bronze"` |
| `s3_client.put_bucket_encryption(SSEAlgorithm='AES256')` | `aws_s3_bucket_server_side_encryption_configuration` |
| `s3_client.put_bucket_tagging(TagSet=[...])` | `provider "aws" { default_tags {} }` (global) |
| `s3_client.put_object(Key='dementia/')` | `aws_s3_object "bronze_dementia_folder"` |

### `03_setup_s3_lifecycle.py` → `storage.tf`

| Llamada boto3 | Recurso Terraform |
|---|---|
| `s3.put_bucket_lifecycle_configuration(Rules=[{Days: 0, StorageClass: 'GLACIER'}])` | `aws_s3_bucket_lifecycle_configuration "bronze_glacier"` |

### `02_deploy_lambda_bronze.py` → `security.tf` + `compute.tf`

| Llamada boto3 | Recurso Terraform |
|---|---|
| `iam.create_role(RoleName='tfm-lambda-role', AssumeRolePolicyDocument=trust_policy)` | `aws_iam_role "lambda_role"` |
| `iam.attach_role_policy(PolicyArn='AWSLambdaBasicExecutionRole')` | `aws_iam_role_policy_attachment "lambda_basic_execution"` |
| `iam.attach_role_policy(PolicyArn='AmazonS3FullAccess')` | `aws_iam_role_policy_attachment "lambda_s3_full_access"` |
| `zipfile.ZipFile(...); zf.write(lambda_file, 'lambda_function.py')` | `data "archive_file" "lambda_bronze"` |
| `lambda_client.create_function(FunctionName=..., Runtime='python3.12', Timeout=300, MemorySize=512)` | `aws_lambda_function "bronze_ingest"` |

### `02_deploy_lambda_normalizer.py` → `compute.tf`

| Llamada boto3 | Recurso Terraform |
|---|---|
| `aws_lambda.create_function(Timeout=180, MemorySize=512)` | `aws_lambda_function "normalizer"` |
| `aws_lambda.add_permission(StatementId='s3-trigger-permission')` | `aws_lambda_permission "allow_s3_invoke_normalizer"` |
| `s3.put_bucket_notification_configuration(prefix='raw/', suffix='.wav')` | `aws_s3_bucket_notification "bronze_raw_trigger"` |
| `time.sleep(5)` para propagación | `depends_on = [aws_lambda_permission...]` |

### `02_deploy_lambda_gold.py` → `compute.tf`

| Llamada boto3 | Recurso Terraform |
|---|---|
| `lambda_client.create_function(Timeout=60, MemorySize=128)` | `aws_lambda_function "gold_filter"` |
| `s3.put_bucket_notification_configuration(prefix='features/', suffix='.json')` | `aws_s3_bucket_notification "silver_features_trigger"` |

### `01_create_notebook.py` → `security.tf` + `ml.tf`

| Llamada boto3 | Recurso Terraform |
|---|---|
| `iam.create_role(AssumeRolePolicyDocument=sagemaker_trust_policy)` | `aws_iam_role "sagemaker_role"` |
| `sm_client.create_notebook_instance_lifecycle_config(OnStart=[script])` | `aws_sagemaker_notebook_instance_lifecycle_configuration` |
| `sm_client.create_notebook_instance(InstanceType='ml.t3.medium', VolumeSizeInGB=10)` | `aws_sagemaker_notebook_instance "notebook"` |
| `esperar_notebook_listo()` (polling manual) | Terraform espera automáticamente a que el recurso esté listo |

---

## Arquitectura Medallion

```
[Streamlit App / Google Drive]
          |
          v
  [Lambda: tfm-dementia-bronze-ingest]    ← Trigger: HTTP / EventBridge Schedule
          |
          v
  [S3: tfm-dementia-bronze/raw/]
          |
          | S3 Event Notification (raw/*.wav)
          v
  [Lambda: tfm-dementia-bronze-normalizer] ← Trigger: S3 ObjectCreated
          |
          v
  [S3: tfm-dementia-bronze/norm/]
          |
          | (Lifecycle: Days=0 → S3 Glacier el siguiente UTC midnight)
          v
  [S3 Glacier — cold storage]

          | (proceso en SageMaker Notebook)
          v
  [SageMaker: tfm-dementia-notebook]      ← ml.t3.medium, 10 GB, Python 3.12
     Librosa + OpenSMILE + Whisper + spaCy
          |
          v
  [S3: tfm-dementia-silver/features/]
          |
          | S3 Event Notification (features/*.json)
          v
  [Lambda: tfm-dementia-gold-filter]      ← Trigger: S3 ObjectCreated
          |
          v
  [S3: tfm-dementia-gold/dataset/]
          |
          v
  [Glue Crawler: tfm-dementia-gold-crawler]
          |
          v
  [Glue Data Catalog: tfm_dementia_gold]
          |
          v
  [Athena Workgroup: tfm-dementia-workgroup]
     SELECT * FROM tfm_dementia_gold.dataset
```

---

## Estructura de archivos

```
terraform/AWS/
├── main.tf        → Provider AWS (region eu-central-1) + caller identity
├── variables.tf   → Variables (region, project_name, env) + locals con nombres de recursos
├── storage.tf     → 4 buckets S3 + versioning + encryption + lifecycle Glacier
├── security.tf    → 3 IAM Roles (Lambda, SageMaker, Glue) + policy attachments
├── compute.tf     → 3 Lambda Functions + CloudWatch logs + S3 triggers
├── ml.tf          → SageMaker Notebook Instance + Lifecycle Config
├── analytics.tf   → Glue Catalog + Crawler + Athena Workgroup
├── outputs.tf     → ARNs, URLs de consola, S3 URIs, query de ejemplo
└── README.md      → Este archivo
```

---

## Prerrequisitos

1. **AWS CLI** configurado con las credenciales correctas:
   ```bash
   aws configure
   # AWS Access Key ID: ...
   # AWS Secret Access Key: ...
   # Default region name: eu-central-1
   ```

2. **Terraform >= 1.5** instalado. Verificar:
   ```bash
   terraform version
   ```

3. **Credenciales de Google Drive** en variable de entorno (para la Lambda Bronze):
   ```bash
   # Windows PowerShell:
   $env:TF_VAR_google_credentials_json = Get-Content "cloud\1_bronze\cloud_drive\credentials.json" -Raw
   
   # Linux/Mac:
   export TF_VAR_google_credentials_json=$(cat cloud/1_bronze/cloud_drive/credentials.json)
   ```

---

## Uso — Flujo de trabajo Terraform

### 1. Inicializar (equivalente a `pip install boto3`)
```bash
cd TFM/terraform/AWS
terraform init
```
Descarga el provider `hashicorp/aws ~> 5.0` y `hashicorp/archive ~> 2.0`.
### 2. terraform fmt (El Estético) 
**¿Cuándo?** Siempre que escribas código.
**¿Qué hace?** Arregla automáticamente los espacios y sangrías de tus archivos `.tf` para que se vean limpios.

```bash
terraform fmt
```

### 3. terraform validate (El Corrector) 校验
**¿Cuándo?** Antes de intentar desplegar nada.
**¿Qué hace?** Comprueba que no tengas errores de sintaxis (paréntesis sin cerrar, nombres mal escritos, etc.). Si te dice "Success!", vas por buen camino.

```bash
terraform validate
```

### 4. Ver qué se va a crear (antes de ejecutar nada)
```bash
terraform plan
```
Muestra exactamente los recursos que se crearán. En boto3, no hay este paso —
ejecutas y descubres si algo falla a mitad.

### 5. Desplegar toda la infraestructura
```bash
terraform apply
```
Confirmar con `yes`. Tiempo estimado: **5-8 minutos** (SageMaker es lo más lento).

### 6. Ver los outputs (ARNs, URLs, S3 URIs)
```bash
terraform output
```

### 7. Ejecutar el Glue Crawler (tras subir datos a Gold)
```bash
aws glue start-crawler --name $(terraform output -raw glue_crawler_name)
```

### 8. Destruir toda la infraestructura
```bash
terraform destroy 
```
Elimina **todos** los recursos en el orden correcto (respetando dependencias).
Para destruir solo el Notebook (el más caro):
```bash
terraform destroy -target=aws_sagemaker_notebook_instance.notebook
```

---

## Comparativa de costes

| Recurso | Script boto3 | Coste | Terraform | Diferencia |
|---|---|---|---|---|
| 4 buckets S3 (5 GB) | `01_create_s3_buckets.py` | ~$0.12/mes | Igual | Sin cambio |
| S3 Glacier (raw/) | `03_setup_s3_lifecycle.py` | ~$0.02/GB/mes | Igual | Sin cambio |
| Lambda x3 (100 invoc.) | `02_deploy_lambda_*.py` | ~$0.20/mes | Igual | Sin cambio |
| SageMaker ml.t3.medium | `01_create_notebook.py` | ~$0.05/h | Igual | Sin cambio |
| CloudWatch logs | (automático) | ~$0.50/GB | Explícito (14 días) | Retención controlada |
| **Total primera ejecución** | | **~$1.22** | | **~$1.22** |

El coste no cambia — la infraestructura es idéntica. Lo que cambia es cómo se gestiona.

---

## Notas importantes

**`.gitignore` recomendado** — añadir al proyecto:
```
# Terraform
terraform/AWS/.terraform/
terraform/AWS/.lambda_builds/
terraform/AWS/terraform.tfstate
terraform/AWS/terraform.tfstate.backup
terraform/AWS/terraform.tfvars
terraform/AZURE/.terraform/
terraform/AZURE/terraform.tfstate
terraform/AZURE/terraform.tfstate.backup
```

**Importar recursos existentes** — si ya creaste los buckets con boto3 y quieres que Terraform los gestione sin recrearlos:
```bash
terraform import aws_s3_bucket.bronze tfm-dementia-bronze
terraform import aws_s3_bucket.silver tfm-dementia-silver
terraform import aws_s3_bucket.gold   tfm-dementia-gold
```


terraform apply -out aws.tfplan
terraform show -json aws.tfplan > aws.tfplan.json
terraform apply "aws.tfplan"

Entorno profesional

TF state en S3

terraform {
  backend "s3" {
    bucket         = "tfm-dementia-tfstate-bucket"
    key            = "terraform.tfstate"
    region         = "eu-central-1"
    use_lockfile = true
  }
}

terraform plan -destroy -out aws.tf.destroy 
terraform apply "aws.tf.destroy" 
nhekoo@gmail.com

CREAR CON MODULOS SIEMPRE ....CON IA 