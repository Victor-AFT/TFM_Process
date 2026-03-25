"""
Despliega la Lambda Gold en AWS
================================

Crea la función Lambda que filtra las ~40 variables más
importantes del JSON Silver y las guarda en S3 Gold.

Uso: python 02_deploy_lambda_gold.py
"""

import boto3
import json
import time
import zipfile
import io
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# --- Configuración ---
REGION = 'eu-central-1'
LAMBDA_NAME = 'tfm-gold-filter'
ROLE_NAME = 'tfm-lambda-role'  # Reutilizamos el role creado en Bronze


def empaquetar_lambda():
    """Crea un ZIP con el código de la Lambda."""
    zip_buffer = io.BytesIO()
    lambda_file = Path(__file__).parent / '01_lambda_gold.py'
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(lambda_file, 'lambda_function.py')
    
    zip_buffer.seek(0)
    return zip_buffer.read()


def desplegar_lambda(lambda_client, role_arn, zip_bytes):
    """Crea o actualiza la Lambda Gold."""
    
    variables_entorno = {
        'SILVER_BUCKET': 'tfm-dementia-silver',
        'GOLD_BUCKET': 'tfm-dementia-gold',
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
            Timeout=60,
            MemorySize=128,
            Description='Gold: Filtra top 40 variables del JSON Silver',
            Environment={'Variables': variables_entorno}
        )
        print(f"  ✅ Lambda creada: {LAMBDA_NAME}")


def main():
    print("=" * 50)
    print("Gold Layer - Despliegue Lambda")
    print("=" * 50)
    
    # 1. Obtener Role ARN (reutilizamos el de Bronze)
    print("\n1. Buscando IAM Role...")
    iam = boto3.client('iam')
    try:
        response = iam.get_role(RoleName=ROLE_NAME)
        role_arn = response['Role']['Arn']
        print(f"  ✅ Role encontrado: {ROLE_NAME}")
    except iam.exceptions.NoSuchEntityException:
        print(f"  ❌ Role '{ROLE_NAME}' no encontrado.")
        print("  Ejecuta primero: python cloud/bronze/cloud/02_deploy_lambda_bronze.py")
        return
    
    # 2. Empaquetar
    print("\n2. Empaquetando código...")
    zip_bytes = empaquetar_lambda()
    print(f"  ✅ ZIP creado ({len(zip_bytes)} bytes)")
    
    # 3. Desplegar
    print("\n3. Desplegando Lambda...")
    lambda_client = boto3.client('lambda', region_name=REGION)
    desplegar_lambda(lambda_client, role_arn, zip_bytes)
    
    # 4. Configurar Trigger Automático S3
    print("\n4. Configurando Trigger automático S3 desde S3 Silver...")
    s3_client = boto3.client('s3', region_name=REGION)
    bucket_silver = 'tfm-dementia-silver'
    
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_NAME,
            StatementId='s3-trigger-permission-gold',
            Action='lambda:InvokeFunction',
            Principal='s3.amazonaws.com',
            SourceArn=f"arn:aws:s3:::{bucket_silver}"
        )
    except lambda_client.exceptions.ResourceConflictException:
        pass
        
    time.sleep(4)
    try:
        s3_client.put_bucket_notification_configuration(
            Bucket=bucket_silver,
            NotificationConfiguration={
                'LambdaFunctionConfigurations': [
                    {
                        'LambdaFunctionArn': lambda_client.get_function(FunctionName=LAMBDA_NAME)['Configuration']['FunctionArn'],
                        'Events': ['s3:ObjectCreated:*'],
                        'Filter': {
                            'Key': {
                                'FilterRules': [
                                    {'Name': 'prefix', 'Value': 'features/'},
                                    {'Name': 'suffix', 'Value': '.json'}
                                ]
                            }
                        }
                    }
                ]
            }
        )
        print(f"  ✅ Trigger configurado: Ejecución automática cuando haya JSONs en s3://{bucket_silver}/features/")
    except Exception as e:
        if "Unable to validate the following destination configurations" in str(e):
            print("  ⚠️ S3 aún no reconoce el permiso recién creado. Ejecuta el script de despliegue otra vez en un par de segundos.")
        else:
            print(f"  ❌ Error configurando Trigger S3: {e}")

    print("\n" + "=" * 50)
    print("✅ Lambda Gold desplegada y automatizada")
    print("=" * 50)
    print(f"\nPara ejecutarla desde la consola AWS (opcional):")
    print(f"  Lambda > {LAMBDA_NAME} > Test")
    print(f"  Evento de prueba:")
    print(json.dumps({
        "silver_key": "features/ADReSSo21_features.json",
        "gold_key": "features/gold_features.json"
    }, indent=2))


if __name__ == '__main__':
    main()
