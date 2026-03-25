
# ==============================================================================
# OUTPUTS.TF — Valores de salida tras terraform apply
# ==============================================================================
#
# Los outputs son los equivalentes a los print() que hacen los scripts boto3
# al final de cada ejecución (URLs de Lambda, ARNs, etc.).
#
# Se muestran en la terminal al terminar terraform apply y se pueden consultar
# en cualquier momento con: terraform output
#
# Los valores marcados como sensitive = true no se muestran en logs de CI/CD.
# ==============================================================================


# --- Infraestructura base ---

output "resource_group_name" {
  description = "Nombre del Resource Group que contiene toda la infraestructura del TFM."
  value       = azurerm_resource_group.rg.name
}

output "resource_group_location" {
  description = "Región de Azure donde se desplegó la infraestructura."
  value       = azurerm_resource_group.rg.location
}


# --- Data Lake Gen2 ---

output "datalake_name" {
  description = "Nombre de la cuenta de almacenamiento Data Lake Gen2."
  value       = azurerm_storage_account.datalake.name
}

output "datalake_dfs_endpoint" {
  description = "Endpoint DFS del Data Lake. Usar para conectar AML Workspace, ADF y Azure Databricks."
  value       = azurerm_storage_account.datalake.primary_dfs_endpoint
}

output "datalake_blob_endpoint" {
  description = "Endpoint Blob del Data Lake. Usar para conexiones via SDK (Python azure-storage-blob)."
  value       = azurerm_storage_account.datalake.primary_blob_endpoint
}

output "medallion_containers" {
  description = "Nombres de los containers de la arquitectura Medallion (Bronze → Silver → Gold)."
  value = {
    bronze_raw         = azurerm_storage_container.bronze_raw.name
    bronze_norm        = azurerm_storage_container.bronze_norm.name
    silver_features    = azurerm_storage_container.silver_features.name
    silver_transcripts = azurerm_storage_container.silver_transcripts.name
    silver_logs        = azurerm_storage_container.silver_logs.name
    gold_dataset       = azurerm_storage_container.gold_dataset.name
  }
}


# --- Seguridad ---

output "managed_identity_client_id" {
  description = "Client ID de la Managed Identity. Pasar como AZURE_CLIENT_ID en los SDKs."
  value       = azurerm_user_assigned_identity.tfm_identity.client_id
}

output "key_vault_uri" {
  description = "URI del Key Vault donde residen las credenciales de Google Drive."
  value       = azurerm_key_vault.kv.vault_uri
}


# --- Azure Functions (equivalente a las URLs de Lambda en AWS Console) ---

output "func_bronze_ingest_hostname" {
  description = "Hostname de la Azure Function equivalente a Lambda 'tfm-bronze-ingest'."
  value       = azurerm_linux_function_app.func_bronze_ingest.default_hostname
}

output "func_normalizer_hostname" {
  description = "Hostname de la Azure Function equivalente a Lambda 'tfm-bronze-normalizer'."
  value       = azurerm_linux_function_app.func_normalizer.default_hostname
}

output "func_gold_filter_hostname" {
  description = "Hostname de la Azure Function equivalente a Lambda 'tfm-gold-filter'."
  value       = azurerm_linux_function_app.func_gold_filter.default_hostname
}

output "application_insights_connection_string" {
  description = "Connection string de Application Insights para las Function Apps (equivalente a CloudWatch)."
  value       = azurerm_application_insights.insights.connection_string
  sensitive   = true # No se muestra en logs; usar: terraform output -json application_insights_connection_string
}


# --- Azure Machine Learning ---

output "aml_workspace_id" {
  description = "Resource ID del Azure ML Workspace. Equivalente al ARN del SageMaker Domain."
  value       = azurerm_machine_learning_workspace.aml_workspace.id
}

output "aml_workspace_url" {
  description = "URL de Azure ML Studio para abrir el Workspace en el navegador."
  value       = "https://ml.azure.com/workspaces/${azurerm_machine_learning_workspace.aml_workspace.name}/overview?wsid=${azurerm_machine_learning_workspace.aml_workspace.id}"
}

output "compute_instance_name" {
  description = "Nombre del Compute Instance (equivalente al Notebook Instance de SageMaker)."
  value       = azurerm_machine_learning_compute_instance.notebook.name
}


# --- Azure Data Factory ---

output "data_factory_name" {
  description = "Nombre del Azure Data Factory. Equivalente al Glue Job/Crawler de AWS."
  value       = azurerm_data_factory.adf.name
}

output "data_factory_url" {
  description = "URL de Azure Data Factory Studio para diseñar pipelines ETL."
  value       = "https://adf.azure.com/en/authoring/pipeline?factory=/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${azurerm_resource_group.rg.name}/providers/Microsoft.DataFactory/factories/${azurerm_data_factory.adf.name}"
}


# --- Resumen de costes estimados ---

output "cost_estimate_info" {
  description = "Nota sobre costes. Ver README.md para tabla completa AWS vs Azure."
  value       = "Coste idle (~$0/mes). Coste activo estimado: ~$0.20-0.50/ejecucion (sin AML). Con AML Compute Instance encendido: ~$0.14/h adicionales. Recuerda apagar el Compute Instance cuando no lo uses."
}
