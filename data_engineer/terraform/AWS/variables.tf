
# ==============================================================================
# VARIABLES.TF — Parámetros configurables del módulo Terraform
# ==============================================================================
#
# Los valores "hardcodeados" en los scripts boto3 (REGION, LAMBDA_NAME,
# bucket names, etc.) se convierten aquí en variables reutilizables.
#
# Para personalizar el despliegue, crea un archivo terraform.tfvars:
#   aws_region    = "eu-central-1"
#   project_name  = "tfm-dementia"
#   environment   = "prod"
#
# ==============================================================================

variable "aws_region" {
  description = "Región AWS. Equivalente a REGION = 'eu-central-1' en todos los scripts boto3."
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Nombre base del proyecto. Se usa como prefijo en nombres de buckets, Lambdas, roles, etc."
  type        = string
  default     = "tfm-dementia"
}

variable "environment" {
  description = "Entorno de despliegue. Se incluye en los tags de todos los recursos."
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "El entorno debe ser 'dev', 'staging' o 'prod'."
  }
}

variable "google_drive_dementia_folder_id" {
  description = <<-EOT
    ID de la carpeta de Google Drive con audios de demencia.
    Equivalente a DEMENTIA_FOLDER_ID en 02_deploy_lambda_bronze.py.
    No se incluye en tfstate si se pasa como variable de entorno TF_VAR_*.
  EOT
  type        = string
  default     = "1GKlvbU57g80-ofCOXGwatDD4U15tpJ4S"
}

variable "google_drive_nodementia_folder_id" {
  description = "ID de la carpeta de Google Drive con audios sin demencia. Ver NODEMENTIA_FOLDER_ID en 02_deploy_lambda_bronze.py."
  type        = string
  default     = "1jm7w7J8SfuwKHpEALIK6uxR9aQZR1q8I"
}

variable "google_credentials_json" {
  description = <<-EOT
    Contenido JSON del Service Account de Google Drive.
    Equivalente a GOOGLE_CREDENTIALS_JSON en la Lambda Bronze.
    NUNCA pongas el valor real aquí. Pásalo como variable de entorno:
      export TF_VAR_google_credentials_json=$(cat credentials.json)
  EOT
  type        = string
  default     = "PLACEHOLDER - Pasar via TF_VAR_google_credentials_json"
  sensitive   = true
}

# ==============================================================================
# LOCALS — Valores derivados de las variables
# ==============================================================================

locals {
  # Nombres de los buckets S3 — exactamente los mismos que en 01_create_s3_buckets.py:
  #   BUCKETS = {
  #     'bronze': 'tfm-dementia-bronze',
  #     'silver': 'tfm-dementia-silver',
  #     'gold':   'tfm-dementia-gold',
  #     'athena': 'tfm-dementia-athena-results'
  #   }
  bucket_bronze = "${var.project_name}-bronze-tf"
  bucket_silver = "${var.project_name}-silver-tf"
  bucket_gold   = "${var.project_name}-gold-tf"
  bucket_athena = "${var.project_name}-athena-results-tf"

  # Nombres de las Lambdas — exactamente los mismos que en los scripts de despliegue
  lambda_bronze_name     = "${var.project_name}-bronze-ingest-tf"     # LAMBDA_NAME en 02_deploy_lambda_bronze.py
  lambda_normalizer_name = "${var.project_name}-bronze-normalizer-tf" # lambda_name en 02_deploy_lambda_normalizer.py
  lambda_gold_name       = "${var.project_name}-gold-filter-tf"       # LAMBDA_NAME en 02_deploy_lambda_gold.py

  # Nombres de los roles IAM — exactamente los mismos que en los scripts de despliegue
  lambda_role_name    = "${var.project_name}-lambda-role-tf"    # ROLE_NAME en los scripts de Lambda
  sagemaker_role_name = "${var.project_name}-sagemaker-role-tf" # ROLE_NAME en 01_create_notebook.py

  # Tags aplicados a todos los recursos via provider default_tags en main.tf
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Course      = "MBIT-DataEngineering-2025"
    Region      = var.aws_region
  }
}
