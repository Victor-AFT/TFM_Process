
# ==============================================================================
# ANALYTICS.TF — Azure Data Factory (equivalente a AWS Glue)
# ==============================================================================
#
# MAPEO AWS → AZURE:
#   AWS Glue Crawler   → Azure Data Factory (orquestación de pipelines ETL)
#   AWS Glue Data Catalog → Azure Purview / ADF Dataset definitions
#   Amazon Athena      → Azure Synapse Analytics (serverless SQL)
#                        (Synapse no se incluye aquí por requerir cuenta de nivel Enterprise)
#
# En el TFM original, el flujo final es:
#   S3 Gold → Glue Crawler → Glue Data Catalog → Athena SQL → Modelos ML
#
# En Azure, el equivalente arquitectónico es:
#   Data Lake Gold → ADF Pipeline → ADF Dataset → Synapse Analytics SQL → Modelos ML
#
# NOTA: Azure Data Factory es más rico que AWS Glue en términos de conectores
# (200+ fuentes de datos). Para este TFM, el ADF se provisiona listo para
# conectar con el Data Lake Gen2 Gold layer.
# ==============================================================================


# ==============================================================================
# AZURE DATA FACTORY — Orquestador ETL (equivalente a AWS Glue)
# ==============================================================================

resource "azurerm_data_factory" "adf" {
  name                = "adf-${var.project_name}-${local.unique_suffix}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  # SystemAssigned permite que ADF acceda al Data Lake sin credenciales explícitas
  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

# RBAC: el Data Factory puede leer los datos de la capa Gold del Data Lake
resource "azurerm_role_assignment" "adf_datalake_reader" {
  scope                = azurerm_storage_account.datalake.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_data_factory.adf.identity[0].principal_id
}


# ==============================================================================
# LINKED SERVICE — Conexión de ADF con el Data Lake Gen2
# ==============================================================================
#
# Un Linked Service en ADF es el equivalente a una "conexión de datos" en Glue:
# define cómo conectarse a la fuente/destino.
# Esta conexión apunta específicamente a la capa Gold para las queries analíticas.
# ==============================================================================

resource "azurerm_data_factory_linked_service_data_lake_storage_gen2" "datalake_gold" {
  name            = "ls-datalake-gold"
  data_factory_id = azurerm_data_factory.adf.id

  # Endpoint DFS (Data Lake Filesystem) del Storage Account
  url = azurerm_storage_account.datalake.primary_dfs_endpoint

  # Autenticación con la clave de cuenta del Storage.
  # En producción, se recomienda use_managed_identity = true (requiere
  # que la identidad del ADF tenga el rol Storage Blob Data Reader ya asignado).
  storage_account_key = azurerm_storage_account.datalake.primary_access_key
}
