
# ==============================================================================
# ML.TF — Azure Machine Learning (equivalente a Amazon SageMaker)
# ==============================================================================
#
# Equivalente boto3: cloud/2_silver/01_create_notebook.py
#
# MAPEO AWS → AZURE:
#   SageMaker Notebook Instance (ml.t3.medium)  → AML Compute Instance (Standard_DS2_v2)
#   IAM Role "tfm-sagemaker-notebook-role"       → Managed Identity (SystemAssigned en el Workspace)
#   S3FullAccess (policy del role)               → RBAC "Storage Blob Data Contributor" (security.tf)
#   Lifecycle Config (script de inicio pip)      → Setup script en el Compute Instance
#
# ESPECIFICACIONES EQUIVALENTES:
#   ml.t3.medium (AWS):       2 vCPU,  4 GB RAM  → Standard_DS2_v2 (Azure): 2 vCPU, 7 GB RAM
#   Coste aprox.:             ~$0.05/h            → ~$0.14/h (West Europe)
#
# NOTA DE ARQUITECTURA (del README Silver del TFM):
#   El Notebook es la solución académica. En producción se reemplazaría
#   por Azure ML Pipelines (equivalente a SageMaker Pipelines) con
#   compute clusters efímeros, facturando solo durante el procesamiento.
# ==============================================================================


# ==============================================================================
# AZURE ML WORKSPACE
# ==============================================================================
#
# El Workspace es el contenedor central de Azure ML: experimentos, modelos,
# datasets, compute resources y pipelines viven todos aquí.
# Equivalente al "Amazon SageMaker Domain" en AWS.
#
# PRERREQUISITO: El resource provider "Microsoft.MachineLearningServices"
# debe estar registrado en la suscripción. Si terraform apply falla con
# "subscription is not registered", ejecuta:
#   az provider register --namespace Microsoft.MachineLearningServices
# ==============================================================================

resource "azurerm_machine_learning_workspace" "aml_workspace" {
  name                = "aml-${var.project_name}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  # El AML Workspace necesita estos tres recursos como dependencias de plataforma
  application_insights_id = azurerm_application_insights.insights.id
  key_vault_id            = azurerm_key_vault.kv.id
  storage_account_id      = azurerm_storage_account.datalake.id

  # SystemAssigned: Azure crea una identidad gestionada para el Workspace automáticamente.
  # Esta identidad necesita acceso al Data Lake y al Key Vault para funcionar.
  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

# Access Policy en Key Vault para el AML Workspace.
# El Workspace necesita acceso al Key Vault para almacenar sus propios secretos internos.
# Se crea DESPUÉS del workspace para poder referenciar su system-assigned identity.
resource "azurerm_key_vault_access_policy" "aml_workspace" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_machine_learning_workspace.aml_workspace.identity[0].principal_id

  key_permissions         = ["Get", "List", "Create", "Delete", "Recover"]
  secret_permissions      = ["Get", "List", "Set", "Delete", "Recover"]
  certificate_permissions = ["Get", "List"]
}

# RBAC: el AML Workspace puede leer y escribir en el Data Lake
resource "azurerm_role_assignment" "aml_datalake_contributor" {
  scope                = azurerm_storage_account.datalake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_machine_learning_workspace.aml_workspace.identity[0].principal_id
}


# ==============================================================================
# COMPUTE INSTANCE — Equivalente al SageMaker Notebook Instance
# ==============================================================================
#
# El Compute Instance es una VM gestionada con JupyterLab preinstalado.
# Equivalente directo al Notebook Instance de SageMaker que crea
# 01_create_notebook.py (NOTEBOOK_NAME = 'tfm-audio-processing').
#
# ⚠️  COSTE: Este recurso genera coste mientras esté activo (~$0.14/h).
#     Recuerda apagarlo desde Azure ML Studio cuando no lo uses.
#     Equivalente al comentario del script original:
#     "⚠️ IMPORTANTE: Apaga el Notebook cuando termines."
#
# Para destruirlo específicamente sin destruir todo:
#   terraform destroy -target=azurerm_machine_learning_compute_instance.notebook
# ==============================================================================

resource "azurerm_machine_learning_compute_instance" "notebook" {
  name                          = "ci-tfm-notebook"
  machine_learning_workspace_id = azurerm_machine_learning_workspace.aml_workspace.id

  # Standard_DS2_v2: 2 vCPU, 7 GB RAM — equivalente funcional al ml.t3.medium de SageMaker
  virtual_machine_size = "Standard_DS2_v2"

  # El script de inicio instala las mismas librerías que el Lifecycle Config del Notebook SageMaker:
  #   pip install librosa soundfile opensmile spacy ffmpeg-python openai-whisper
  #   python -m spacy download en_core_web_md
  # Esto se configura en Azure ML Studio (Environment/Setup scripts)
  # o directamente en el terminal de JupyterLab tras arrancar la instancia.

  description = "Notebook para extracción de features acústicas y lingüísticas. Equivalente a SageMaker Notebook ml.t3.medium."
}
