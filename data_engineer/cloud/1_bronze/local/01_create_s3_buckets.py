"""
Script para crear los buckets S3 para la arquitectura Medallion
Región: eu-central-1 (Frankfurt)

Requisitos:
    pip install boto3

Uso:
    python 01_create_s3_buckets.py
"""

import boto3
import sys
from botocore.exceptions import ClientError

# Configuración para Windows y caracteres especiales
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Configuración
REGION = 'eu-central-1'
BUCKETS = {
    'bronze': 'tfm-dementia-bronze',
    'silver': 'tfm-dementia-silver',
    'gold': 'tfm-dementia-gold',
    'athena': 'tfm-dementia-athena-results'
}

def create_bucket(bucket_name, region):
    """Crea un bucket S3 con configuración óptima"""
    s3_client = boto3.client('s3', region_name=region)
    
    try:
        # Crear bucket con configuración de región
        location = {'LocationConstraint': region}
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration=location
        )
        print(f"✅ Bucket creado: {bucket_name}")
        
        # Habilitar versionado (para Bronze - backup)
        if 'bronze' in bucket_name:
            s3_client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            print(f"  → Versionado habilitado")
        
        # Configurar encriptación por defecto
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [{
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': 'AES256'
                    }
                }]
            }
        )
        print(f"  → Encriptación AES-256 configurada")
        
        # Tags para organización
        s3_client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={
                'TagSet': [
                    {'Key': 'Project', 'Value': 'TFM-Dementia'},
                    {'Key': 'Environment', 'Value': 'Production'},
                    {'Key': 'ManagedBy', 'Value': 'Python-Script'}
                ]
            }
        )
        print(f"  → Tags configurados")
        
        # Configurar lifecycle para Bronze (mover a Glacier después de 90 días)
        if 'bronze' in bucket_name:
            s3_client.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration={
                    'Rules': [{
                        'Id': 'MoveToGlacier',
                        'Status': 'Enabled',
                        'Transitions': [{
                            'Days': 90,
                            'StorageClass': 'GLACIER'
                        }]
                    }]
                }
            )
            print(f"  → Lifecycle configurado (Glacier después de 90 días)")
        
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print(f"⚠️  Bucket ya existe: {bucket_name}")
            return True
        elif e.response['Error']['Code'] == 'BucketAlreadyExists':
            print(f"❌ Error: El nombre {bucket_name} ya está tomado por otra cuenta")
            return False
        else:
            print(f"❌ Error creando bucket {bucket_name}: {e}")
            return False

def create_folder_structure(bucket_name, region):
    """Crea la estructura de carpetas en el bucket"""
    s3_client = boto3.client('s3', region_name=region)
    
    folders = []
    if 'bronze' in bucket_name:
        folders = ['dementia/', 'nodementia/']
    elif 'silver' in bucket_name:
        folders = ['transcripts/', 'features/', 'logs/']
    elif 'gold' in bucket_name:
        folders = ['dataset/']
    
    for folder in folders:
        try:
            s3_client.put_object(Bucket=bucket_name, Key=folder)
            print(f"  → Carpeta creada: {folder}")
        except ClientError as e:
            print(f"  ⚠️  Error creando carpeta {folder}: {e}")

def main():
    print("=" * 60)
    print("🚀 Creando Buckets S3 para TFM - Arquitectura Medallion")
    print(f"📍 Región: {REGION}")
    print("=" * 60)
    print()
    
    # Verificar credenciales AWS
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS Account ID: {identity['Account']}")
        print(f"✅ Usuario/Role: {identity['Arn'].split('/')[-1]}")
        print()
    except Exception as e:
        print(f"❌ Error: No se pueden verificar las credenciales AWS")
        print(f"   Ejecuta: aws configure")
        return
    
    # Crear buckets
    success_count = 0
    for layer, bucket_name in BUCKETS.items():
        print(f"\n📦 Creando bucket {layer.upper()}: {bucket_name}")
        if create_bucket(bucket_name, REGION):
            create_folder_structure(bucket_name, REGION)
            success_count += 1
    
    print()
    print("=" * 60)
    print(f"✅ Proceso completado: {success_count}/{len(BUCKETS)} buckets creados")
    print("=" * 60)
    print()
    print("📋 Próximos pasos:")
    print("  1. Verificar buckets en AWS Console: https://s3.console.aws.amazon.com/s3/buckets?region=eu-central-1")
    print("  2. Ejecutar: python 02_upload_audios_to_s3.py")
    print()

if __name__ == "__main__":
    main()
