
# ==============================================================================
# COMPUTE.TF — Azure Functions (equivalente a AWS Lambda)
# ==============================================================================
#
# Equivalente boto3:
#   cloud/1_bronze/cloud_drive/02_deploy_lambda_bronze.py       → func_bronze_ingest
#   cloud/1_bronze/cloud_normalizer/02_deploy_lambda_normalizer.py → func_normalizer
#   cloud/3_gold/02_deploy_lambda_gold.py                        → func_gold_filter
#
# MAPEO AWS → AZURE:
#   AWS Lambda (Python 3.12, 512 MB)     → Azure Function App (Linux, Python 3.12)
#   AWS Lambda Trigger (S3 Event)        → Azure Event Grid System Topic
#   IAM Role con Lambda policies          → User Assigned Managed Identity (security.tf)
#   AWS CloudWatch                        → Azure Application Insights
#
# MODELO DE FACTURACIÓN:
#   Igual que Lambda, el plan "Consumption" (Y1) cobra por ejecución.
#   No hay coste cuando las funciones están inactivas.
# ==============================================================================


# ==============================================================================
# OBSERVABILIDAD — Log Analytics + Application Insights
# ==============================================================================
#
# Equivalente AWS: Amazon CloudWatch (métricas, logs y trazas de Lambda)
# Workspace-based Application Insights = práctica estándar (Classic está deprecado)
# ==============================================================================

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "log-${var.project_name}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "PerGB2018"
  retention_in_days   = 30 # 30 días de retención de logs (configurable hasta 730)
  tags                = local.common_tags
}

resource "azurerm_application_insights" "insights" {
  name                = "appi-${var.project_name}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  workspace_id        = azurerm_log_analytics_workspace.logs.id
  application_type    = "other"
  tags                = local.common_tags
}


# ==============================================================================
# STORAGE DE FUNCIONES — Uso interno del runtime de Azure Functions
# ==============================================================================
#
# Azure Functions requiere una cuenta de almacenamiento separada para su runtime
# (gestión de triggers, blobs de ejecución, locks distribuidos).
# NO es el Data Lake — este storage es solo para la infraestructura interna.
# ==============================================================================

resource "azurerm_storage_account" "functions_storage" {
  name                     = "tfmfuncstore${local.unique_suffix}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = local.common_tags
}


# ==============================================================================
# APP SERVICE PLAN — Plan de cómputo compartido (Consumption = Serverless)
# ==============================================================================
#
# El plan "Y1" (Consumption) es el equivalente directo al modelo de facturación
# de AWS Lambda: se paga por invocación y por ms de CPU, no por servidor.
# Las 3 Function Apps comparten este mismo plan.
# ==============================================================================

resource "azurerm_service_plan" "consumption_plan" {
  name                = "asp-${var.project_name}-consumption"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "Y1" # Y1 = Consumption (serverless). EP1/EP2 = Premium (siempre activo).
  tags                = local.common_tags
}


# ==============================================================================
# FUNCIÓN 1: Bronze Ingest
# ==============================================================================
#
# Equivalente boto3:  cloud/1_bronze/cloud_drive/02_deploy_lambda_bronze.py
# Lambda original:    tfm-bronze-ingest (Python 3.12, 512 MB, timeout 300s)
# Función:            Descarga audios .wav de Google Drive → bronze-raw container
#
# Variables de entorno:
#   En boto3, las credenciales de Google Drive se pasan como texto plano en
#   GOOGLE_CREDENTIALS_JSON. Aquí se pasa el URI del secreto en Key Vault;
#   el código de la función lo recupera en runtime via la Managed Identity.
# ==============================================================================

resource "azurerm_linux_function_app" "func_bronze_ingest" {
  name                       = "func-${var.project_name}-bronze-ingest"
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  service_plan_id            = azurerm_service_plan.consumption_plan.id
  storage_account_name       = azurerm_storage_account.functions_storage.name
  storage_account_access_key = azurerm_storage_account.functions_storage.primary_access_key

  # Asigna la Managed Identity (equivalente al IAM Role en AWS)
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.tfm_identity.id]
  }

  site_config {
    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME              = "python"
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.insights.connection_string
    # Configuración del Data Lake (el código leerá/escribirá aquí)
    STORAGE_ACCOUNT_NAME = azurerm_storage_account.datalake.name
    BRONZE_RAW_CONTAINER = azurerm_storage_container.bronze_raw.name
    # URIs de los secretos en Key Vault (el código los recupera usando la Managed Identity)
    GOOGLE_CREDENTIALS_SECRET_URI       = azurerm_key_vault_secret.google_drive_credentials.versionless_id
    GDRIVE_FOLDER_DEMENTIA_SECRET_URI   = azurerm_key_vault_secret.gdrive_folder_dementia.versionless_id
    GDRIVE_FOLDER_NODEMENTIA_SECRET_URI = azurerm_key_vault_secret.gdrive_folder_nodementia.versionless_id
    # ID de la Managed Identity (necesario para autenticar contra Key Vault en apps multi-identity)
    AZURE_CLIENT_ID = azurerm_user_assigned_identity.tfm_identity.client_id
  }

  tags = local.common_tags
}


