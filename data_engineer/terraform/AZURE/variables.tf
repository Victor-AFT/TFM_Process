
# ==============================================================================
# VARIABLES.TF — Parámetros configurables del módulo Terraform
# ==============================================================================
#
# Centraliza todos los valores configurables en un solo lugar.
# Para personalizar el despliegue, crea un archivo terraform.tfvars:
#
#   project_name   = "tfm-dementia"
#   location       = "West Europe"
#   environment    = "prod"
#   student_suffix = "miguelfr96"
#
# ==============================================================================

variable "project_name" {
  description = "Nombre base del proyecto. Se usa como prefijo en todos los recursos de Azure."
  type        = string
  default     = "tfm-dementia"
}

variable "location" {
  description = <<-EOT
    Región de Azure donde se despliega la infraestructura.
    "West Europe" (Países Bajos) equivale geográficamente a eu-central-1 (Frankfurt) de AWS
    y es la región usada en los ejercicios ej1/ej2 del módulo DE-13.
    Alternativas: "Germany West Central" para máxima cercanía a Frankfurt.
  EOT
  type        = string
  default     = "West Europe"
}

variable "environment" {
  description = "Entorno de despliegue. Se añade como sufijo al nombre del Resource Group."
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "El entorno debe ser 'dev', 'staging' o 'prod'."
  }
}

variable "student_suffix" {
  description = <<-EOT
    Sufijo único del estudiante para garantizar nombres globalmente únicos.
    Se usa en Storage Accounts y Key Vaults (restricción de Azure: nombres globales).
    Mismo patrón que ej1/ej2: md5(student_suffix) → 8 caracteres hex.
  EOT
  type        = string
  default     = "miguelfr96"
}

# ==============================================================================
# LOCALS — Valores derivados (no son inputs, son cálculos internos)
# ==============================================================================

locals {
  # Genera un sufijo de 8 caracteres único y reproducible a partir del
  # nombre del estudiante. Mismo patrón ya validado en ej1/ej2:
  #   md5("miguelfr96") → "a3f8c1d2..." → toma los 8 primeros → "a3f8c1d2"
  unique_suffix = lower(substr(md5(var.student_suffix), 0, 8))

  # Tags que se aplican a TODOS los recursos del proyecto.
  # En producción, los tags son esenciales para:
  #   - Control de costes por proyecto
  #   - Políticas de compliance (Azure Policy)
  #   - Inventario de recursos
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Course      = "MBIT-DataEngineering-2025"
  }
}
