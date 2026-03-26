import librosa
import soundfile as sf
import opensmile
import pandas as pd
import numpy as np
from pathlib import Path
import os
import uuid
import json


origin_demential='Repo_Demential/'
origin_nodemential='Repo_Nodemential/'
dest_demential='Repo_Demential_Normalizado/'
#SCORE AL AUDIO
def audio_quality_score(y, sr):
    score = 100
    detalles = {}

    # 1️⃣ RMS (volumen promedio de la señal)
    # Calcula la energía media del audio.
    # Un RMS muy bajo indica audio débil o silencioso.
    # Un RMS muy alto indica audio saturado o mal normalizado.
    rms = np.sqrt(np.mean(y**2))
    detalles["rms"] = rms

    # Penaliza si el volumen está fuera del rango saludable para voz
    # Rango recomendado: 0.05 – 0.15
    if rms < 0.05 or rms > 0.15:
        score -= 30


    # 2️⃣ Clipping (saturación de la señal)
    # Detecta si la señal alcanza o supera ±1.0,
    # lo que indica recorte digital (distorsión).
    clipping = np.any(np.abs(y) >= 1.0)
    detalles["clipping"] = clipping

    # El clipping es muy dañino para jitter, shimmer y HNR,
    # por eso se penaliza fuertemente.
    if clipping:
        score -= 40

    # 3️⃣ Duración útil del audio
    # Calcula la duración total en segundos.
    # Audios muy cortos no permiten estimar bien
    # características acústicas estables.
    duration = len(y) / sr
    detalles["duracion"] = duration

    # Penaliza audios demasiado cortos (< 2 segundos)
    # porque generan medidas inestables en openSMILE.
    if duration < 2.0:
        score -= 20

    # 4️⃣ Pico robusto (percentil 95)
    # Mide la amplitud típica alta ignorando picos extremos.
    # Es más robusto que usar el máximo absoluto.
    peak95 = np.percentile(np.abs(y), 95)
    detalles["peak95"] = peak95

    # Si el pico típico supera 1.0, la señal está
    # mal escalada o muy cerca del clipping.
    if peak95 > 1.0:
        score -= 10

    # Asegurar que el score final esté entre 0 y 100
    # Evita valores negativos tras aplicar penalizaciones.
    score = max(0, score)

    # Etiqueta final
    if score >= 80:
        calidad = "Excelente"
    elif score >= 60:
        calidad = "Usable"
    else:
        calidad = "Mala"

    return score, calidad

#Normalizacion del audio A 16K
def normalizacion_audio(audio):
    data = []
    print("ENTRADA AUDIO:", audio)
 
    y, sr = librosa.load(audio, sr=16000, mono=True)
    rms = np.sqrt(np.mean(y**2))
    y = y / rms * 0.1
    score, calidad = audio_quality_score(y, sr)
    Path(dest_demential).mkdir(parents=True, exist_ok=True)
    nombre_original = Path(audio).name
    nuevo_nombre = f"N_{nombre_original}"
    path_dest = Path(dest_demential) / nuevo_nombre
    # Guardar audio normalizado
    sf.write(path_dest, y, 16000)
    print("Guardado en:", path_dest)
    data.append(score)
    data.append(calidad)
    data.append(nuevo_nombre)
    data.append(path_dest)
    
    return data

def opensmile_parameters(salida_normalizada):

    smile = opensmile.Smile(
    feature_set=opensmile.FeatureSet.eGeMAPSv02,
    feature_level=opensmile.FeatureLevel.Functionals
    )

    return smile.process_file(salida_normalizada)

#añadimos todas las variables de librosa
#añadimos todas las variables de Opensmile
#añadimos todas las variables de Whisper+Spacy
def construir_json_desde_directorio(ruta_base):
    ruta = Path(ruta_base)
    resultados = []
    # Extensiones de audio que quieres considerar
    extensiones_audio = {".wav"}
    for archivo in ruta.rglob("*"):
        if archivo.is_file() and archivo.suffix.lower() in extensiones_audio:
            print("archivo: ",archivo)
            quality=normalizacion_audio(archivo)
            # Construcción del objeto JSON
            features=opensmile_parameters(quality[3])
            data = {
                "uuid": str(uuid.uuid4()),
                "nombre": str(archivo.parent),
                "audio": quality[2],
                "score": quality[0],              
                "calidad": quality[1], 
                "parametros": {}
            }
            #print(features)
            
            vars_acusticas = {
                "F0semitoneFrom27.5Hz_sma3nz_amean": float(features['F0semitoneFrom27.5Hz_sma3nz_amean'].iloc[0]),
                "F0semitoneFrom27.5Hz_sma3nz_stddevNorm": float(features['F0semitoneFrom27.5Hz_sma3nz_stddevNorm'].iloc[0]),
                "loudness_sma3_amean": float(features['loudness_sma3_amean'].iloc[0]),
                "loudness_sma3_stddevNorm": float(features['loudness_sma3_stddevNorm'].iloc[0]),
                "jitterLocal_sma3nz_amean": float(features['jitterLocal_sma3nz_amean'].iloc[0]),
                "jitterLocal_sma3nz_stddevNorm": float(features['jitterLocal_sma3nz_stddevNorm'].iloc[0]),
                "shimmerLocaldB_sma3nz_amean": float(features['shimmerLocaldB_sma3nz_amean'].iloc[0]),
                "shimmerLocaldB_sma3nz_stddevNorm": float(features['shimmerLocaldB_sma3nz_stddevNorm'].iloc[0]),
                "HNRdBACF_sma3nz_amean": float(features['HNRdBACF_sma3nz_amean'].iloc[0]),
                "HNRdBACF_sma3nz_stddevNorm": float(features['HNRdBACF_sma3nz_stddevNorm'].iloc[0]),
                "alphaRatioV_sma3nz_amean": float(features['alphaRatioV_sma3nz_amean'].iloc[0]),
                "alphaRatioV_sma3nz_stddevNorm": float(features['alphaRatioV_sma3nz_stddevNorm'].iloc[0]),
                "hammarbergIndexV_sma3nz_amean": float(features['hammarbergIndexV_sma3nz_amean'].iloc[0]),
                "hammarbergIndexV_sma3nz_stddevNorm": float(features['hammarbergIndexV_sma3nz_stddevNorm'].iloc[0]),
                "slopeV0-500_sma3nz_amean": float(features['slopeV0-500_sma3nz_amean'].iloc[0]),
                "slopeV500-1500_sma3nz_amean": float(features['slopeV500-1500_sma3nz_amean'].iloc[0])
            }

            data["parametros"].update(vars_acusticas)
            resultados.append(data)
            # Exportar a archivo JSON con indentación bonita
            with open("demential_normalizado.json", "w", encoding="utf-8") as f:
                json.dump(resultados, f, ensure_ascii=False, indent=4)
    #return resultados


construir_json_desde_directorio(origin_demential)

