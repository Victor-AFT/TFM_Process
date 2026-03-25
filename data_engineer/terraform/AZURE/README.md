# Infraestructura como Código — TFM Detección de Demencia

Este directorio contiene la infraestructura completa del TFM definida en **Terraform** para **Azure**.

Es la evolución natural del directorio `cloud/` del proyecto: mientras `cloud/` usa scripts Python con **boto3** (infraestructura imperativa sobre AWS), `terraform/` define la misma arquitectura de forma **declarativa** sobre **Azure**.

---

## ¿Por qué Terraform en lugar de los scripts boto3?

| Característica | Scripts boto3 (`cloud/`) | Terraform (`terraform/`) |
|---|---|---|
| Estilo | **Imperativo** — describes *cómo* hacer las cosas | **Declarativo** — describes *qué* quieres |
| Estado | Sin gestión de estado: no sabe qué existe | Gestiona `tfstate`: sabe exactamente qué existe |
| Idempotencia | Hay que programarla manualmente (try/except) | Nativa: `apply` siempre llega al estado deseado |
| Rollback | Manual | `terraform destroy` deshace todo con un comando |
| Multicloud | Solo AWS (boto3) | Misma sintaxis para AWS, Azure, GCP |
| Visibilidad | Print() en terminal | `terraform plan` muestra cambios antes de aplicar |

---

## Arquitectura Medallion en Azure

```
[Streamlit App / Google Drive]
          |
          v
  [func-bronze-ingest]          ← Azure Function (equivalente a Lambda tfm-bronze-ingest)
     Descarga .wav               Trigger: HTTP / Timer
          |
          v
  [bronze-raw container]        ← Data Lake Gen2 (equivalente a s3://tfm-dementia-bronze/raw/)
          |
          | Evento de Storage (Event Grid)
          v
  [func-normalizer]             ← Azure Function (equivalente a Lambda tfm-bronze-normalizer)
     Normaliza 16kHz RMS 0.1     Trigger: BlobTrigger sobre bronze-raw/*.wav
          |
          v
  [bronze-norm container]       ← Data Lake Gen2 (equivalente a s3://tfm-dementia-bronze/norm/)
          |
          | (Lifecycle Policy: 1 día → Cool, 2 días → Archive)
          v
  [Archive Tier]                ← Equivalente a S3 Glacier
          
          |  (proceso manual en AML Compute Instance)
          v
  [ci-tfm-notebook]             ← AML Compute Instance (equivalente a SageMaker Notebook ml.t3.medium)
     Librosa + OpenSMILE         Standard_DS2_v2: 2 vCPU, 7 GB RAM
     Whisper + spaCy
          |
          v
  [silver-features container]   ← Data Lake Gen2 (equivalente a s3://tfm-dementia-silver/features/)
          |
          | Evento de Storage (Event Grid)
          v
  [func-gold-filter]            ← Azure Function (equivalente a Lambda tfm-gold-filter)
     Filtra ~44 variables         Trigger: BlobTrigger sobre silver-features/*.json
          |
          v
  [gold-dataset container]      ← Data Lake Gen2 (equivalente a s3://tfm-dementia-gold/)
          |
          v
  [Azure Data Factory]          ← Equivalente a AWS Glue Crawler
     Pipeline ETL
          |
          v
  [Modelos ML / Power BI]
```

---

## Mapeo completo AWS → Azure

| Script boto3 original | Recurso AWS | Archivo Terraform | Recurso Azure |
|---|---|---|---|
| `01_create_s3_buckets.py` | S3 Bucket (x4) | `storage.tf` | `azurerm_storage_account` (Data Lake Gen2) |
| `01_create_s3_buckets.py` | S3 Folders (raw/, norm/, features/...) | `storage.tf` | `azurerm_storage_container` (x7) |
| `03_setup_s3_lifecycle.py` | S3 Lifecycle → Glacier | `storage.tf` | `azurerm_storage_management_policy` |
| `02_deploy_lambda_bronze.py` | Lambda `tfm-bronze-ingest` | `compute.tf` | `azurerm_linux_function_app` |
| `02_deploy_lambda_normalizer.py` | Lambda `tfm-bronze-normalizer` + S3 trigger | `compute.tf` | `azurerm_linux_function_app` + `azurerm_eventgrid_system_topic` |
| `02_deploy_lambda_gold.py` | Lambda `tfm-gold-filter` + S3 trigger | `compute.tf` | `azurerm_linux_function_app` |
| `crear_role_lambda()` | IAM Role `tfm-lambda-role` | `security.tf` | `azurerm_user_assigned_identity` |
| `crear_role_notebook()` | IAM Role `tfm-sagemaker-notebook-role` | `security.tf` | `azurerm_user_assigned_identity` (mismo) |
| `iam.attach_role_policy(AmazonS3FullAccess)` | IAM Policy attachment | `security.tf` | `azurerm_role_assignment` (Storage Blob Data Contributor) |
| `GOOGLE_CREDENTIALS_JSON` (env var en texto plano) | — (antipatrón) | `security.tf` | `azurerm_key_vault` + `azurerm_key_vault_secret` |
| `01_create_notebook.py` | SageMaker Notebook Instance `ml.t3.medium` | `ml.tf` | `azurerm_machine_learning_compute_instance` (`Standard_DS2_v2`) |
| AWS Glue Crawler + Data Catalog | Glue | `analytics.tf` | `azurerm_data_factory` + linked service |
| Amazon CloudWatch | CloudWatch | `compute.tf` | `azurerm_application_insights` |

