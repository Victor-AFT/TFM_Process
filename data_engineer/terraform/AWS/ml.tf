
# ==============================================================================
# ML.TF — Amazon SageMaker Notebook Instance
# ==============================================================================
#
# Traducción DIRECTA de: cloud/2_silver/01_create_notebook.py
#
# El script boto3 hace:
#   1. crear_role_notebook(iam)         → aws_iam_role.sagemaker_role (en security.tf)
#   2. crear_notebook(sm_client, role_arn) → aws_sagemaker_notebook_instance
#   3. esperar_notebook_listo(sm_client) → Terraform lo maneja automáticamente
#
# El script boto3 también crea un Lifecycle Config con LIFECYCLE_SCRIPT
# (script bash que instala librosa, opensmile, whisper, spaCy).
# Se traduce aquí como aws_sagemaker_notebook_instance_lifecycle_configuration.
#
# CONFIGURACIÓN EQUIVALENTE:
#   NOTEBOOK_NAME   = 'tfm-audio-processing'  → name = "${var.project_name}-notebook"
#   INSTANCE_TYPE   = 'ml.t3.medium'           → instance_type = "ml.t3.medium"
#   VolumeSizeInGB  = 10                        → volume_size = 10
# ==============================================================================


# ==============================================================================
# LIFECYCLE CONFIG — Script de inicio que instala las dependencias
# ==============================================================================
#
# Traducción del LIFECYCLE_SCRIPT en 01_create_notebook.py:
#   pip install librosa soundfile opensmile spacy ffmpeg-python openai-whisper
#   python -m spacy download en_core_web_md
#
# En boto3 el script se pasa como: OnStart=[{'Content': script.encode('utf-8').hex()}]
# En Terraform se pasa como base64encode() — Terraform lo codifica automáticamente.
# ==============================================================================

resource "aws_sagemaker_notebook_instance_lifecycle_configuration" "install_deps" {
  name = "${var.project_name}-lifecycle"

  # on_start se ejecuta cada vez que el Notebook arranca (no solo en la creación)
  on_start = base64encode(<<-SCRIPT
    #!/bin/bash
    set -e

    # Instalar dependencias de procesamiento de audio y NLP
    # Equivalente al LIFECYCLE_SCRIPT en 01_create_notebook.py
    pip install librosa==0.10.1 soundfile==0.12.1 opensmile==2.5.0
    pip install spacy==3.7.2 ffmpeg-python==0.2.0
    pip install openai-whisper==20231117
    python -m spacy download en_core_web_md

    echo "Dependencias del TFM instaladas correctamente"
  SCRIPT
  )
}


# ==============================================================================
# SAGEMAKER NOTEBOOK INSTANCE — Equivalente a un Jupyter en la nube
# ==============================================================================
#
# Traducción de sm_client.create_notebook_instance(...) en 01_create_notebook.py
#
# ⚠️  COSTE: Este recurso genera ~$0.05/h mientras esté en estado "InService".
#     Recuerda apagarlo desde la consola cuando no lo uses.
#     Equivalente al comentario del script original:
#     "⚠️ IMPORTANTE: Apaga el Notebook cuando termines para no gastar dinero."
#
# Para destruirlo específicamente sin destruir todo:
#   terraform destroy -target=aws_sagemaker_notebook_instance.notebook
# ==============================================================================

resource "aws_sagemaker_notebook_instance" "notebook" {
  name          = "${var.project_name}-notebook"
  role_arn      = aws_iam_role.sagemaker_role.arn
  instance_type = "ml.t3.medium" # Equivalente a INSTANCE_TYPE = 'ml.t3.medium' en boto3
  volume_size   = 10             # GB — equivalente a VolumeSizeInGB=10 en boto3

  lifecycle_config_name  = aws_sagemaker_notebook_instance_lifecycle_configuration.install_deps.name
  direct_internet_access = "Enabled"

  # El script boto3 habilita DirectInternetAccess para descargar las dependencias y modelos
}
