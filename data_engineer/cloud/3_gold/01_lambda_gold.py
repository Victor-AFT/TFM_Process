"""
Lambda Gold — Filtra las variables más importantes del JSON Silver
===================================================================

Lee el JSON completo de S3 Silver (con todas las features extraídas),
selecciona solo las variables más importantes para Machine Learning,
y guarda un JSON limpio y aplanado en S3 Gold.

Parámetros (se pasan al invocar la Lambda):
  - silver_bucket: Bucket S3 origen (por defecto: variable de entorno)
  - silver_key: Clave del archivo JSON en Silver
  - gold_bucket: Bucket S3 destino (por defecto: variable de entorno)
  - gold_key: Clave del archivo JSON de salida en Gold

Variables de entorno:
  - SILVER_BUCKET: Bucket S3 Silver (por defecto: tfm-dementia-silver)
  - GOLD_BUCKET: Bucket S3 Gold (por defecto: tfm-dementia-gold)
"""

import boto3
import json
import os


# --- Variables que seleccionamos para ML ---
# Estas son las ~40 variables más relevantes para detectar demencia.
# Están organizadas por tipo para que sea fácil de entender y modificar.

VARIABLES_SELECCIONADAS = {
    
    # --- Metadatos (identificación) ---
    'metadatos': [
        'audio',         # Nombre del archivo
        'dementia',      # Etiqueta: dementia / nodementia
    ],
    
    # --- Librosa: características acústicas ---
    'librosa': [
        'mfcc_1_mean',               # Coeficientes cepstrales (timbre de voz)
        'mfcc_2_mean',
        'mfcc_3_mean',
        'mfcc_4_mean',
        'mfcc_5_mean',
        'spectral_centroid_mean',     # Centro espectral (brillo de la voz)
        'spectral_rolloff_mean',      # Rolloff espectral
        'spectral_bandwidth_mean',    # Ancho de banda espectral
        'zcr_mean',                   # Tasa de cruces por cero
        'pitch_mean',                 # Tono medio
        'pitch_std',                  # Variabilidad del tono
        'jitter',                     # Irregularidad del tono
        'shimmer',                    # Irregularidad de amplitud
        'rms_mean',                   # Energía media
        'hnr_db',                     # Relación armónico-ruido
        'duration',                   # Duración del audio
        'tempo',                      # Velocidad del habla
        'Skewness_pause_duration',    # Asimetría de pausas
        'Kurtosis_pause_duration',    # Curtosis de pausas
    ],
    
    # --- OpenSMILE: características eGeMAPSv02 ---
    'opensmile': [
        'F0semitoneFrom27.5Hz_sma3nz_amean',      # Frecuencia fundamental media
        'F0semitoneFrom27.5Hz_sma3nz_stddevNorm',  # Variabilidad F0
        'loudness_sma3_amean',                      # Volumen medio
        'loudness_sma3_stddevNorm',                 # Variabilidad de volumen
        'jitterLocal_sma3nz_amean',                 # Jitter (OpenSMILE)
        'shimmerLocaldB_sma3nz_amean',              # Shimmer (OpenSMILE)
        'HNRdBACF_sma3nz_amean',                    # HNR (OpenSMILE)
        'F1frequency_sma3nz_amean',                  # Primer formante
        'F2frequency_sma3nz_amean',                  # Segundo formante
        'F3frequency_sma3nz_amean',                  # Tercer formante
        'MeanVoicedSegmentLengthSec',                # Duración media segmentos con voz
        'MeanUnvoicedSegmentLength',                 # Duración media silencios
        'VoicedSegmentsPerSec',                      # Ritmo del habla
    ],
    
    # --- Whisper + spaCy: características lingüísticas ---
    'whisper_spacy': [
        'n_words',                 # Número de palabras
        'n_sents',                 # Número de oraciones
        'mean_words_per_sent',     # Palabras por oración
        'ttr',                     # Type-Token Ratio (diversidad léxica)
        'noun_ratio',              # Proporción de sustantivos
        'verb_ratio',              # Proporción de verbos
        'adj_ratio',               # Proporción de adjetivos
        'Filler_frequency',        # Frecuencia de muletillas (um, eh...)
        'Local_coherence',         # Coherencia entre oraciones
        'Lexical_errors',          # Errores léxicos
    ],
}


