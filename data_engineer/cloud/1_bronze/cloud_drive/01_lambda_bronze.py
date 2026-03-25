"""
Lambda Bronze — Descarga audios desde Google Drive y los guarda en S3
=====================================================================

Google Drive tiene esta estructura:
  dementia/
    Abe Burrows/        ← subcarpeta por persona
      audio1.wav
    Allan Burns/
      audio2.wav
  nodementia/
    ... (misma estructura)

Esta Lambda navega esa estructura, descarga los .wav y los sube a S3.

Parámetros (se pasan al invocar la Lambda):
  - max_files: Nº máximo de audios a descargar POR CATEGORÍA (obligatorio)

Variables de entorno:
  - S3_BUCKET: Bucket S3 destino
  - GOOGLE_CREDENTIALS_JSON: JSON completo del Service Account
  - DEMENTIA_FOLDER_ID: ID carpeta dementia
  - NODEMENTIA_FOLDER_ID: ID carpeta nodementia
"""

import boto3
import json
import os
import urllib.request
import urllib.parse
from google.oauth2 import service_account
from google.auth.transport.requests import Request


def obtener_token_google():
    """Obtiene token OAuth2 con el Service Account."""
    creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON', '')
    if not creds_json:
        raise ValueError('Falta GOOGLE_CREDENTIALS_JSON en variables de entorno.')

    creds_dict = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    credentials.refresh(Request())
    return credentials.token


def listar_contenido_drive(folder_id, token, max_results=100):
    """Lista archivos y carpetas dentro de una carpeta de Google Drive."""
    url = "https://www.googleapis.com/drive/v3/files"

    params = urllib.parse.urlencode({
        'q': f"'{folder_id}' in parents and trashed=false",
        'fields': 'files(id,name,mimeType)',
        'pageSize': max_results
    })

    request = urllib.request.Request(
        f"{url}?{params}",
        headers={'Authorization': f'Bearer {token}'}
    )
    response = urllib.request.urlopen(request)
    data = json.loads(response.read().decode())

    return data.get('files', [])


def descargar_archivo_drive(file_id, token):
    """Descarga un archivo de Google Drive."""
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    request = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    response = urllib.request.urlopen(request)
    return response.read()


def lambda_handler(event, context):
    """
    Descarga audios de Google Drive (estructura con subcarpetas) y los sube a S3.
    
    Ejemplo: {"max_files": 2}
    """

    # --- Validar parámetros ---
    max_files = event.get('max_files')
    if max_files is None:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Falta "max_files". Indica cuántos audios por categoría.'
            })
        }

    bucket = event.get('bucket', os.environ.get('S3_BUCKET', 'tfm-dementia-bronze'))

    categorias = {
        'dementia': event.get(
            'dementia_folder_id',
            os.environ.get('DEMENTIA_FOLDER_ID', '1GKlvbU57g80-ofCOXGwatDD4U15tpJ4S')
        ),
        'nodementia': event.get(
            'nodementia_folder_id',
            os.environ.get('NODEMENTIA_FOLDER_ID', '1jm7w7J8SfuwKHpEALIK6uxR9aQZR1q8I')
        )
    }

    # --- Autenticar ---
    print("🔐 Autenticando con Service Account...")
    token = obtener_token_google()
    print("✅ Token obtenido")

    # --- Procesar cada categoría ---
    s3 = boto3.client('s3')
    resultados = []

    for categoria, folder_id in categorias.items():
        if not folder_id:
            continue

        print(f"\n📂 Categoría: {categoria} (max: {max_files})")

        # Paso 1: listar subcarpetas (cada persona es una subcarpeta)
        contenido = listar_contenido_drive(folder_id, token)
        subcarpetas = [f for f in contenido if f['mimeType'] == 'application/vnd.google-apps.folder']
        archivos_raiz = [f for f in contenido if f['name'].endswith('.wav')]

        print(f"   � Subcarpetas: {len(subcarpetas)}, Archivos raíz: {len(archivos_raiz)}")

        # Recopilar archivos wav (de subcarpetas o raíz)
        wavs_a_descargar = []

        # Si hay archivos wav directamente en la carpeta
        for archivo in archivos_raiz:
            if len(wavs_a_descargar) >= max_files:
                break
            wavs_a_descargar.append({
                'id': archivo['id'],
                'name': archivo['name'],
                'persona': ''
            })

        # Si hay subcarpetas (una por persona), buscar wav dentro
        for subcarpeta in subcarpetas:
            if len(wavs_a_descargar) >= max_files:
                break

            persona = subcarpeta['name']
            archivos_persona = listar_contenido_drive(subcarpeta['id'], token, max_results=5)
            wavs_persona = [f for f in archivos_persona if f['name'].endswith('.wav')]

            for wav in wavs_persona:
                if len(wavs_a_descargar) >= max_files:
                    break
                wavs_a_descargar.append({
                    'id': wav['id'],
                    'name': wav['name'],
                    'persona': persona
                })

        print(f"   🎵 WAVs a descargar: {len(wavs_a_descargar)}")

        # Paso 2: descargar y subir a S3
        for wav in wavs_a_descargar:
            nombre = wav['name']
            persona = wav['persona']

            # Ruta en S3: categoria/persona_archivo.wav
            if persona:
                s3_key = f"{categoria}/{persona}_{nombre}"
            else:
                s3_key = f"{categoria}/{nombre}"

            print(f"   📥 Descargando: {persona}/{nombre}...")

            try:
                audio_data = descargar_archivo_drive(wav['id'], token)

                s3.put_object(
                    Bucket=bucket,
                    Key=s3_key,
                    Body=audio_data,
                    ContentType='audio/wav'
                )

                size_mb = len(audio_data) / (1024 * 1024)
                print(f"   ✅ {s3_key} ({size_mb:.1f} MB)")

                resultados.append({
                    'archivo': s3_key,
                    'status': 'ok',
                    'size_mb': round(size_mb, 2)
                })

            except Exception as e:
                print(f"   ❌ Error: {e}")
                resultados.append({
                    'archivo': s3_key,
                    'status': 'error',
                    'error': str(e)
                })

    # --- Resumen ---
    ok = sum(1 for r in resultados if r['status'] == 'ok')
    total = len(resultados)

    print(f"\n📊 Resultado: {ok}/{total} archivos cargados en S3")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'mensaje': f'Bronze: {ok}/{total} audios cargados',
            'bucket': bucket,
            'max_files_por_categoria': max_files,
            'resultados': resultados
        }, indent=2, ensure_ascii=False)
    }
