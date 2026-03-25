
# ==============================================================================
# COMPUTE.TF — AWS Lambda Functions y Triggers S3
# ==============================================================================
#
# Traducción DIRECTA de:
#   cloud/1_bronze/cloud_drive/02_deploy_lambda_bronze.py       → aws_lambda_function.bronze_ingest
#   cloud/1_bronze/cloud_normalizer/02_deploy_lambda_normalizer.py → aws_lambda_function.normalizer
#   cloud/3_gold/02_deploy_lambda_gold.py                        → aws_lambda_function.gold_filter
#
# VENTAJA CLAVE vs boto3:
#   Los scripts boto3 empaquetan el ZIP manualmente con subprocess + zipfile.
#   Terraform usa el provider "archive" para generar los ZIPs automáticamente
#   referenciando los archivos Python existentes en cloud/ — sin pasos manuales.
#
# NOTA SOBRE DEPENDENCIAS EXTERNAS (Lambda Bronze):
#   La Lambda Bronze requiere google-auth (instalado vía subprocess en boto3).
#   Para producción, el ZIP debe construirse con: pip install google-auth -t .
#   Ver el comentario en aws_lambda_function.bronze_ingest.
# ==============================================================================


# ==============================================================================
# CLOUDWATCH LOG GROUPS — Logs de cada Lambda
# ==============================================================================
#
# CloudWatch crea los log groups automáticamente en la primera ejecución,
# pero definirlos en Terraform permite controlar la retención y evitar
# que queden huérfanos tras un terraform destroy.
# ==============================================================================

resource "aws_cloudwatch_log_group" "lambda_bronze" {
  name              = "/aws/lambda/${local.lambda_bronze_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "lambda_normalizer" {
  name              = "/aws/lambda/${local.lambda_normalizer_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "lambda_gold" {
  name              = "/aws/lambda/${local.lambda_gold_name}"
  retention_in_days = 14
}


# ==============================================================================
# EMPAQUETADO DE LAS LAMBDAS — Generación automática de ZIPs
# ==============================================================================
#
# En boto3, el empaquetado se hace manualmente en empaquetar_lambda_con_dependencias():
#   zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED)
#   zf.write(lambda_file, 'lambda_function.py')
#
# Terraform lo hace declarativamente con el provider "archive".
# Los ZIPs se generan en .terraform/lambda_builds/ (ignorados por git).
# ==============================================================================

# Lambda Bronze: empaqueta 01_lambda_bronze.py como lambda_function.py
# (mismo rename que hace el script boto3: zf.write(lambda_file, 'lambda_function.py'))
data "archive_file" "lambda_bronze" {
  type = "zip"
  source {
    content  = file("${path.module}/../../cloud/1_bronze/cloud_drive/01_lambda_bronze.py")
    filename = "lambda_function.py"
  }
  output_path = "${path.module}/.lambda_builds/bronze_ingest.zip"
}

# Lambda Normalizer: empaqueta 01_lambda_normalizer.py
# (el handler en boto3 es '01_lambda_normalizer.lambda_handler')
data "archive_file" "lambda_normalizer" {
  type = "zip"
  source {
    content  = file("${path.module}/../../cloud/1_bronze/cloud_normalizer/01_lambda_normalizer.py")
    filename = "01_lambda_normalizer.py"
  }
  output_path = "${path.module}/.lambda_builds/normalizer.zip"
}

# Lambda Gold: empaqueta 01_lambda_gold.py como lambda_function.py
data "archive_file" "lambda_gold" {
  type = "zip"
  source {
    content  = file("${path.module}/../../cloud/3_gold/01_lambda_gold.py")
    filename = "lambda_function.py"
  }
  output_path = "${path.module}/.lambda_builds/gold_filter.zip"
}


# ==============================================================================
# LAMBDA 1: Bronze Ingest — Descarga Google Drive → S3 Bronze
# ==============================================================================
#
# Traducción de desplegar_lambda() en 02_deploy_lambda_bronze.py:
#   lambda_client.create_function(
#     FunctionName=LAMBDA_NAME,         → name = local.lambda_bronze_name
#     Runtime='python3.12',             → runtime = "python3.12"
#     Role=role_arn,                    → role = aws_iam_role.lambda_role.arn
#     Handler='lambda_function.lambda_handler', → handler = "lambda_function.lambda_handler"
#     Timeout=300,                      → timeout = 300
#     MemorySize=512,                   → memory_size = 512
#     Environment={'Variables': {...}}  → environment { variables = {...} }
#   )
#
# NOTA: Esta Lambda requiere google-auth en el ZIP para funcionar.
# Para empaquetar con dependencias:
#   pip install google-auth requests -t lambda_package/
#   cp 01_lambda_bronze.py lambda_package/lambda_function.py
#   cd lambda_package && zip -r ../bronze_with_deps.zip .
# Y luego cambiar el data.archive_file por:
#   filename = ".lambda_builds/bronze_with_deps.zip"
# ==============================================================================

