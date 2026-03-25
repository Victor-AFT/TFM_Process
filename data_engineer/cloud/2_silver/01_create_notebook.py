"""
Crea un SageMaker Notebook Instance para procesar audios
=========================================================

Un SageMaker Notebook es un Jupyter Notebook en la nube.
No necesita Docker. Abres el notebook, instalas librerías con pip,
y ejecutas tu código. Igual que en tu PC pero en AWS.

Este script:
  1. Crea un IAM Role para el Notebook (si no existe)
  2. Crea la instancia de Notebook
  3. Te da el link para abrirlo

Uso: python 01_create_notebook.py
Coste: ~$0.05/hora (ml.t3.medium). Apágalo cuando termines.
"""

import boto3
import json
import time
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# --- Configuración ---
REGION = 'eu-central-1'
NOTEBOOK_NAME = 'tfm-audio-processing'
ROLE_NAME = 'tfm-sagemaker-notebook-role'
INSTANCE_TYPE = 'ml.t3.medium'  # Barato: ~$0.05/hora, 2 vCPUs, 4 GB RAM


def crear_role_notebook(iam):
    """Crea el IAM Role para el Notebook."""
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "sagemaker.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }
    
    try:
        response = iam.get_role(RoleName=ROLE_NAME)
        print(f"  ✅ Role ya existe: {ROLE_NAME}")
        return response['Role']['Arn']
        
    except iam.exceptions.NoSuchEntityException:
        print(f"  Creando role {ROLE_NAME}...")
        
        response = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role para SageMaker Notebook del TFM'
        )
        role_arn = response['Role']['Arn']
        
        # Permisos: SageMaker + S3
        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/AmazonSageMakerFullAccess'
        )
        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess'
        )
        
        print(f"  ✅ Role creado: {role_arn}")
        print("  Esperando 10s para propagación...")
        time.sleep(10)
        
        return role_arn


# Script de arranque: instala las dependencias automáticamente al crear el Notebook
LIFECYCLE_SCRIPT = """#!/bin/bash
set -e

# Instalar dependencias de audio
pip install librosa soundfile opensmile spacy ffmpeg-python
pip install openai-whisper
python -m spacy download en_core_web_md

echo "✅ Dependencias instaladas correctamente"
"""


def crear_notebook(sm_client, role_arn):
    """Crea la instancia de SageMaker Notebook."""
    
    # Crear lifecycle config (instala dependencias al arrancar)
    lifecycle_name = f'{NOTEBOOK_NAME}-lifecycle'
    try:
        sm_client.create_notebook_instance_lifecycle_config(
            NotebookInstanceLifecycleConfigName=lifecycle_name,
            OnStart=[{'Content': LIFECYCLE_SCRIPT.encode('utf-8').hex()}]
        )
    except sm_client.exceptions.ClientError as e:
        if 'already exists' in str(e).lower() or 'ResourceInUse' in str(e):
            print(f"  Lifecycle config ya existe: {lifecycle_name}")
        else:
            raise
    
    # Crear el notebook
    try:
        sm_client.create_notebook_instance(
            NotebookInstanceName=NOTEBOOK_NAME,
            InstanceType=INSTANCE_TYPE,
            RoleArn=role_arn,
            VolumeSizeInGB=10,
            DirectInternetAccess='Enabled',
        )
        print(f"  ✅ Notebook creado: {NOTEBOOK_NAME}")
        print(f"  Tipo: {INSTANCE_TYPE}")
        print(f"  Disco: 10 GB")
        
    except sm_client.exceptions.ClientError as e:
        if 'already exists' in str(e).lower() or 'ResourceInUse' in str(e):
            print(f"  Notebook ya existe: {NOTEBOOK_NAME}")
        else:
            raise


def esperar_notebook_listo(sm_client):
    """Espera hasta que el Notebook esté listo para usar."""
    
    print("\n  Esperando a que el Notebook arranque...")
    print("  (esto puede tardar 3-5 minutos)")
    
    while True:
        response = sm_client.describe_notebook_instance(
            NotebookInstanceName=NOTEBOOK_NAME
        )
        status = response['NotebookInstanceStatus']
        
        if status == 'InService':
            url = response.get('Url', '')
            print(f"\n  ✅ Notebook LISTO")
            print(f"  URL: https://{url}")
            return url
        elif status == 'Failed':
            print(f"\n  ❌ Error al crear el Notebook")
            print(f"  Razón: {response.get('FailureReason', 'Desconocida')}")
            return None
        else:
            print(f"  Estado: {status}...")
            time.sleep(30)


def main():
    print("=" * 50)
    print("Silver Layer - SageMaker Notebook")
    print("=" * 50)
    
    # 1. IAM Role
    print("\n1. Configurando IAM Role...")
    iam = boto3.client('iam')
    role_arn = crear_role_notebook(iam)
    
    # 2. Crear Notebook
    print("\n2. Creando Notebook Instance...")
    sm_client = boto3.client('sagemaker', region_name=REGION)
    crear_notebook(sm_client, role_arn)
    
    # 3. Esperar
    print("\n3. Esperando...")
    url = esperar_notebook_listo(sm_client)
    
    if url:
        print("\n" + "=" * 50)
        print("✅ Notebook listo")
        print("=" * 50)
        print(f"\nAbre el Notebook en: https://{url}")
        print("\nPasos dentro del Notebook:")
        print("  1. Crea un nuevo notebook (Python 3)")
        print("  2. Copia el código de process_silver.py")
        print("  3. Ejecuta las celdas")
        print("  4. Los resultados se guardan en S3 Silver")
        print("\n⚠️  IMPORTANTE: Apaga el Notebook cuando termines")
        print("   para no gastar dinero innecesariamente.")


if __name__ == '__main__':
    main()
