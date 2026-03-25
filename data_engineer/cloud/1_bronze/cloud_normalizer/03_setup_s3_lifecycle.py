import boto3
from botocore.exceptions import ClientError

def setup_s3_glacier_rule():
    """Configura una regla de ciclo de vida en S3 para enviar archivos de 'raw/' a Glacier."""
    bucket_name = 'tfm-dementia-bronze'
    rule_id = 'MoveRawToGlacier'
    # Glacier Flexible Retrieval (GLACIER) o Glacier Deep Archive (DEEP_ARCHIVE)
    storage_class = 'GLACIER' 
    prefix = 'raw/'
    
    s3 = boto3.client('s3')
    
    print(f"🧊 Configurando regla de Glacier en {bucket_name} para la carpeta {prefix}...")
    
    # Configuración de la regla de Lifecycle
    lifecycle_config = {
        'Rules': [
            {
                'ID': rule_id,
                'Filter': {
                    'Prefix': prefix
                },
                'Status': 'Enabled',
                'Transitions': [
                    {
                        'Days': 0, # Mover inmediatamente (se aplica al día siguiente en la zona horaria UTC)
                        'StorageClass': storage_class
                    }
                ]
            }
        ]
    }
    
    try:
        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle_config
        )
        print(f"✅ ¡Regla de ciclo de vida creada con éxito!")
        print(f"   Todo lo que entre en s3://{bucket_name}/{prefix} se moverá a Amazon {storage_class} a las 00:00 UTC automáticamente.")
    except ClientError as e:
        print(f"❌ Error configurando la regla: {e}")

if __name__ == '__main__':
    setup_s3_glacier_rule()
