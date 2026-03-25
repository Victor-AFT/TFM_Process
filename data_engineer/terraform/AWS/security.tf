
# ==============================================================================
# SECURITY.TF — IAM Roles y Políticas
# ==============================================================================
#
# Traducción DIRECTA de las funciones crear_role_lambda() y crear_role_notebook()
# que aparecen en:
#   cloud/1_bronze/cloud_drive/02_deploy_lambda_bronze.py
#   cloud/1_bronze/cloud_normalizer/02_deploy_lambda_normalizer.py
#   cloud/2_silver/01_create_notebook.py
#
# VENTAJA CLAVE de Terraform vs boto3:
#   En boto3, cada script comprueba si el role ya existe con iam.get_role() +
#   except NoSuchEntityException. En Terraform, la idempotencia es automática:
#   si el role ya existe con el mismo nombre, Terraform lo adopta sin error.
# ==============================================================================


# ==============================================================================
# IAM ROLE PARA LAMBDAS — "tfm-lambda-role" / "tfm-lambda-s3-role"
# ==============================================================================
#
# Traducción de crear_role_lambda() en 02_deploy_lambda_bronze.py:
#   trust_policy = { "Statement": [{"Principal": {"Service": "lambda.amazonaws.com"}, ...}] }
#   iam.create_role(RoleName=ROLE_NAME, AssumeRolePolicyDocument=...)
#   iam.attach_role_policy(PolicyArn='AWSLambdaBasicExecutionRole')
#   iam.attach_role_policy(PolicyArn='AmazonS3FullAccess')
#
# NOTA: Los scripts usan dos nombres distintos para el mismo role:
#   - 'tfm-lambda-role'    en bronze y gold
#   - 'tfm-lambda-s3-role' en normalizer
# En Terraform los unificamos en un solo role con el nombre de variables.tf.
# ==============================================================================

resource "aws_iam_role" "lambda_role" {
  name        = local.lambda_role_name
  description = "Role para las Lambdas Bronze, Normalizer y Gold del TFM"

  # Trust policy: permite que el servicio Lambda asuma este role
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Equivalente a: iam.attach_role_policy(PolicyArn='AWSLambdaBasicExecutionRole')
# Permite a las Lambdas escribir logs en CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Equivalente a: iam.attach_role_policy(PolicyArn='AmazonS3FullAccess')
# Permite a las Lambdas leer y escribir en cualquier bucket S3 de la cuenta
resource "aws_iam_role_policy_attachment" "lambda_s3_full_access" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}


# ==============================================================================
# IAM ROLE PARA SAGEMAKER — "tfm-sagemaker-notebook-role"
# ==============================================================================
#
# Traducción de crear_role_notebook() en 01_create_notebook.py:
#   trust_policy = { "Statement": [{"Principal": {"Service": "sagemaker.amazonaws.com"}, ...}] }
#   iam.attach_role_policy(PolicyArn='AmazonSageMakerFullAccess')
#   iam.attach_role_policy(PolicyArn='AmazonS3FullAccess')
# ==============================================================================

resource "aws_iam_role" "sagemaker_role" {
  name        = local.sagemaker_role_name
  description = "Role para el SageMaker Notebook Instance del TFM"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sagemaker.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Equivalente a: iam.attach_role_policy(PolicyArn='AmazonSageMakerFullAccess')
resource "aws_iam_role_policy_attachment" "sagemaker_full_access" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

# Equivalente a: iam.attach_role_policy(PolicyArn='AmazonS3FullAccess')
resource "aws_iam_role_policy_attachment" "sagemaker_s3_full_access" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}


# ==============================================================================
# IAM ROLE PARA GLUE — Necesario para el Crawler (analytics.tf)
# ==============================================================================

resource "aws_iam_role" "glue_role" {
  name        = "${var.project_name}-glue-role"
  description = "Role para el Glue Crawler que indexa la capa Gold"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service_role" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy_attachment" "glue_s3_read" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}