# ==============================================================================
# FUNCIÓN 2: Normalizer (disparada por eventos de Storage)
# ==============================================================================
#
# Equivalente boto3:  cloud/1_bronze/cloud_normalizer/02_deploy_lambda_normalizer.py
# Lambda original:    tfm-bronze-normalizer (Python 3.12, 512 MB, timeout 180s)
# Función:            Normaliza audios raw/ (16kHz, RMS 0.1) → bronze-norm container
#
# TRIGGER: En AWS se configura con s3.put_bucket_notification_configuration()
#   filtrando por prefix "raw/" y suffix ".wav".
#   En Azure, el trigger se define en el código de la función (function.json)
#   como un BlobTrigger, y el Event Grid System Topic (abajo) es la
#   infraestructura de routing de eventos necesaria para que funcione.
# ==============================================================================

resource "azurerm_linux_function_app" "func_normalizer" {
  name                       = "func-${var.project_name}-normalizer"
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  service_plan_id            = azurerm_service_plan.consumption_plan.id
  storage_account_name       = azurerm_storage_account.functions_storage.name
  storage_account_access_key = azurerm_storage_account.functions_storage.primary_access_key

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.tfm_identity.id]
  }

  site_config {
    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME              = "python"
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.insights.connection_string
    STORAGE_ACCOUNT_NAME                  = azurerm_storage_account.datalake.name
    BRONZE_RAW_CONTAINER                  = azurerm_storage_container.bronze_raw.name
    BRONZE_NORM_CONTAINER                 = azurerm_storage_container.bronze_norm.name
    AZURE_CLIENT_ID                       = azurerm_user_assigned_identity.tfm_identity.client_id
  }

  tags = local.common_tags
}

# Event Grid System Topic — infraestructura de eventos del Storage Account.
# Equivalente al S3 Event Notification que en boto3 se configura con
# put_bucket_notification_configuration(). El binding de trigger del
# Normalizer (BlobTrigger en function.json) usa este topic internamente.
resource "azurerm_eventgrid_system_topic" "bronze_raw_events" {
  name                   = "egt-${var.project_name}-bronze-raw"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  source_arm_resource_id = azurerm_storage_account.datalake.id
  topic_type             = "Microsoft.Storage.StorageAccounts"
  tags                   = local.common_tags
}


# ==============================================================================
# FUNCIÓN 3: Gold Filter (disparada por nuevos JSONs en silver-features)
# ==============================================================================
#
# Equivalente boto3:  cloud/3_gold/02_deploy_lambda_gold.py
# Lambda original:    tfm-gold-filter (Python 3.12, 128 MB, timeout 60s)
# Función:            Lee features.json de Silver → filtra ~44 variables → gold-dataset
#
# En boto3 se reutiliza el mismo IAM Role que Bronze (ROLE_NAME = 'tfm-lambda-role').
# En Azure, la misma Managed Identity se asigna a las 3 funciones — mismo patrón.
# ==============================================================================

resource "azurerm_linux_function_app" "func_gold_filter" {
  name                       = "func-${var.project_name}-gold-filter"
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  service_plan_id            = azurerm_service_plan.consumption_plan.id
  storage_account_name       = azurerm_storage_account.functions_storage.name
  storage_account_access_key = azurerm_storage_account.functions_storage.primary_access_key

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.tfm_identity.id]
  }

  site_config {
    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME              = "python"
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.insights.connection_string
    STORAGE_ACCOUNT_NAME                  = azurerm_storage_account.datalake.name
    SILVER_FEATURES_CONTAINER             = azurerm_storage_container.silver_features.name
    GOLD_DATASET_CONTAINER                = azurerm_storage_container.gold_dataset.name
    AZURE_CLIENT_ID                       = azurerm_user_assigned_identity.tfm_identity.client_id
  }

  tags = local.common_tags
}
