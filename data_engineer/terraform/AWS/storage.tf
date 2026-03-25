
# ==============================================================================
# STORAGE.TF — Buckets S3 y Arquitectura Medallion
# ==============================================================================
#
# Traducción DIRECTA de: cloud/1_bronze/local/01_create_s3_buckets.py
#                         cloud/1_bronze/cloud_normalizer/03_setup_s3_lifecycle.py
#
# El script boto3 crea 4 buckets con llamadas imperativas:
#   s3_client.create_bucket(...)
#   s3_client.put_bucket_versioning(...)
#   s3_client.put_bucket_encryption(...)
#   s3_client.put_bucket_tagging(...)
#   s3_client.put_bucket_lifecycle_configuration(...)
#
# Aquí cada una de esas llamadas se convierte en un recurso Terraform declarativo.
# La ventaja: si ya existen, Terraform NO los vuelve a crear (idempotencia nativa).
# El script boto3 también tiene lógica try/except para manejar esto — en Terraform
# no hace falta.
# ==============================================================================


# ==============================================================================
# BUCKET BRONZE — s3://tfm-dementia-bronze
# ==============================================================================

resource "aws_s3_bucket" "bronze" {
  bucket = local.bucket_bronze

  # Si el bucket ya existe de un despliegue anterior con boto3 y lo quieres
  # adoptar en lugar de recrear: terraform import aws_s3_bucket.bronze tfm-dementia-bronze
}

# Equivalente a: s3_client.put_bucket_versioning(VersioningConfiguration={'Status': 'Enabled'})
# Solo habilitado en Bronze (backup de los audios originales)
resource "aws_s3_bucket_versioning" "bronze" {
  bucket = aws_s3_bucket.bronze.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Equivalente a: s3_client.put_bucket_encryption(SSEAlgorithm='AES256')
resource "aws_s3_bucket_server_side_encryption_configuration" "bronze" {
  bucket = aws_s3_bucket.bronze.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "bronze" {
  bucket                  = aws_s3_bucket.bronze.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Estructura de carpetas en Bronze (objetos vacíos que simulan directorios)
# Equivalente a: create_folder_structure() en 01_create_s3_buckets.py
resource "aws_s3_object" "bronze_dementia_folder" {
  bucket  = aws_s3_bucket.bronze.id
  key     = "dementia/"
  content = ""
}

resource "aws_s3_object" "bronze_nodementia_folder" {
  bucket  = aws_s3_bucket.bronze.id
  key     = "nodementia/"
  content = ""
}

resource "aws_s3_object" "bronze_raw_folder" {
  bucket  = aws_s3_bucket.bronze.id
  key     = "raw/"
  content = ""
}

resource "aws_s3_object" "bronze_norm_folder" {
  bucket  = aws_s3_bucket.bronze.id
  key     = "norm/"
  content = ""
}


# ==============================================================================
# LIFECYCLE POLICY — S3 Glacier para audios crudos
# ==============================================================================
#
# Traducción DIRECTA de: cloud/1_bronze/cloud_normalizer/03_setup_s3_lifecycle.py
#
# El script boto3:
#   storage_class = 'GLACIER'
#   prefix = 'raw/'
#   Transitions: [{'Days': 0, 'StorageClass': storage_class}]
#
# Days: 0 significa que se aplica el siguiente UTC midnight (no es instantáneo).
# ==============================================================================

resource "aws_s3_bucket_lifecycle_configuration" "bronze_glacier" {
  # Debe ejecutarse DESPUÉS de que el versionado esté activo
  depends_on = [aws_s3_bucket_versioning.bronze]

  bucket = aws_s3_bucket.bronze.id

  rule {
    id     = "MoveRawToGlacier"
    status = "Enabled"

    filter {
      prefix = "raw/" # Solo los audios crudos van a Glacier — norm/ permanece accesible
    }

    transition {
      days          = 0         # El siguiente UTC midnight (equivalente a Days: 0 en boto3)
      storage_class = "GLACIER" # Amazon S3 Glacier Flexible Retrieval
    }
  }
}


# ==============================================================================
# BUCKET SILVER — s3://tfm-dementia-silver
# ==============================================================================

resource "aws_s3_bucket" "silver" {
  bucket = local.bucket_silver
}

resource "aws_s3_bucket_server_side_encryption_configuration" "silver" {
  bucket = aws_s3_bucket.silver.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "silver" {
  bucket                  = aws_s3_bucket.silver.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Estructura de carpetas Silver (transcripts/, features/, logs/)
resource "aws_s3_object" "silver_transcripts_folder" {
  bucket  = aws_s3_bucket.silver.id
  key     = "transcripts/"
  content = ""
}

resource "aws_s3_object" "silver_features_folder" {
  bucket  = aws_s3_bucket.silver.id
  key     = "features/"
  content = ""
}

resource "aws_s3_object" "silver_logs_folder" {
  bucket  = aws_s3_bucket.silver.id
  key     = "logs/"
  content = ""
}


# ==============================================================================
# BUCKET GOLD — s3://tfm-dementia-gold
# ==============================================================================

resource "aws_s3_bucket" "gold" {
  bucket = local.bucket_gold
}

resource "aws_s3_bucket_server_side_encryption_configuration" "gold" {
  bucket = aws_s3_bucket.gold.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "gold" {
  bucket                  = aws_s3_bucket.gold.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "gold_dataset_folder" {
  bucket  = aws_s3_bucket.gold.id
  key     = "dataset/"
  content = ""
}


# ==============================================================================
# BUCKET ATHENA RESULTS — s3://tfm-dementia-athena-results
# ==============================================================================

resource "aws_s3_bucket" "athena_results" {
  bucket = local.bucket_athena
}

resource "aws_s3_bucket_server_side_encryption_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket                  = aws_s3_bucket.athena_results.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