resource "aws_lambda_function" "bronze_ingest" {
  function_name = local.lambda_bronze_name
  description   = "Bronze: Descarga audios de Google Drive a S3"
  role          = aws_iam_role.lambda_role.arn

  filename         = data.archive_file.lambda_bronze.output_path
  source_code_hash = data.archive_file.lambda_bronze.output_base64sha256

  handler     = "lambda_function.lambda_handler"
  runtime     = "python3.12"
  timeout     = 300 # 5 minutos — equivalente a Timeout=300 en boto3
  memory_size = 512 # MB — equivalente a MemorySize=512 en boto3

  environment {
    variables = {
      S3_BUCKET            = aws_s3_bucket.bronze.bucket
      DEMENTIA_FOLDER_ID   = var.google_drive_dementia_folder_id
      NODEMENTIA_FOLDER_ID = var.google_drive_nodementia_folder_id
      # SEGURIDAD: En boto3 se pasa como texto plano. Aquí también por simplicidad,
      # pero la práctica correcta es usar AWS Secrets Manager o SSM Parameter Store.
      GOOGLE_CREDENTIALS_JSON = var.google_credentials_json
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_cloudwatch_log_group.lambda_bronze
  ]
}


# ==============================================================================
# LAMBDA 2: Normalizer — Normaliza raw/*.wav → norm/
# ==============================================================================
#
# Traducción de la función en 02_deploy_lambda_normalizer.py:
#   Runtime='python3.12', Timeout=180, MemorySize=512
#   Handler='01_lambda_normalizer.lambda_handler'
# ==============================================================================

resource "aws_lambda_function" "normalizer" {
  function_name = local.lambda_normalizer_name
  description   = "Bronze: Normaliza audios raw/ (16kHz, RMS 0.1) → norm/"
  role          = aws_iam_role.lambda_role.arn

  filename         = data.archive_file.lambda_normalizer.output_path
  source_code_hash = data.archive_file.lambda_normalizer.output_base64sha256

  handler     = "01_lambda_normalizer.lambda_handler"
  runtime     = "python3.12"
  timeout     = 180 # 3 minutos — equivalente a Timeout=180 en boto3
  memory_size = 512

  environment {
    variables = {
      BRONZE_BUCKET = aws_s3_bucket.bronze.bucket
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_cloudwatch_log_group.lambda_normalizer
  ]
}

# Permiso para que S3 pueda invocar la Lambda Normalizer.
# Equivalente a: lambda_client.add_permission(StatementId='s3-trigger-permission', ...)
resource "aws_lambda_permission" "allow_s3_invoke_normalizer" {
  statement_id  = "s3-trigger-permission"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.normalizer.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.bronze.arn
}

# Trigger S3 → Lambda Normalizer al subir .wav a raw/
# Equivalente a: s3.put_bucket_notification_configuration(
#   Filter: prefix='raw/', suffix='.wav'
# )
resource "aws_s3_bucket_notification" "bronze_raw_trigger" {
  # depends_on es crítico: S3 no puede configurar el trigger hasta que
  # aws_lambda_permission exista. En boto3 esto se hacía con time.sleep(5).
  depends_on = [aws_lambda_permission.allow_s3_invoke_normalizer]

  bucket = aws_s3_bucket.bronze.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.normalizer.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/"
    filter_suffix       = ".wav"
  }
}


# ==============================================================================
# LAMBDA 3: Gold Filter — Filtra ~44 variables Silver → Gold
# ==============================================================================
#
# Traducción de desplegar_lambda() en 02_deploy_lambda_gold.py:
#   Runtime='python3.12', Timeout=60, MemorySize=128
# ==============================================================================

resource "aws_lambda_function" "gold_filter" {
  function_name = local.lambda_gold_name
  description   = "Gold: Filtra top 44 variables del JSON Silver → S3 Gold"
  role          = aws_iam_role.lambda_role.arn

  filename         = data.archive_file.lambda_gold.output_path
  source_code_hash = data.archive_file.lambda_gold.output_base64sha256

  handler     = "lambda_function.lambda_handler"
  runtime     = "python3.12"
  timeout     = 60  # 1 minuto — equivalente a Timeout=60 en boto3
  memory_size = 128 # MB — equivalente a MemorySize=128 en boto3

  environment {
    variables = {
      SILVER_BUCKET = aws_s3_bucket.silver.bucket
      GOLD_BUCKET   = aws_s3_bucket.gold.bucket
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_cloudwatch_log_group.lambda_gold
  ]
}

# Permiso para que S3 pueda invocar la Lambda Gold
resource "aws_lambda_permission" "allow_s3_invoke_gold" {
  statement_id  = "s3-trigger-permission-gold"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.gold_filter.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.silver.arn
}

# Trigger S3 → Lambda Gold al subir .json a features/
# Equivalente a: put_bucket_notification_configuration(
#   Filter: prefix='features/', suffix='.json'
# )
resource "aws_s3_bucket_notification" "silver_features_trigger" {
  depends_on = [aws_lambda_permission.allow_s3_invoke_gold]

  bucket = aws_s3_bucket.silver.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.gold_filter.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "features/"
    filter_suffix       = ".json"
  }
}
