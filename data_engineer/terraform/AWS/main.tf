
# ==============================================================================
# MAIN.TF — Configuración del Provider y datos de la cuenta AWS
# ==============================================================================
#
# Este archivo es la traducción directa de la configuración implícita que
# todos los scripts boto3 del proyecto asumen en segundo plano:
#   boto3.client('s3', region_name='eu-central-1')
#   boto3.client('lambda', region_name='eu-central-1')
#   ...
#
# En Terraform, esa configuración se centraliza aquí una sola vez.
# ==============================================================================

terraform {
  required_version = ">= 1.5"

  required_providers {
    # Provider oficial de AWS
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    # Provider para generar ZIPs de las Lambdas sin salir de Terraform
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }

  # RECOMENDACIÓN: Almacenar el tfstate en S3 en lugar de en local.
  # Descomenta esto cuando tengas el bucket de estado creado:
  #
  # backend "s3" {
  #   bucket         = "tfm-dementia-terraform-state"
  #   key            = "tfm/terraform.tfstate"
  #   region         = "eu-central-1"
  #   encrypt        = true
  # }
}

provider "aws" {
  # Región eu-central-1 (Frankfurt) — la misma que usan todos los scripts boto3:
  # REGION = 'eu-central-1' en 01_create_s3_buckets.py, 02_deploy_lambda_bronze.py, etc.
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# Obtiene los datos de la cuenta y usuario actual.
# Equivalente a: sts = boto3.client('sts'); sts.get_caller_identity()
# que hacen los scripts boto3 para verificar las credenciales al inicio.
data "aws_caller_identity" "current" {}
