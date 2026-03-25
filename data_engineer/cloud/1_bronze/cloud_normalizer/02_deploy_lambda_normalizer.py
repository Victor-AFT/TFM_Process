import boto3
import zipfile
import os
import time

def deploy_lambda():
    """Script para empaquetar y subir la Lambda de Normalización a AWS."""
    # Configuración principal
    lambda_name = 'tfm-bronze-normalizer'
    role_name = 'tfm-lambda-s3-role'
    bucket_name = 'tfm-dementia-bronze'
    python_file = '01_lambda_normalizer.py'
    zip_filename = 'lambda_normalizer.zip'
    region = 'eu-central-1'

    # Rutas absolutas para evitar problemas al ejecutar desde otra carpeta
    base_dir = os.path.dirname(os.path.abspath(__file__))
    python_file_path = os.path.join(base_dir, python_file)
    zip_filename_path = os.path.join(base_dir, zip_filename)

    # Clientes de AWS
    iam = boto3.client('iam')
    aws_lambda = boto3.client('lambda', region_name=region)
    s3 = boto3.client('s3', region_name=region)

    print(f"🚀 Iniciando despliegue de Lambda: {lambda_name}")

    # 1. Empaquetar el archivo Python en un ZIP
    print(f"📦 Empaquetando {python_file} en {zip_filename}...")
    with zipfile.ZipFile(zip_filename_path, 'w') as zipf:
        zipf.write(python_file_path, arcname=python_file)

    # 2. Obtener el ARN del Rol IAM existente (creado para la otra lambda)
    print("🔍 Buscando Rol IAM...")
    try:
        role = iam.get_role(RoleName=role_name)
        role_arn = role['Role']['Arn']
        print(f"✅ Rol encontrado: {role_arn}")
    except Exception as e:
        print(f"❌ Error buscando el rol '{role_name}'. Asegúrate de que existe primero.")
        print(e)
        return

    # 3. Crear o Actualizar Lambda
    try:
        print("☁️ Verificando si la función ya existe en AWS...")
        aws_lambda.get_function(FunctionName=lambda_name)
        
        print("🔄 La función ya existe. Actualizando el código...")
        with open(zip_filename_path, 'rb') as f:
            aws_lambda.update_function_code(
                FunctionName=lambda_name,
                ZipFile=f.read()
            )
        print("✅ Código actualizado con éxito!")
        
    except aws_lambda.exceptions.ResourceNotFoundException:
        print("🆕 Creando la nueva función Lambda...")
        
        with open(zip_filename_path, 'rb') as f:
            aws_lambda.create_function(
                FunctionName=lambda_name,
                Runtime='python3.12',
                Role=role_arn,
                Handler='01_lambda_normalizer.lambda_handler',
                Code={'ZipFile': f.read()},
                Description='Normaliza audios de S3 (raw/) y los guarda en (norm/)',
                Timeout=180, # 3 minutos (el audio processing puede tardar)
                MemorySize=512 # Memoria extra para audio en memoria
            )
        print("✅ Función Lambda creada con éxito!")

    # 4. Configurar el Trigger de S3 (Evento cuando se sube algo a raw/)
    print(f"🔗 Configurando Trigger desde el bucket: {bucket_name}...")
    
    # Dar permisos a S3 para invocar esta Lambda
    try:
        aws_lambda.add_permission(
            FunctionName=lambda_name,
            StatementId='s3-trigger-permission',
            Action='lambda:InvokeFunction',
            Principal='s3.amazonaws.com',
            SourceArn=f"arn:aws:s3:::{bucket_name}"
        )
    except aws_lambda.exceptions.ResourceConflictException:
        print("⏩ El permiso de S3 ya existía.")

    # Configurar la notificación en S3
    print("⏳ Esperando 5 segundos para que AWS propague los permisos IAM internamente...")
    time.sleep(5)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            s3.put_bucket_notification_configuration(
                Bucket=bucket_name,
                NotificationConfiguration={
                    'LambdaFunctionConfigurations': [
                        {
                            'LambdaFunctionArn': aws_lambda.get_function(FunctionName=lambda_name)['Configuration']['FunctionArn'],
                            'Events': ['s3:ObjectCreated:*'],
                            'Filter': {
                                'Key': {
                                    'FilterRules': [
                                        {
                                            'Name': 'prefix',
                                            'Value': 'raw/'
                                        },
                                        {
                                            'Name': 'suffix',
                                            'Value': '.wav'
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                }
            )
            print(f"✅ Trigger configurado: Se activará al subir .wav a s3://{bucket_name}/raw/")
            break
        except Exception as e:
            if "Unable to validate the following destination configurations" in str(e) and attempt < max_retries - 1:
                print(f"⚠️ S3 aún no reconoce el permiso de la Lambda, reintentando en 5s... (Intento {attempt + 1}/{max_retries})")
                time.sleep(5)
            else:
                print(f"❌ Error final configurando el Trigger de S3: {e}")
                break

    # Limpieza
    if os.path.exists(zip_filename_path):
        os.remove(zip_filename_path)
        print(f"🗑️ Archivo temporal {zip_filename} eliminado.")

if __name__ == '__main__':
    deploy_lambda()