def aplanar_registro(registro):
    """
    Aplana un registro del JSON Silver.
    
    El JSON Silver tiene esta estructura anidada:
        {
            "audio": "...",
            "dementia": "...",
            "parametros_librosa": { ... },
            "parametros_opensmile": { ... },
            "parametros_whisperSpacy": { ... }
        }
    
    Esta función lo convierte en un diccionario plano con solo
    las variables seleccionadas.
    """
    resultado = {}
    
    # Metadatos (nivel raíz)
    for var in VARIABLES_SELECCIONADAS['metadatos']:
        if var in registro:
            resultado[var] = registro[var]
    
    # Librosa (dentro de parametros_librosa)
    librosa_params = registro.get('parametros_librosa', {})
    for var in VARIABLES_SELECCIONADAS['librosa']:
        if var in librosa_params:
            resultado[var] = librosa_params[var]
    
    # OpenSMILE (dentro de parametros_opensmile)
    opensmile_params = registro.get('parametros_opensmile', {})
    for var in VARIABLES_SELECCIONADAS['opensmile']:
        if var in opensmile_params:
            resultado[var] = opensmile_params[var]
    
    # Whisper + spaCy (dentro de parametros_whisperSpacy)
    whisper_params = registro.get('parametros_whisperSpacy', {})
    for var in VARIABLES_SELECCIONADAS['whisper_spacy']:
        if var in whisper_params:
            resultado[var] = whisper_params[var]
    
    return resultado


def lambda_handler(event, context):
    """
    Lee JSON de S3 Silver, filtra variables, guarda en S3 Gold.
    
    Ejemplo de invocación:
        {
            "silver_key": "features/ADReSSo21_latest.json",
            "gold_key": "features/gold_features.json"
        }
    """
    s3 = boto3.client('s3')
    
    # --- Detectar si es un Evento Automático de S3 o Manual ---
    silver_bucket = None
    silver_key = None
    gold_bucket = os.environ.get('GOLD_BUCKET', 'tfm-dementia-gold')
    gold_key = None

    if 'Records' in event and len(event['Records']) > 0:
        record = event['Records'][0]
        if 's3' in record:
            silver_bucket = record['s3']['bucket']['name']
            import urllib.parse
            silver_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
            nombre_archivo = silver_key.split('/')[-1]
            gold_key = f"features/gold_{nombre_archivo}"
    
    # Si no vino por S3 (ejecución manual de prueba en la consola)
    if silver_bucket is None:
        silver_bucket = event.get('silver_bucket', os.environ.get('SILVER_BUCKET', 'tfm-dementia-silver'))
        silver_key = event.get('silver_key', 'features/ADReSSo21_features.json')
        gold_bucket = event.get('gold_bucket', gold_bucket)
        gold_key = event.get('gold_key', 'features/gold_features.json')
    
    print(f"📥 Leyendo: s3://{silver_bucket}/{silver_key}")
    
    # --- Leer JSON de Silver ---
    try:
        response = s3.get_object(Bucket=silver_bucket, Key=silver_key)
        datos_silver = json.loads(response['Body'].read().decode())
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': f'No se pudo leer el archivo de Silver: {str(e)}'
            })
        }
    
    print(f"📊 Registros leídos: {len(datos_silver)}")
    
    # --- Filtrar y aplanar ---
    datos_gold = []
    
    for registro in datos_silver:
        registro_filtrado = aplanar_registro(registro)
        datos_gold.append(registro_filtrado)
    
    # Contar variables
    if datos_gold:
        n_variables = len(datos_gold[0])
        print(f"✅ Variables seleccionadas: {n_variables}")
    
    # --- Guardar en S3 Gold ---
    s3.put_object(
        Bucket=gold_bucket,
        Key=gold_key,
        Body=json.dumps(datos_gold, indent=2, ensure_ascii=False),
        ContentType='application/json'
    )
    
    print(f"📤 Guardado en: s3://{gold_bucket}/{gold_key}")
    
    # --- Resumen ---
    resumen = {
        'mensaje': f'Gold: {len(datos_gold)} registros con {n_variables} variables',
        'origen': f's3://{silver_bucket}/{silver_key}',
        'destino': f's3://{gold_bucket}/{gold_key}',
        'registros': len(datos_gold),
        'variables': n_variables,
        'lista_variables': list(datos_gold[0].keys()) if datos_gold else []
    }
    
    print(f"\n📊 Resultado: {len(datos_gold)} registros × {n_variables} variables → S3 Gold")
    
    return {
        'statusCode': 200,
        'body': json.dumps(resumen, indent=2, ensure_ascii=False)
    }
