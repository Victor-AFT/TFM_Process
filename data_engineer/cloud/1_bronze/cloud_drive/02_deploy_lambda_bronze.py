"""
Despliega la Lambda Bronze en AWS
==================================

Este script:
  1. Instala google-auth en una carpeta temporal
  2. Empaqueta el código + dependencias en un ZIP
  3. Crea/actualiza el IAM Role
  4. Crea/actualiza la Lambda en AWS

Requisitos: pip install boto3
Uso: python 02_deploy_lambda_bronze.py
"""

import boto3
import json
import time
import zipfile
import io
import sys
import subprocess
import shutil
import tempfile
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# --- Configuración ---
REGION = 'eu-central-1'
LAMBDA_NAME = 'tfm-bronze-ingest'
ROLE_NAME = 'tfm-lambda-role'

# Google Drive folder IDs
DEMENTIA_FOLDER_ID = '1GKlvbU57g80-ofCOXGwatDD4U15tpJ4S'
NODEMENTIA_FOLDER_ID = '1jm7w7J8SfuwKHpEALIK6uxR9aQZR1q8I'


def crear_role_lambda(iam):
    """Crea el IAM Role para la Lambda si no existe."""
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
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
            Description='Role para Lambdas del TFM'
        )
        role_arn = response['Role']['Arn']

        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess'
        )

        print(f"  ✅ Role creado: {role_arn}")
        print("  Esperando 10s para propagación...")
        time.sleep(10)
        return role_arn


def empaquetar_lambda_con_dependencias():
    """
    Instala google-auth en una carpeta temporal y crea un ZIP
    con el código de la Lambda + las dependencias.
    """
    # Carpeta temporal para las dependencias
    tmp_dir = tempfile.mkdtemp()
    deps_dir = Path(tmp_dir) / 'deps'

    print("  Instalando google-auth + requests (versión Linux para Lambda)...")
    subprocess.check_call([
        sys.executable, '-m', 'pip', 'install',
        'google-auth', 'requests',
        '--target', str(deps_dir),
        '--platform', 'manylinux2014_x86_64',
        '--implementation', 'cp',
        '--python-version', '3.12',
        '--only-binary=:all:',
        '--quiet', '--no-user'
    ])

    # Crear ZIP
    zip_buffer = io.BytesIO()
    lambda_file = Path(__file__).parent / '01_lambda_bronze.py'

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Añadir el código de la Lambda
        zf.write(lambda_file, 'lambda_function.py')

        # Añadir las dependencias
        for file_path in deps_dir.rglob('*'):
            if file_path.is_file():
                arcname = str(file_path.relative_to(deps_dir))
                zf.write(file_path, arcname)

    # Limpiar
    shutil.rmtree(tmp_dir, ignore_errors=True)

    zip_buffer.seek(0)
    return zip_buffer.read()


def desplegar_lambda(lambda_client, role_arn, zip_bytes, creds_json):
    """Crea o actualiza la función Lambda en AWS."""

    variables_entorno = {
        'S3_BUCKET': 'tfm-dementia-bronze',
        'DEMENTIA_FOLDER_ID': DEMENTIA_FOLDER_ID,
        'NODEMENTIA_FOLDER_ID': NODEMENTIA_FOLDER_ID,
        'GOOGLE_CREDENTIALS_JSON': creds_json,
    }

    try:
        lambda_client.update_function_code(
            FunctionName=LAMBDA_NAME,
            ZipFile=zip_bytes
        )
        time.sleep(3)
        lambda_client.update_function_configuration(
            FunctionName=LAMBDA_NAME,
            Environment={'Variables': variables_entorno}
        )
        print(f"  ✅ Lambda actualizada: {LAMBDA_NAME}")
    except lambda_client.exceptions.ResourceNotFoundException:
        lambda_client.create_function(
            FunctionName=LAMBDA_NAME,
            Runtime='python3.12',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_bytes},
            Timeout=300,
            MemorySize=512,
            Description='Bronze: Descarga audios de Google Drive a S3',
            Environment={'Variables': variables_entorno}
        )
        print(f"  ✅ Lambda creada: {LAMBDA_NAME}")


def main():
    print("=" * 50)
    print("Bronze Layer - Despliegue Lambda")
    print("=" * 50)

    # Buscar credentials.json en la misma carpeta que este script
    script_dir = Path(__file__).parent
    creds_file = script_dir / 'credentials.json'
    
    if not creds_file.exists():
        # Si no está en la misma carpeta, preguntar
        creds_file = Path(input("\nRuta al JSON del Service Account: ").strip().strip('"'))
    
    if not creds_file.exists():
        print(f"❌ No se encontró el archivo: {creds_file}")
        return
    
    print(f"  📄 Usando credenciales: {creds_file}")
    
    with open(creds_file, 'r') as f:
        creds_json = f.read()

    # Verificar que es un JSON válido
    try:
        creds_data = json.loads(creds_json)
        print(f"  ✅ Service Account: {creds_data.get('client_email', '?')}")
    except json.JSONDecodeError:
        print("❌ El archivo no es un JSON válido")
        return

    # 1. IAM Role
    print("\n1. Configurando IAM Role...")
    iam = boto3.client('iam')
    role_arn = crear_role_lambda(iam)

    # 2. Empaquetar con dependencias
    print("\n2. Empaquetando código + dependencias...")
    zip_bytes = empaquetar_lambda_con_dependencias()
    print(f"  ✅ ZIP creado ({len(zip_bytes) / 1024:.0f} KB)")

    # 3. Desplegar
    print("\n3. Desplegando Lambda...")
    lambda_client = boto3.client('lambda', region_name=REGION)
    desplegar_lambda(lambda_client, role_arn, zip_bytes, creds_json)

    print("\n" + "=" * 50)
    print("✅ Lambda Bronze desplegada")
    print("=" * 50)
    print(f"\nPuedes probarla en AWS Console:")
    print(f"  Lambda > {LAMBDA_NAME} > Test")
    print(f"  Evento:")
    print(json.dumps({"max_files": 2}, indent=2))


if __name__ == '__main__':
    main()
