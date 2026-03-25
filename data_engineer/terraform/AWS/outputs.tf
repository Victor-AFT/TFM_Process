
# ==============================================================================
# OUTPUTS.TF — Valores de salida tras terraform apply
# ==============================================================================
#
# Equivalente a los print() al final de cada script boto3:
#   "✅ Bucket creado: tfm-dementia-bronze"
#   "✅ Lambda creada: tfm-bronze-ingest"
#   "URL: https://{notebook_url}"
#
# En Terraform, los outputs se muestran automáticamente al terminar el apply
# y se pueden consultar en cualquier momento con: terraform output
# ==============================================================================


# --- Cuenta AWS ---

output "aws_account_id" {
  description = "ID de la cuenta AWS. Equivalente al print de sts.get_caller_identity() en los scripts."
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "Región de despliegue."
  value       = var.aws_region
}


# --- Buckets S3 (Arquitectura Medallion) ---

output "bucket_bronze" {
  description = "Nombre del bucket Bronze. Equivalente a BUCKETS['bronze'] = 'tfm-dementia-bronze'."
  value       = aws_s3_bucket.bronze.bucket
}

output "bucket_silver" {
  description = "Nombre del bucket Silver."
  value       = aws_s3_bucket.silver.bucket
}

output "bucket_gold" {
  description = "Nombre del bucket Gold."
  value       = aws_s3_bucket.gold.bucket
}

output "bucket_athena_results" {
  description = "Nombre del bucket para resultados de Athena."
  value       = aws_s3_bucket.athena_results.bucket
}

output "medallion_s3_uris" {
  description = "URIs S3 de cada capa de la arquitectura Medallion."
  value = {
    bronze_raw   = "s3://${aws_s3_bucket.bronze.bucket}/raw/"
    bronze_norm  = "s3://${aws_s3_bucket.bronze.bucket}/norm/"
    silver_feats = "s3://${aws_s3_bucket.silver.bucket}/features/"
    gold_dataset = "s3://${aws_s3_bucket.gold.bucket}/dataset/"
  }
}


# --- IAM Roles ---

output "lambda_role_arn" {
  description = "ARN del role Lambda. Equivalente al role_arn devuelto por crear_role_lambda()."
  value       = aws_iam_role.lambda_role.arn
}

output "sagemaker_role_arn" {
  description = "ARN del role SageMaker. Equivalente al role_arn devuelto por crear_role_notebook()."
  value       = aws_iam_role.sagemaker_role.arn
}


# --- Lambda Functions ---

output "lambda_bronze_arn" {
  description = "ARN de la Lambda Bronze Ingest. Equivalente a LAMBDA_NAME = 'tfm-bronze-ingest'."
  value       = aws_lambda_function.bronze_ingest.arn
}

output "lambda_normalizer_arn" {
  description = "ARN de la Lambda Normalizer."
  value       = aws_lambda_function.normalizer.arn
}

output "lambda_gold_arn" {
  description = "ARN de la Lambda Gold Filter. Equivalente a LAMBDA_NAME = 'tfm-gold-filter'."
  value       = aws_lambda_function.gold_filter.arn
}

output "lambda_console_urls" {
  description = "URLs directas a las Lambdas en AWS Console."
  value = {
    bronze_ingest = "https://${var.aws_region}.console.aws.amazon.com/lambda/home?region=${var.aws_region}#/functions/${aws_lambda_function.bronze_ingest.function_name}"
    normalizer    = "https://${var.aws_region}.console.aws.amazon.com/lambda/home?region=${var.aws_region}#/functions/${aws_lambda_function.normalizer.function_name}"
    gold_filter   = "https://${var.aws_region}.console.aws.amazon.com/lambda/home?region=${var.aws_region}#/functions/${aws_lambda_function.gold_filter.function_name}"
  }
}


# --- SageMaker ---

output "sagemaker_notebook_name" {
  description = "Nombre del SageMaker Notebook Instance. Equivalente a NOTEBOOK_NAME = 'tfm-audio-processing'."
  value       = aws_sagemaker_notebook_instance.notebook.id
}

output "sagemaker_notebook_url" {
  description = "URL para abrir el Notebook en AWS Console. Equivalente a la URL que imprime esperar_notebook_listo()."
  value       = "https://${var.aws_region}.console.aws.amazon.com/sagemaker/home?region=${var.aws_region}#/notebook-instances/${aws_sagemaker_notebook_instance.notebook.id}"
}


# --- Glue + Athena ---

output "glue_database_name" {
  description = "Nombre de la base de datos en Glue Data Catalog."
  value       = aws_glue_catalog_database.tfm_gold.name
}

output "glue_crawler_name" {
  description = "Nombre del Glue Crawler. Ejecutar con: aws glue start-crawler --name <nombre>"
  value       = aws_glue_crawler.gold_crawler.name
}

output "athena_workgroup" {
  description = "Nombre del Athena Workgroup para queries SQL sobre la capa Gold."
  value       = aws_athena_workgroup.tfm.name
}

output "athena_query_example" {
  description = "Query de ejemplo para Athena (ejecutar tras el primer run del Crawler)."
  value       = "SELECT audio, dementia, mfcc_mean_1, pitch_mean FROM \"${aws_glue_catalog_database.tfm_gold.name}\".\"dataset\" LIMIT 10;"
}
