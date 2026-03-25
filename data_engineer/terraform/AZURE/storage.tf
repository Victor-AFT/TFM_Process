
# ==============================================================================
# STORAGE.TF — Data Lake Gen2 y Arquitectura Medallion
# ==============================================================================
#
# Equivalente boto3: cloud/1_bronze/local/01_create_s3_buckets.py
#                    cloud/1_bronze/cloud_normalizer/03_setup_s3_lifecycle.py
#
# MAPEO AWS → AZURE:
#   S3 Bucket "tfm-dementia-bronze"        → Container "bronze-raw" + "bronze-norm"
#   S3 Bucket "tfm-dementia-silver"        → Container "silver-features" + "silver-transcripts" + "silver-logs"
#   S3 Bucket "tfm-dementia-gold"          → Container "gold-dataset"
#   S3 Bucket "tfm-dementia-athena-results" → Container "athena-results"
#   4 buckets S3 separados                 → 1 Storage Account (Data Lake Gen2) con 7 containers
#
# En Azure, un único Storage Account con HNS habilitado (Data Lake Gen2)
# reemplaza los 4 buckets S3. Los containers son equivalentes a las "carpetas"
# de nivel superior dentro de cada bucket.
# ==============================================================================


# ==============================================================================
# DATA LAKE GEN2 — Storage Account principal del proyecto
# ==============================================================================

resource "azurerm_storage_account" "datalake" {
  name                = "tfmdatalake${local.unique_suffix}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  account_tier             = "Standard"
  account_replication_type = "LRS" # Locally Redundant Storage — equivalente a la redundancia por defecto de S3
  account_kind             = "StorageV2"
  is_hns_enabled           = true # Hierarchical Namespace = Data Lake Gen2 real (como en ej1/ej2)

  # Equivalente a s3:put_bucket_versioning en 01_create_s3_buckets.py
  blob_properties {
    versioning_enabled = true
  }

  tags = local.common_tags
}


# ==============================================================================
# CAPA BRONZE — Audios crudos (equivalente a s3://tfm-dementia-bronze)
# ==============================================================================

# Carpeta de entrada: audios .wav sin procesar subidos por la Streamlit app o Lambda
# Equivalente a: s3://tfm-dementia-bronze/raw/  y  raw/{dementia,nodementia}/
resource "azurerm_storage_container" "bronze_raw" {
  name                  = "bronze-raw"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

# Carpeta de salida del Normalizer: audios normalizados (16kHz, RMS 0.1)
# Equivalente a: s3://tfm-dementia-bronze/norm/
resource "azurerm_storage_container" "bronze_norm" {
  name                  = "bronze-norm"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}


# ==============================================================================
# CAPA SILVER — Features extraídas (equivalente a s3://tfm-dementia-silver)
# ==============================================================================

# JSONs con las ~141 features acústicas y lingüísticas por audio
# Generadas por el SageMaker Notebook (Librosa + OpenSMILE + Whisper + spaCy)
resource "azurerm_storage_container" "silver_features" {
  name                  = "silver-features"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

# Transcripciones de texto generadas por Whisper
resource "azurerm_storage_container" "silver_transcripts" {
  name                  = "silver-transcripts"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

# Logs de ejecución del pipeline de extracción de features
resource "azurerm_storage_container" "silver_logs" {
  name                  = "silver-logs"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}


# ==============================================================================
# CAPA GOLD — Dataset listo para ML (equivalente a s3://tfm-dementia-gold)
# ==============================================================================

# JSONs filtrados con las ~44 variables más importantes (salida de la Lambda Gold)
# Listo para consumir directamente por modelos de clasificación ML
resource "azurerm_storage_container" "gold_dataset" {
  name                  = "gold-dataset"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

# Resultados de queries analíticas (equivalente a s3://tfm-dementia-athena-results)
resource "azurerm_storage_container" "analytics_results" {
  name                  = "analytics-results"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}


# ==============================================================================
# LIFECYCLE POLICY — Archivado automático de audios crudos
# ==============================================================================
#
# Equivalente boto3: cloud/1_bronze/cloud_normalizer/03_setup_s3_lifecycle.py
#
# MAPEO AWS → AZURE:
#   S3 Glacier (Days: 0)  →  Azure Archive Tier (días 1→Cool, días 2→Archive)
#
# El script boto3 configura Days: 0 (se aplica al siguiente UTC midnight).
# Azure no permite archivar directamente en día 0; el mínimo es 1 día en Cool
# antes de pasar a Archive. El comportamiento es equivalente en la práctica.
#
# IMPORTANTE: El tier Archive en Azure tiene un coste de rehidratación
# (equivalente al "retrieval cost" de Glacier). Los audios archivados
# solo se recuperan si se rehidratan explícitamente al tier Hot o Cool.
# ==============================================================================

resource "azurerm_storage_management_policy" "lifecycle" {
  storage_account_id = azurerm_storage_account.datalake.id

  rule {
    name    = "archive-bronze-raw-audios"
    enabled = true

    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["bronze-raw/"] # Solo aplica a los audios crudos, no a bronze-norm
    }

    actions {
      base_blob {
        # Día 1: mover a Cool (acceso infrecuente, ~50% más barato que Hot)
        tier_to_cool_after_days_since_modification_greater_than = 1
        # Día 2: archivar (equivalente a S3 Glacier — ~90% más barato que Hot)
        tier_to_archive_after_days_since_modification_greater_than = 2
      }
    }
  }
}