---

## Estructura de archivos

```
terraform/
├── main.tf        → Provider (azurerm) y Resource Group raíz
├── variables.tf   → Parámetros configurables + locals (unique_suffix, tags)
├── storage.tf     → Data Lake Gen2 + 7 containers + lifecycle policy
├── security.tf    → Managed Identity + Key Vault + secretos + RBAC
├── compute.tf     → Log Analytics + App Insights + 3 Function Apps + Event Grid
├── ml.tf          → Azure ML Workspace + Compute Instance
├── analytics.tf   → Azure Data Factory + Linked Service al Data Lake
├── outputs.tf     → URLs, nombres y IDs de todos los recursos creados
└── README.md      → Este archivo
```

---

## Prerrequisitos

1. **Azure CLI** instalado y autenticado:
   ```bash
   az login
   az account set --subscription "<tu-subscription-id>"
   ```

2. **Terraform >= 1.5** instalado:
   ```bash
   # Verificar versión
   terraform version
   ```

3. **Resource providers registrados** en la suscripción:
   ```bash
   az provider register --namespace Microsoft.MachineLearningServices
   az provider register --namespace Microsoft.EventGrid
   az provider register --namespace Microsoft.DataFactory
   az provider register --namespace Microsoft.KeyVault
   az provider register --namespace Microsoft.Insights
   ```

---

## Uso — Flujo de trabajo Terraform

### 1. Inicializar (descargar providers)
```bash
cd TFM/terraform
terraform init
```
###1.1 Validar 
terraform validate

### 2. Revisar el plan antes de aplicar
```bash
terraform plan
```
Muestra exactamente qué recursos se van a crear, modificar o eliminar.
Equivalente a revisar los scripts boto3 antes de ejecutarlos.

### 3. Aplicar la infraestructura
```bash
terraform apply
```
Confirmar con `yes`. El despliegue completo tarda aproximadamente 10-15 minutos
(el AML Workspace es el recurso más lento en provisionar).

### 4. Ver los outputs (URLs y nombres de recursos)
```bash
terraform output
```

### 5. Destruir toda la infraestructura
```bash
terraform destroy
```
Elimina **todos** los recursos del proyecto en Azure. Útil para limpiar después
del TFM y evitar costes.

Para destruir solo el Compute Instance (el recurso más caro):
```bash
terraform destroy -target=azurerm_machine_learning_compute_instance.notebook
```

---

## Personalización

Crea un archivo `terraform.tfvars` en este directorio para sobrescribir los valores por defecto:

```hcl
# terraform.tfvars
project_name   = "tfm-dementia"
location       = "West Europe"
environment    = "prod"
student_suffix = "miguelfr96"   # Cambia esto por tu propio identificador
```

---

## Comparativa de costes AWS vs Azure

| Recurso | Servicio AWS | Coste AWS est. | Servicio Azure | Coste Azure est. |
|---|---|---|---|---|
| Storage (5 GB) | S3 (4 buckets) | ~$0.12/mes | Data Lake Gen2 | ~$0.10/mes |
| Cold storage | S3 Glacier | ~$0.004/GB/mes | Archive Tier | ~$0.002/GB/mes |
| Funciones (100 invocaciones) | Lambda | ~$0.20/mes | Azure Functions (Consumption) | ~$0.20/mes |
| Notebook / ML | SageMaker ml.t3.medium | ~$0.05/h | AML Standard_DS2_v2 | ~$0.14/h |
| ETL | AWS Glue | ~$0.44/DPU-h | Azure Data Factory | ~$0.25/pipeline/mes |
| Logs | CloudWatch | ~$0.50/GB | Application Insights | ~$0.27/GB |
| **Total primera ejecución** | | **~$1.22** | | **~$0.80-1.00** |

---

## Conexión con los ejercicios del módulo DE-13

Este Terraform es la extensión directa de los ejercicios del módulo:

| Ejercicio | Lo que hace | Recursos de este Terraform |
|---|---|---|
| `ej1/main.tf` | Resource Group + Storage Account (Data Lake Gen2) | `main.tf` + `storage.tf` (base) |
| `ej2/main.tf` | Añade container `landing` | `storage.tf` (extiende con 7 containers Medallion) |
| **Este TFM** | Arquitectura Medallion completa | Todos los archivos |

El container `landing` de `ej2` equivale a `bronze-raw` en esta arquitectura:
es el punto de entrada de los datos crudos en la arquitectura Medallion.

---

## Notas de seguridad

- El archivo `terraform.tfstate` contiene el estado de la infraestructura. **No subir a Git**.
  Añadir al `.gitignore`:
  ```
  terraform.tfstate
  terraform.tfstate.backup
  .terraform/
  terraform.tfvars
  ```

- El secreto `google-drive-credentials` tiene un valor placeholder. Actualizarlo desde Azure Portal
  o con el CLI antes de ejecutar la Function App Bronze:
  ```bash
  az keyvault secret set --vault-name "kv-tfm-<suffix>" \
    --name "google-drive-credentials" \
    --file "cloud/1_bronze/cloud_drive/credentials.json"
  ```
