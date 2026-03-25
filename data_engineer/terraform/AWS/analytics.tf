
# ==============================================================================
# ANALYTICS.TF — AWS Glue + Amazon Athena
# ==============================================================================
#
# Equivalente a la capa de consumo descrita en cloud/README.md:
#   "S3 Gold → Glue Crawler → Glue Data Catalog → Athena SQL → Modelos ML"
#
# En el TFM original, Glue y Athena se configuraban manualmente desde la consola.
# Aquí se definen como código, reproducibles en cualquier cuenta AWS.
#
# FLUJO:
#   1. Glue Crawler escanea s3://tfm-dementia-gold/dataset/
#   2. Infiere el schema del JSON e indexa en Glue Data Catalog
#   3. Athena puede hacer queries SQL directamente sobre S3 Gold
#      (sin mover datos, igual que en el modelo original del TFM)
# ==============================================================================


# ==============================================================================
# GLUE DATA CATALOG — Base de datos de metadatos
# ==============================================================================

resource "aws_glue_catalog_database" "tfm_gold" {
  name        = replace("${var.project_name}_gold", "-", "_") # Glue no admite guiones en el nombre
  description = "Catálogo de la capa Gold del TFM. Indexado por el Glue Crawler."
}


# ==============================================================================
# GLUE CRAWLER — Escanea Gold y actualiza el Data Catalog
# ==============================================================================
#
# El Crawler infiere el schema del JSON gold_features.json (las ~44 variables)
# y lo registra en el Data Catalog para que Athena pueda consultarlo con SQL.
# ==============================================================================

resource "aws_glue_crawler" "gold_crawler" {
  name          = "${var.project_name}-gold-crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.tfm_gold.name
  description   = "Crawler que indexa los JSONs de la capa Gold para consultarlos con Athena"

  s3_target {
    path = "s3://${aws_s3_bucket.gold.bucket}/dataset/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE" # Actualiza el schema si cambia la estructura del JSON
    delete_behavior = "LOG"                # Solo loguea (no borra) si desaparecen columnas
  }

  # Ejecutar el Crawler manualmente desde consola o programáticamente:
  #   aws glue start-crawler --name tfm-dementia-gold-crawler
  # O via EventBridge para ejecución automática cuando lleguen nuevos JSONs a Gold.
}


# ==============================================================================
# ATHENA WORKGROUP — Configuración de queries SQL sobre S3
# ==============================================================================
#
# El Workgroup centraliza los resultados de todas las queries de Athena
# en el bucket de resultados dedicado (s3://tfm-dementia-athena-results/).
# ==============================================================================

resource "aws_athena_workgroup" "tfm" {
  name        = "${var.project_name}-workgroup"
  description = "Workgroup para queries SQL sobre la capa Gold del TFM"

  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }

    # Límite de seguridad: ninguna query podrá escanear más de 1 GB de datos
    bytes_scanned_cutoff_per_query = 1073741824 # 1 GB en bytes
  }
}
