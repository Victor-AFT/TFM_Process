import json
import urllib.parse
import boto3
import io
import wave
import struct
import math

s3 = boto3.client('s3')

def normalize_audio_basic(wav_bytes, target_rms=0.1):
    """
    Normalización de RMS en memoria usando librerías estándar de Python.
    No requiere Numpy ni SciPy, por lo que no necesita Layers de AWS.
    """
    in_buffer = io.BytesIO(wav_bytes)
    with wave.open(in_buffer, 'rb') as wav_in:
        params = wav_in.getparams()
        n_channels = params.nchannels
        sampwidth = params.sampwidth
        n_frames = params.nframes
        
        raw_frames = wav_in.readframes(n_frames)
        
    # Solo soportamos 16-bit PCM (2 bytes por muestra) que es el estandar .wav
    if sampwidth != 2:
        print(f"Advertencia: El audio tiene sampwidth={sampwidth}. Solo se soporta 16-bit. Se omite normalización.")
        return wav_bytes
        
    num_samples = n_frames * n_channels
    if num_samples == 0:
        return wav_bytes
        
    # Desempaquetar bytes a enteros (little-endian 16-bit)
    fmt = f"<{num_samples}h"
    samples = list(struct.unpack(fmt, raw_frames))
    
    # Calcular RMS actual
    sum_sq = sum((s / 32768.0) ** 2 for s in samples)
    rms_current = math.sqrt(sum_sq / num_samples)
    
    if rms_current == 0:
        return wav_bytes
        
    # Calcular factor de ganancia
    gain = target_rms / rms_current
    
    # Aplicar ganancia y clipping
    normalized_samples = []
    for s in samples:
        val = (s / 32768.0) * gain
        if val > 1.0: val = 1.0
        elif val < -1.0: val = -1.0
        normalized_samples.append(int(val * 32767))
        
    # Empaquetar de vuelta a bytes
    new_frames = struct.pack(fmt, *normalized_samples)
    
    # Escribir el nuevo wav de vuelta a un buffer en memoria
    out_buffer = io.BytesIO()
    with wave.open(out_buffer, 'wb') as wav_out:
        wav_out.setparams(params)
        wav_out.writeframes(new_frames)
        
    return out_buffer.getvalue()

def lambda_handler(event, context):
    """
    Lambda que se activa por evento de S3 cuando la Web App sube un archivo a 'raw/'.
    Lee el archivo, lo normaliza (RMS 0.1), y lo guarda en 'norm/'.
    """
    print(f"Recibido evento: {json.dumps(event)}")
    
    try:
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')
        
        print(f"Procesando archivo: s3://{bucket}/{key}")
        
        if not key.startswith("raw/"):
            print("El archivo no está en raw/. Ignorando.")
            return {'statusCode': 200, 'body': 'No pertenece a la carpeta raw/'}
            
        response = s3.get_object(Bucket=bucket, Key=key)
        wav_bytes = response['Body'].read()
        
        print(f"Audio descargado. Tamaño: {len(wav_bytes)} bytes")
        
        print("Iniciando normalización RMS a 0.1...")
        norm_wav_bytes = normalize_audio_basic(wav_bytes, target_rms=0.1)
        
        new_key = key.replace('raw/', 'norm/', 1)
        
        print(f"Subiendo archivo normalizado a: s3://{bucket}/{new_key}")
        s3.put_object(
            Bucket=bucket,
            Key=new_key,
            Body=norm_wav_bytes,
            ContentType='audio/wav'
        )
        
        print(f"¡Normalización completada! {new_key} disponible para SageMaker.")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Normalización exitosa', 'file': new_key})
        }
        
    except Exception as e:
        print(f"Error procesando {key}: {str(e)}")
        raise e
