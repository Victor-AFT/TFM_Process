
# ==============================================================================
# SECURITY.TF — Identidades, Key Vault y Control de Acceso
# ==============================================================================
#
# Equivalente boto3: Roles IAM creados en 02_deploy_lambda_bronze.py
#                    y 01_create_notebook.py (crear_role_lambda, crear_role_notebook)
#
# MAPEO AWS → AZURE:
#   AWS IAM Role "tfm-lambda-role"           → User Assigned Managed Identity
#   AWS IAM Role "tfm-sagemaker-notebook-role" → Managed Identity (mismo, en Azure
#                                                un único MI puede tener múltiples roles)
#   AmazonS3FullAccess (policy)              → "Storage Blob Data Contributor" (RBAC)
#   Variables de entorno con secretos        → Azure Key Vault
#
# DIFERENCIA CLAVE con AWS:
#   En AWS se crean 2 IAM Roles separados (uno para Lambda, otro para SageMaker).
#   En Azure, una única User Assigned Managed Identity puede asignarse a múltiples
#   recursos (Function Apps + AML Workspace), simplificando la gestión de permisos.
# ==============================================================================


# ==============================================================================
# MANAGED IDENTITY — Equivalente a los IAM Roles de AWS
# ==============================================================================

resource "azurerm_user_assigned_identity" "tfm_identity" {
  name                = "id-${var.project_name}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tags                = local.common_tags
}


# ==============================================================================
# KEY VAULT — Almacén de secretos (credenciales Google Drive y otros)
# ==============================================================================
#
# En el script boto3 original (02_deploy_lambda_bronze.py), las credenciales
# de Google Drive se pasan como variable de entorno GOOGLE_CREDENTIALS_JSON
# directamente en la configuración de la Lambda. Esto es un antipatrón de
# seguridad (secretos en texto plano en variables de entorno).
#
# En Azure, la práctica correcta es almacenar los secretos en Key Vault
# y que el código de la Function App los lea en runtime usando la
# Managed Identity (sin credenciales hardcodeadas en ningún sitio).
# ==============================================================================

resource "azurerm_key_vault" "kv" {
  name                = "kv-tfm-${local.unique_suffix}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  # Usar vault access policies (no RBAC de Azure) — más simple para proyectos académicos.
  # En producción se recomienda enable_rbac_authorization = true.
  enable_rbac_authorization = false

  tags = local.common_tags
}

# --- Access Policies ---

# Permiso para el operador de Terraform (la persona/SP que ejecuta terraform apply).
# Necesario para que Terraform pueda crear y gestionar los secretos en el vault.
resource "azurerm_key_vault_access_policy" "terraform_operator" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = ["Get", "List", "Set", "Delete", "Purge", "Recover"]
}

# Permiso de solo lectura para la Managed Identity.
# Las Function Apps usan esta identidad para leer secretos en runtime.
resource "azurerm_key_vault_access_policy" "managed_identity" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.tfm_identity.principal_id

  secret_permissions = ["Get", "List"]
}

# --- Secretos ---

# Credenciales del Service Account de Google Drive.
# Equivalente a: variable GOOGLE_CREDENTIALS_JSON en Lambda tfm-bronze-ingest.
# IMPORTANTE: Sustituir el valor placeholder antes de ejecutar terraform apply.
#             Nunca commitear el JSON real en Git.
resource "azurerm_key_vault_secret" "google_drive_credentials" {
  # El depends_on asegura que el operador ya tiene permisos ANTES de intentar crear el secreto.
  depends_on = [azurerm_key_vault_access_policy.terraform_operator]

  name         = "google-drive-credentials"
  value        = "PLACEHOLDER - Reemplazar con el contenido de credentials.json del Service Account"
  key_vault_id = azurerm_key_vault.kv.id
}

# IDs de las carpetas de Google Drive (equivalente a las env vars de la Lambda Bronze)
resource "azurerm_key_vault_secret" "gdrive_folder_dementia" {
  depends_on   = [azurerm_key_vault_access_policy.terraform_operator]
  name         = "gdrive-folder-dementia"
  value        = "1GKlvbU57g80-ofCOXGwatDD4U15tpJ4S"
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "gdrive_folder_nodementia" {
  depends_on   = [azurerm_key_vault_access_policy.terraform_operator]
  name         = "gdrive-folder-nodementia"
  value        = "1jm7w7J8SfuwKHpEALIK6uxR9aQZR1q8I"
  key_vault_id = azurerm_key_vault.kv.id
}


# ==============================================================================
# RBAC — Permisos de la Managed Identity sobre el Data Lake
# ==============================================================================
#
# Equivalente AWS: iam.attach_role_policy(PolicyArn='AmazonS3FullAccess')
#
# "Storage Blob Data Contributor" permite leer y escribir blobs en el Data Lake.
# Es el equivalente de S3 FullAccess pero con scope limitado a una cuenta
# (principio de mínimo privilegio — mejor que AmazonS3FullAccess global).
# ==============================================================================

resource "azurerm_role_assignment" "identity_datalake_contributor" {
  scope                = azurerm_storage_account.datalake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.tfm_identity.principal_id
}
