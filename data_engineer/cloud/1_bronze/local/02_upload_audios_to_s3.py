"""
Script para subir audios desde TAILBANK/ a S3 Bronze
Mantiene la estructura de carpetas (dementia/nodementia)

Requisitos:
    pip install boto3 tqdm

Uso:
    python 02_upload_audios_to_s3.py
"""

import boto3
import sys
from pathlib import Path
from tqdm import tqdm

# Configuración para Windows y caracteres especiales
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
import hashlib
import json
from datetime import datetime

# Configuración
REGION = 'eu-central-1'
BUCKET_NAME = 'tfm-dementia-bronze'
LOCAL_DIR = Path(__file__).parent.parent.parent / 'TAILBANK'

def calculate_md5(file_path):
    """Calcula MD5 hash de un archivo"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def upload_audio(s3_client, local_path, s3_key, metadata):
    """Sube un archivo de audio a S3 con metadatos"""
    try:
        # Calcular MD5 para verificación de integridad
        md5_hash = calculate_md5(local_path)
        
        # Metadatos adicionales
        meta = {
            'md5': md5_hash,
            'upload_date': datetime.now().isoformat(),
            'original_name': local_path.name,
            **metadata
        }
        
        # Subir archivo
        s3_client.upload_file(
            str(local_path),
            BUCKET_NAME,
            s3_key,
            ExtraArgs={
                'Metadata': meta,
                'ContentType': 'audio/wav',
                'StorageClass': 'STANDARD'
            }
        )
        
        return True, md5_hash
        
    except Exception as e:
        print(f"\n❌ Error subiendo {local_path.name}: {e}")
        return False, None

def get_audio_files(directory):
    """Obtiene todos los archivos .wav del directorio (soporta estructura plana y anidada)"""
    audio_files = []
    
    for category in ['dementia', 'nodementia']:
        category_path = directory / category
        if category_path.exists():
            # 1. Buscar archivos directamente en la carpeta de categoría
            direct_wavs = list(category_path.glob('*.wav'))
            for wav in direct_wavs:
                audio_files.append({
                    'path': wav,
                    'category': category,
                    'speaker': wav.stem,  # Usar nombre de archivo como ID
                    's3_key': f"{category}/{wav.name}"
                })

            # 2. Buscar en subdirectorios (estructura original)
            for subdir in category_path.iterdir():
                if subdir.is_dir():
                    wav_files = list(subdir.glob('*.wav'))
                    for wav in wav_files:
                        audio_files.append({
                            'path': wav,
                            'category': category,
                            'speaker': subdir.name,
                            's3_key': f"{category}/{subdir.name}/{wav.name}"
                        })
    
    return audio_files

def main():
    print("=" * 60)
    print("📤 Subiendo Audios a S3 Bronze Layer")
    print(f"📍 Bucket: s3://{BUCKET_NAME}/")
    print(f"📂 Directorio local: {LOCAL_DIR}")
    print("=" * 60)
    print()
    
    # Verificar directorio local
    if not LOCAL_DIR.exists():
        print(f"❌ Error: Directorio no encontrado: {LOCAL_DIR}")
        print(f"   Verifica que TAILBANK/ existe en la raíz del proyecto")
        return
    
    # Obtener lista de audios
    print("🔍 Buscando archivos de audio...")
    audio_files = get_audio_files(LOCAL_DIR)
    
    if not audio_files:
        print("⚠️  No se encontraron archivos .wav en TAILBANK/")
        return
    
    print(f"✅ Encontrados {len(audio_files)} archivos de audio")
    dementia_count = sum(1 for a in audio_files if a['category'] == 'dementia')
    nodementia_count = len(audio_files) - dementia_count
    print(f"   - Demencia: {dementia_count}")
    print(f"   - Sin demencia: {nodementia_count}")
    print()
    
    # Conectar a S3
    s3_client = boto3.client('s3', region_name=REGION)
    
    # Verificar que el bucket existe
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        print(f"✅ Bucket verificado: {BUCKET_NAME}")
    except Exception as e:
        print(f"❌ Error: Bucket no encontrado o sin permisos")
        print(f"   Ejecuta primero: python 01_create_s3_buckets.py")
        return
    
    print()
    print("📤 Iniciando carga de archivos...")
    print()
    
    # Subir archivos con barra de progreso
    upload_log = []
    success_count = 0
    
    for audio in tqdm(audio_files, desc="Subiendo audios", unit="archivo"):
        metadata = {
            'category': audio['category'],
            'speaker': audio['speaker']
        }
        
        success, md5 = upload_audio(
            s3_client,
            audio['path'],
            audio['s3_key'],
            metadata
        )
        
        if success:
            success_count += 1
            upload_log.append({
                'file': audio['path'].name,
                's3_key': audio['s3_key'],
                'category': audio['category'],
                'md5': md5,
                'timestamp': datetime.now().isoformat()
            })
    
    print()
    print("=" * 60)
    print(f"✅ Carga completada: {success_count}/{len(audio_files)} archivos subidos")
    print("=" * 60)
    print()
    
    # Guardar log de carga
    log_file = Path(__file__).parent / f"upload_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w') as f:
        json.dump(upload_log, f, indent=2)
    print(f"📝 Log guardado en: {log_file}")
    print()
    
    # Verificar en S3
    print("🔍 Verificando archivos en S3...")
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix='dementia/')
        dementia_s3 = response.get('KeyCount', 0)
        
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix='nodementia/')
        nodementia_s3 = response.get('KeyCount', 0)
        
        print(f"   - s3://{BUCKET_NAME}/dementia/: {dementia_s3} archivos")
        print(f"   - s3://{BUCKET_NAME}/nodementia/: {nodementia_s3} archivos")
    except Exception as e:
        print(f"⚠️  No se pudo verificar: {e}")
    
    print()
    print("📋 Próximos pasos:")
    print(f"  1. Ver archivos: aws s3 ls s3://{BUCKET_NAME}/ --recursive")
    print(f"  2. Consola AWS: https://s3.console.aws.amazon.com/s3/buckets/{BUCKET_NAME}?region={REGION}")
    print("  3. Continuar con Silver Layer (Lambda para transcripción)")
    print()

if __name__ == "__main__":
    main()
