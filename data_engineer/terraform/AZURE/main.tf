
# ==============================================================================
# MAIN.TF — Configuración del Provider y Resource Group
# ==============================================================================
#
# Este archivo es el punto de entrada del módulo Terraform.
# Define el proveedor de Azure (azurerm) y el contenedor raíz de todos
# los recursos del proyecto: el Resource Group.
#
# Equivalente al script boto3: no existe un único equivalente — en boto3
# el cliente de cada servicio asume implícitamente la cuenta y región.
# En Terraform, el provider centraliza esa configuración.
# ==============================================================================

terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # RECOMENDACIÓN DE INDUSTRIA: Usar backend remoto en producción.
  # Descomenta y configura para que el tfstate no viva en local:
  #
  # backend "azurerm" {
  #   resource_group_name  = "rg-tfstate"
  #   storage_account_name = "tfstatetfm"
  #   container_name       = "tfstate"
  #   key                  = "tfm-dementia.terraform.tfstate"
  # }
}

provider "azurerm" {
  features {
    key_vault {
      # Permite destruir Key Vaults con purge en terraform destroy.
      # Útil en entornos de desarrollo/demo para limpiar completamente.
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }

  # Evita que Terraform registre automáticamente resource providers de Azure.
  # Consistente con la configuración de ej1 y ej2 del módulo.
  resource_provider_registrations = "none"
}

# Data source que obtiene la identidad del operador actual (el que ejecuta terraform apply).
# Necesario en security.tf para dar al operador permisos sobre el Key Vault.
data "azurerm_client_config" "current" {}

# ==============================================================================
# RESOURCE GROUP — Contenedor lógico de todos los recursos del proyecto
# ==============================================================================
# En AWS no existe un equivalente directo: los recursos se agrupan
# por región y por tags. En Azure, el Resource Group es obligatorio
# y es la unidad de gestión, facturación y control de acceso.
# ==============================================================================

resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.project_name}-${var.environment}"
  location = var.location
  tags     = local.common_tags
}
