import librosa
import soundfile as sf
import opensmile
import pandas as pd
import numpy as np
from pathlib import Path
import os
import uuid
import json
import spacy
import re
from collections import Counter
import whisper
import ffmpeg
import warnings
from scipy.stats import skew, kurtosis
from datetime import datetime

# Configuración de rutas siguiendo buenas prácticas
# Como el script está en scripts/, subimos un nivel para llegar a la raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DATA_DIR = PROJECT_ROOT / "output_data"
OUTPUT_DATA_DIR.mkdir(exist_ok=True)  # Crear directorio si no existe


warnings.filterwarnings(
    "ignore",
    message="FP16 is not supported on CPU"
)

whisper_model = whisper.load_model("base")
# Usar modelo 'md' o 'lg' para tener vectores de palabras (necesario para similarity)
# Si no está instalado, intentar descargarlo o usar 'sm' como fallback
try:
    nlp = spacy.load("en_core_web_md")
    print("Modelo spaCy 'en_core_web_md' cargado correctamente")
except OSError:
    try:
        # Intentar descargar el modelo si no está instalado
        import subprocess
        import sys
        print("Intentando descargar modelo en_core_web_md...")
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_md"])
        nlp = spacy.load("en_core_web_md")
        print("Modelo spaCy 'en_core_web_md' descargado y cargado correctamente")
    except Exception as download_error:
        print(f"Advertencia: No se pudo cargar/descargar en_core_web_md: {download_error}")
        print("Usando en_core_web_sm como alternativa (similarity y lexical_errors pueden ser menos precisos)")
        nlp = spacy.load("en_core_web_sm")
        print("Modelo spaCy 'en_core_web_sm' cargado correctamente")
print("Modelos cargados correctamente")


# Directorio de origen relativo a la raíz del proyecto
directorio_origen = PROJECT_ROOT / 'TAILBANK'

# python -m spacy download en_core_web_sm


def keyword_repetitions(doc):
    """
    Calcula la proporción de repeticiones de palabras clave en un texto.
    Se consideran palabras de contenido (sustantivos, verbos y adjetivos),
    excluyendo stopwords y signos no alfabéticos.
    """

    # Extrae lemas normalizados (minúsculas) de palabras relevantes:
    # - Solo tokens alfabéticos
    # - Excluye stopwords
    # - Incluye solo sustantivos, verbos y adjetivos
    words = [
        t.lemma_.lower()
        for t in doc
        if t.is_alpha and not t.is_stop and t.pos_ in {"NOUN", "VERB", "ADJ"}
    ]

    # Si no hay palabras válidas, devuelve 0 para evitar divisiones por cero
    if not words:
        return 0.0

    # Cuenta cuántas veces aparece cada palabra
    counts = Counter(words)

    # Calcula el número total de repeticiones:
    # para cada palabra que aparece más de una vez,
    # suma las repeticiones adicionales (c - 1)
    repeated = sum(c - 1 for c in counts.values() if c > 1)

    # Devuelve la proporción de repeticiones respecto al total de palabras
    return repeated / len(words)



def identificar_genero_pitch(audio_path):
    """
    Estima el género del hablante a partir del pitch medio de la voz.
    La clasificación se basa en un umbral simple de frecuencia fundamental.
    """

    # Carga el audio (frecuencia de muestreo por defecto, señal mono)
    y, sr = librosa.load(audio_path)

    # Calcula el pitch (frecuencia fundamental estimada) y su magnitud
    # pitches: matriz de frecuencias
    # magnitudes: energía asociada a cada pitch
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)

    # Selecciona solo los valores de pitch con magnitud significativa
    # (por encima de la mediana) para reducir ruido
    pitch_values = pitches[magnitudes > np.median(magnitudes)]

    # Calcula el pitch medio del hablante
    pitch_mean = np.mean(pitch_values)

    # Clasificación simple basada en umbral:
    # voces graves -> "male", voces agudas -> "female"
    if pitch_mean < 165:
        return "male"
    else:
        return "female"


def normalizar_nombre_audio(nombre_archivo):
    """
    Normaliza el nombre de un archivo de audio para obtener
    un identificador limpio y consistente del hablante.
    """

    # Obtiene el nombre del archivo sin la extensión
    nombre = nombre_archivo.stem  

    # Elimina el prefijo 'N_' usado para indicar audio normalizado
    nombre = re.sub(r"^N_", "", nombre)     

    # Elimina sufijos numéricos finales (ej. _1, _23)
    nombre = re.sub(r"_\d+$", "", nombre)  

    # Inserta un espacio entre letras minúsculas y mayúsculas consecutivas
    # Ejemplo: "johnDoe" -> "john Doe"
    nombre = re.sub(r"([a-z])([A-Z])", r"\1 \2", nombre)

    # Convierte todo a minúsculas y elimina espacios sobrantes
    return nombre.lower().strip()


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


def normalizacion_audio(audio_path, directorio_origen, directorio_destino):
    """
    Carga un archivo de audio, lo normaliza en energía (RMS),
    evalúa su calidad y lo guarda manteniendo la estructura
    original de directorios.
    """

    # Convierte las rutas a objetos Path para facilitar el manejo de archivos
    audio_path = Path(audio_path)
    directorio_origen = Path(directorio_origen)
    directorio_destino = Path(directorio_destino)

    # =========================
    # MANTENER ESTRUCTURA DE CARPETAS
    # =========================
    # Obtiene la ruta relativa del audio respecto al directorio origen
    rel_path = audio_path.parent.relative_to(directorio_origen)

    # Construye la carpeta destino respetando la estructura original
    carpeta_destino = directorio_destino / rel_path

    # Crea las carpetas necesarias si no existen
    carpeta_destino.mkdir(parents=True, exist_ok=True)

    # =========================
    # CARGA DEL AUDIO
    # =========================
    # Carga el audio:
    # - frecuencia de muestreo fija a 16 kHz
    # - señal mono
    y, sr = librosa.load(audio_path, sr=16000, mono=True)

    # =========================
    # NORMALIZACIÓN RMS
    # =========================
    # Calcula la energía RMS de la señal
    rms = np.sqrt(np.mean(y**2))

    # Normaliza la señal para que tenga una RMS objetivo (~0.1)
    # Evita división por cero en audios silenciosos
    if rms > 0:
        y = y / rms * 0.1

    # =========================
    # EVALUACIÓN DE CALIDAD
    # =========================
    # Calcula un score de calidad del audio y una etiqueta cualitativa
    score, calidad = audio_quality_score(y, sr)

    # =========================
    # NOMBRE Y RUTA DE SALIDA
    # =========================
    # Prefijo "N_" para indicar que el audio fue normalizado
    nuevo_nombre = f"N_{audio_path.name}"

    # Ruta final del archivo normalizado
    path_dest = carpeta_destino / nuevo_nombre

    # =========================
    # GUARDADO DEL AUDIO
    # =========================
    # Guarda el audio normalizado en disco
    sf.write(path_dest, y, sr)

    # =========================
    # SALIDA
    # =========================
    # Devuelve información relevante para el pipeline posterior
    return {
        "score": score,                      # Score numérico de calidad
        "calidad": calidad,                  # Etiqueta de calidad (ej. buena/mala)
        "audio_normalizado": path_dest,      # Ruta al audio normalizado
        "nombre_audio": nuevo_nombre         # Nombre del archivo generado
    }



def opensmile_parameters(salida_normalizada):
    """
    Extrae características acústicas del audio utilizando OpenSMILE
    con el conjunto eGeMAPSv02 a nivel de funcionales.
    """

    # Inicializa el objeto Smile de OpenSMILE
    # eGeMAPSv02 es un conjunto compacto y optimizado de features,
    # diseñado para tareas de análisis paralingüístico y clínico
    # 88 caracteristicas
    smile = opensmile.Smile(
        feature_set=opensmile.FeatureSet.eGeMAPSv02,      # Set de features eGeMAPS v02
        feature_level=opensmile.FeatureLevel.Functionals  # Estadísticos globales del audio
    )

    # Procesa el archivo de audio normalizado y devuelve
    # un DataFrame con las características acústicas extraídas
    return smile.process_file(salida_normalizada)



def opensmile_parameters_Compare_2016(salida_normalizada):
    """
    Extrae características acústicas del audio utilizando OpenSMILE
    con el conjunto de features ComParE 2016 a nivel de funcionales.
    """

    # Inicializa el objeto Smile de OpenSMILE
    # ComParE_2016 es un conjunto estándar de características
    # muy utilizado en tareas paralingüísticas (emoción, patología del habla, etc.)
    smile = opensmile.Smile(
        feature_set=opensmile.FeatureSet.ComParE_2016,   # Set de features ComParE 2016
        feature_level=opensmile.FeatureLevel.Functionals # Estadísticos globales del audio
    )

    # Procesa el archivo de audio normalizado y devuelve
    # un DataFrame con todas las características extraídas
    return smile.process_file(salida_normalizada)



def extract_whisper_spacy_features(audio_path):
    """
    Transcribe un archivo de audio con Whisper y extrae características
    lingüísticas y cognitivas usando spaCy.
    """

    # Diccionario donde se almacenarán todas las features extraídas
    features = {}


    # =========================
    # FFMPEG ya debe estar en el PATH del sistema
    # Si no está instalado, ejecutar: winget install --id=Gyan.FFmpeg -e
    # =========================
    
    # =========================
    # RUTA DE AUDIO
    # =========================
    # Convierte la ruta a objeto Path
    audio_path = Path(audio_path)

    # Verifica que el archivo de audio exista
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio no encontrado: {audio_path}")

    # =========================
    # WHISPER: TRANSCRIPCIÓN
    # =========================
    # Transcribe el audio usando Whisper en inglés
    result = whisper_model.transcribe(str(audio_path), language="en")

    # Texto transcrito limpio de espacios iniciales/finales
    text = result["text"].strip()

    # Limpieza básica del texto: elimina espacios múltiples
    text_clean = re.sub(r"\s+", " ", text)
    
    # Guardar texto limpio para uso en características avanzadas (no se guarda en JSON final)
    # Se usa internamente para calcular Local_coherence, Filler_frequency, etc.
    features["_transcription_internal"] = text_clean  # Prefijo _ indica uso interno
    
    # ⚠️ OPCIONAL: Guardar la transcripción completa en JSON (solo necesario para debugging)
    # features["transcription"] = text_clean

    # =========================
    # MÉTRICAS BÁSICAS DE TEXTO
    # =========================
    # Número total de caracteres
    features["n_chars"] = len(text_clean)

    # Procesa el texto con spaCy
    doc = nlp(text_clean)

    # Tokens sin signos de puntuación ni espacios
    tokens = [t for t in doc if not t.is_punct and not t.is_space]

    # Palabras alfabéticas (excluye números y símbolos)
    words = [t for t in tokens if t.is_alpha]

    # Número de tokens, palabras y frases
    features["n_tokens"] = len(tokens)
    features["n_words"] = len(words)
    features["n_sents"] = len(list(doc.sents))

    # Media de palabras por frase
    features["mean_words_per_sent"] = (
        features["n_words"] / features["n_sents"]
        if features["n_sents"] > 0 else 0.0
    )

    # =========================
    # DIVERSIDAD LÉXICA
    # =========================
    # Formas léxicas normalizadas (minúsculas)
    word_forms = [t.text.lower() for t in words]

    # Conjunto de palabras únicas
    unique_words = set(word_forms)

    # Type-Token Ratio (TTR)
    features["ttr"] = (
        len(unique_words) / len(word_forms)
        if len(word_forms) > 0 else 0.0
    )

    # MATTR (Moving-Average TTR) con ventana de 50 palabras
    window = 50
    if len(word_forms) >= window:
        ttrs = []
        for i in range(len(word_forms) - window + 1):
            w = word_forms[i:i + window]
            ttrs.append(len(set(w)) / window)
        features["mattr_50"] = float(np.mean(ttrs))
    else:
        # Si el texto es corto, se usa el TTR estándar
        features["mattr_50"] = features["ttr"]

    # =========================
    # VARIABLES COGNITIVAS
    # =========================
    # Número de repeticiones de palabras clave (indicador de posible deterioro)
    features["keyword_repetitions"] = keyword_repetitions(doc)

    # =========================
    # POS TAGGING
    # =========================
    # Conteo de categorías gramaticales (POS)
    pos_counts = Counter(t.pos_ for t in words)
    total_words = len(words)

    # Función auxiliar para calcular ratios POS
    def ratio(pos):
        return pos_counts.get(pos, 0) / total_words if total_words > 0 else 0.0

    # Ratios de categorías gramaticales principales
    features["noun_ratio"] = ratio("NOUN")
    features["verb_ratio"] = ratio("VERB")
    features["adj_ratio"] = ratio("ADJ")
    features["adv_ratio"] = ratio("ADV")
    # ⚠️ OPCIONAL: Ratios de pronombres y nombres propios (menos relevantes para demencia)
    # features["pron_ratio"] = ratio("PRON")
    # features["propn_ratio"] = ratio("PROPN")

    # Palabras de contenido: sustantivos, verbos, adjetivos y adverbios
    content_words = sum(
        pos_counts.get(p, 0) for p in ["NOUN", "VERB", "ADJ", "ADV"]
    )

    # Ratio de palabras de contenido sobre el total
    features["content_ratio"] = (
        content_words / total_words if total_words > 0 else 0.0
    )

    # ⚠️ OPCIONAL: Ratio sustantivos / pronombres (menos esencial)
    # Valores altos pueden indicar discurso más informativo
    # features["noun_pron_ratio"] = (
    #     pos_counts.get("NOUN", 0) / pos_counts.get("PRON", 1)
    #     if pos_counts.get("PRON", 0) > 0 else float("inf")
    # )

    # Devuelve el diccionario con todas las features extraídas
    return features


def extract_all_librosa_features(audio_path):
    """
    Extrae características acústicas avanzadas usando librosa.
    Incluye MFCCs, características espectrales, tempo, y parámetros de pitch.
    """
    
    # Diccionario donde se almacenarán todas las features
    features = {}
    
    # Carga el audio con la frecuencia de muestreo nativa
    y, sr = librosa.load(audio_path, sr=None)
    
    # =========================
    # 1. MFCCs (Mel-Frequency Cepstral Coefficients)
    # =========================
    # Extrae 13 coeficientes MFCC (estándar para voz)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    
    # Estadísticas de cada coeficiente MFCC
    for i in range(mfccs.shape[0]):
        features[f"mfcc_{i+1}_mean"] = float(np.mean(mfccs[i]))
        # ⚠️ OPCIONAL: Estadísticas detalladas de MFCCs (descomentar si necesitas más detalle)
        # features[f"mfcc_{i+1}_std"] = float(np.std(mfccs[i]))
        # features[f"mfcc_{i+1}_min"] = float(np.min(mfccs[i]))
        # features[f"mfcc_{i+1}_max"] = float(np.max(mfccs[i]))
    
    # =========================
    # 2. CHROMA FEATURES
    # =========================
    # Representa la energía de las 12 clases de pitch (C, C#, D, ...)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    features["chroma_mean"] = float(np.mean(chroma))
    # ⚠️ OPCIONAL: Desviación estándar de chroma
    # features["chroma_std"] = float(np.std(chroma))
    
    # =========================
    # 3. SPECTRAL FEATURES
    # =========================
    # Spectral Centroid: "centro de masa" del espectro (brillo del sonido)
    spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    features["spectral_centroid_mean"] = float(np.mean(spectral_centroids))
    # ⚠️ OPCIONAL: Desviación estándar de spectral centroid
    # features["spectral_centroid_std"] = float(np.std(spectral_centroids))
    
    # Spectral Rolloff: frecuencia por debajo de la cual está el 85% de la energía
    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    features["spectral_rolloff_mean"] = float(np.mean(spectral_rolloff))
    # ⚠️ OPCIONAL: Desviación estándar de spectral rolloff
    # features["spectral_rolloff_std"] = float(np.std(spectral_rolloff))
    
    # Spectral Bandwidth: ancho de banda del espectro
    spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    features["spectral_bandwidth_mean"] = float(np.mean(spectral_bandwidth))
    # ⚠️ OPCIONAL: Desviación estándar de spectral bandwidth
    # features["spectral_bandwidth_std"] = float(np.std(spectral_bandwidth))
    
    # ⚠️ OPCIONAL: Spectral Contrast y Flatness (características menos esenciales)
    # Spectral Contrast: diferencia de energía entre picos y valles espectrales
    # spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    # features["spectral_contrast_mean"] = float(np.mean(spectral_contrast))
    # features["spectral_contrast_std"] = float(np.std(spectral_contrast))
    
    # Spectral Flatness: medida de qué tan "plano" es el espectro (ruido vs tonal)
    # spectral_flatness = librosa.feature.spectral_flatness(y=y)[0]
    # features["spectral_flatness_mean"] = float(np.mean(spectral_flatness))
    # features["spectral_flatness_std"] = float(np.std(spectral_flatness))
    
    # =========================
    # 4. ZERO-CROSSING RATE
    # =========================
    # Tasa de cruces por cero (indicador de fricción/ruido)
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    features["zcr_mean"] = float(np.mean(zcr))
    # ⚠️ OPCIONAL: Desviación estándar de ZCR
    # features["zcr_std"] = float(np.std(zcr))
    
    # =========================
    # 5. TEMPO Y BEATS
    # =========================
    # Estima el tempo (BPM) del audio
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    features["tempo"] = float(tempo)
    
    # =========================
    # 6. PITCH Y MAGNITUD (F0)
    # =========================
    # Extrae pitch (frecuencia fundamental) y su magnitud
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    
    # Selecciona los valores de pitch con magnitud significativa
    pitch_values = pitches[magnitudes > np.median(magnitudes)]
    pitch_values = pitch_values[pitch_values > 0]  # Solo valores positivos
    
    if len(pitch_values) > 0:
        features["pitch_mean"] = float(np.mean(pitch_values))
        features["pitch_std"] = float(np.std(pitch_values))
        # ⚠️ OPCIONAL: Estadísticas detalladas de pitch (descomentar si necesitas más detalle)
        # features["pitch_min"] = float(np.min(pitch_values))
        # features["pitch_max"] = float(np.max(pitch_values))
        # features["pitch_median"] = float(np.median(pitch_values))
        # features["pitch_skew"] = float(skew(pitch_values))
        
        # JITTER: variabilidad del pitch (indicador de estabilidad vocal)
        # Calculado como la desviación estándar relativa
        features["jitter"] = float(np.std(pitch_values) / np.mean(pitch_values))
    else:
        features["pitch_mean"] = 0.0
        features["pitch_std"] = 0.0
        # ⚠️ OPCIONAL: Valores por defecto para características detalladas
        # features["pitch_min"] = 0.0
        # features["pitch_max"] = 0.0
        # features["pitch_median"] = 0.0
        # features["pitch_skew"] = 0.0
        features["jitter"] = 0.0
    
    # =========================
    # 7. SHIMMER (variabilidad de amplitud)
    # =========================
    # Extrae la envolvente de amplitud usando RMS
    rms = librosa.feature.rms(y=y)[0]
    
    if len(rms) > 0 and np.mean(rms) > 0:
        # Shimmer: variabilidad de la amplitud
        features["shimmer"] = float(np.std(rms) / np.mean(rms))
        features["rms_mean"] = float(np.mean(rms))
        features["rms_std"] = float(np.std(rms))
    else:
        features["shimmer"] = 0.0
        features["rms_mean"] = 0.0
        features["rms_std"] = 0.0
    
    # =========================
    # 8. HNR (Harmonic-to-Noise Ratio)
    # =========================
    # Una aproximación usando la separación armónica/percusiva
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    
    # Energía de componentes armónicas vs percusivas (ruido)
    harmonic_energy = np.sum(y_harmonic**2)
    percussive_energy = np.sum(y_percussive**2)
    
    if percussive_energy > 0:
        # HNR en escala lineal
        hnr = harmonic_energy / percussive_energy
        # Convertir a escala logarítmica (dB)
        features["hnr_db"] = float(10 * np.log10(hnr + 1e-10))
    else:
        features["hnr_db"] = 0.0
    
    # =========================
    # 9. DURACIÓN Y ENERGÍA TOTAL
    # =========================
    features["duration"] = float(len(y) / sr)
    # ⚠️ OPCIONAL: Energía total del audio (puede ser redundante con rms_mean)
    # features["energy"] = float(np.sum(y**2))
    
    return features

# --- NUEVAS FUNCIONES PARA PAUSAS Y TEXTO AVANZADO ---

def get_pause_features(audio_path, sr=None):
    """
    Calcula la distribución estadística (Skewness y Kurtosis) de las pausas de silencio.
    
    Estas métricas son importantes para detectar patrones de habla relacionados con demencia:
    - Skewness (asimetría): Indica si hay pausas inusualmente largas (valores positivos altos)
    - Kurtosis (apuntamiento): Mide la concentración de pausas alrededor de la media
    
    Args:
        audio_path: Ruta al archivo de audio
        sr: Frecuencia de muestreo (opcional, se detecta automáticamente si es None)
    
    Returns:
        Diccionario con Skewness_pause_duration y Kurtosis_pause_duration
    """
    try:
        y, sr = librosa.load(audio_path, sr=sr)
        
        # Detectar intervalos de NO-silencio (segmentos con habla)
        # top_db=25 es un umbral razonable para separar habla de silencio
        non_silent_intervals = librosa.effects.split(y, top_db=25)
        
        pause_durations = []
        
        # Calcular las duraciones de los silencios (pausas) entre intervalos de habla
        if len(non_silent_intervals) > 0:
            for i in range(len(non_silent_intervals) - 1):
                end_current = non_silent_intervals[i][1]
                start_next = non_silent_intervals[i+1][0]
                duration = (start_next - end_current) / sr
                
                # Ignorar micro-pausas menores a 50ms (ruido de fondo, no pausas reales)
                if duration > 0.05:
                    pause_durations.append(duration)
        
        # Necesitamos al menos 2 pausas para calcular skewness y kurtosis
        if len(pause_durations) > 1:
            return {
                "Skewness_pause_duration": float(skew(pause_durations)),
                "Kurtosis_pause_duration": float(kurtosis(pause_durations))
            }
        else:
            # Si hay muy pocas pausas, devolver valores neutros
            return {"Skewness_pause_duration": 0.0, "Kurtosis_pause_duration": 0.0}
    except Exception as e:
        print(f"Error calculando características de pausas para {audio_path}: {e}")
        return {"Skewness_pause_duration": 0.0, "Kurtosis_pause_duration": 0.0}

def detect_lexical_errors(doc, nlp_model):
    """
    Detecta errores léxicos en el texto transcrito.
    
    Los errores léxicos pueden incluir:
    - Palabras mal escritas (no reconocidas por el modelo de spaCy)
    - Palabras con patrones sospechosos (muchas consonantes seguidas, etc.)
    - Palabras que no están en el vocabulario del modelo
    
    Args:
        doc: Documento procesado por spaCy
        nlp_model: Modelo de spaCy cargado
    
    Returns:
        Número de errores léxicos detectados y frecuencia como porcentaje
    """
    try:
        error_count = 0
        total_words = 0
        
        # Lista de palabras comunes en inglés (para validación básica)
        # En un caso real, usarías un diccionario completo o biblioteca de spell-check
        common_words = {
            "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
            "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
            "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
            "or", "an", "will", "my", "one", "all", "would", "there", "their"
        }
        
        for token in doc:
            # Solo considerar palabras alfabéticas (excluir números y puntuación)
            if token.is_alpha and not token.is_stop:
                total_words += 1
                word_lower = token.text.lower()
                
                # Verificar si la palabra está en el vocabulario del modelo
                is_in_vocab = word_lower in nlp_model.vocab.strings
                
                # Verificar patrones sospechosos de errores ortográficos
                # 1. Palabras con muchas consonantes seguidas (ej: "thrgh" en lugar de "through")
                consonant_pattern = re.search(r'[bcdfghjklmnpqrstvwxyz]{4,}', word_lower)
                
                # 2. Palabras con muchas vocales seguidas (ej: "aeiou")
                vowel_pattern = re.search(r'[aeiou]{4,}', word_lower)
                
                # 3. Palabras muy cortas que no son comunes (posible error de transcripción)
                is_uncommon_short = len(word_lower) <= 2 and word_lower not in common_words
                
                # 4. Palabras que no están en el vocabulario Y no son nombres propios
                # (spaCy puede no tener todas las palabras, pero nombres propios son válidos)
                if not is_in_vocab and token.pos_ != "PROPN":
                    # Verificar si parece un error (patrones sospechosos)
                    if consonant_pattern or vowel_pattern or is_uncommon_short:
                        error_count += 1
                    # Si es una palabra de longitud razonable pero no está en vocabulario,
                    # podría ser un error de transcripción (Whisper puede cometer errores)
                    elif len(word_lower) > 3 and word_lower not in common_words:
                        # Contar como posible error si tiene características sospechosas
                        # (esto es una heurística, no perfecta)
                        if re.search(r'[^aeiou]{3,}', word_lower):  # 3+ consonantes seguidas
                            error_count += 0.5  # Error parcial
        
        # Calcular frecuencia de errores como porcentaje
        error_frequency = (error_count / total_words * 100) if total_words > 0 else 0.0
        
        return float(error_frequency)
    except Exception as e:
        print(f"Error detectando errores léxicos: {e}")
        return 0.0


def get_advanced_text_features(transcription_text, nlp_model):
    """
    Calcula muletillas (fillers), coherencia semántica local y errores léxicos.
    
    Args:
        transcription_text: Texto transcrito del audio
        nlp_model: Modelo de spaCy cargado (preferiblemente 'md' o 'lg' para vectores)
    
    Returns:
        Diccionario con Filler_frequency, Local_coherence y Lexical_errors
    """
    try:
        doc = nlp_model(transcription_text)
        
        # 1. Fillers (Muletillas en inglés)
        # Lista común de muletillas que indican pausas o dudas en el habla
        fillers = {"um", "uh", "ah", "hmm", "er", "like", "mean", "well", "you know"}
        filler_count = sum(1 for token in doc if token.text.lower() in fillers)
        # Frecuencia como porcentaje de tokens totales
        filler_freq = (filler_count / len(doc)) * 100 if len(doc) > 0 else 0.0
        
        # 2. Coherencia Local (Similitud semántica entre frases adyacentes)
        # Mide qué tan relacionadas están las frases consecutivas
        sentences = list(doc.sents)
        similarities = []
        
        if len(sentences) > 1:
            for i in range(len(sentences) - 1):
                try:
                    # Requiere modelo _md o _lg para vectores reales
                    # Con _sm puede dar advertencia y valores menos precisos
                    sim = sentences[i].similarity(sentences[i+1])
                    similarities.append(sim)
                except Exception as sim_error:
                    # Si similarity falla (modelo sin vectores), usar valor neutro
                    similarities.append(0.5)
            
            if similarities:
                local_coherence = np.mean(similarities)
            else:
                local_coherence = 0.5  # Valor neutro si no se pudo calcular
        else:
            # Si solo hay una frase, no hay coherencia local que medir
            local_coherence = 1.0  # Valor base para textos muy cortos
        
        # 3. Errores Léxicos (Lexical Errors)
        # Detecta palabras mal escritas o con patrones sospechosos
        lexical_errors = detect_lexical_errors(doc, nlp_model)
            
        return {
            "Filler_frequency": float(filler_freq),
            "Local_coherence": float(local_coherence),
            "Lexical_errors": float(lexical_errors)
        }
    except Exception as e:
        print(f"Error calculando características avanzadas de texto: {e}")
        return {"Filler_frequency": 0.0, "Local_coherence": 0.0, "Lexical_errors": 0.0}

def construir_json_desde_directorio(ruta_base):
    """
    Recorre un directorio de forma recursiva, procesa archivos de audio (.wav),
    extrae características acústicas y lingüísticas, y genera un archivo JSON
    con toda la información.
    
    Args:
        ruta_base: Ruta al directorio base con los audios (Path o str)
    """

    # Directorio donde se guardarán los audios normalizados (relativo a la raíz del proyecto)
    directorio_destino = PROJECT_ROOT / 'dementibank_normalizado'

    # Convierte la ruta base en un objeto Path para manejo de archivos
    ruta = Path(ruta_base) if not isinstance(ruta_base, Path) else ruta_base

    # Lista donde se almacenará la información final de cada audio
    resultados = []

    # Extensiones de audio permitidas
    extensiones_audio = {".wav"}

    # Recorre todos los archivos y subdirectorios de forma recursiva
    for archivo in ruta.rglob("*"):

        # Filtra solo archivos .wav
        if archivo.is_file() and archivo.suffix.lower() in extensiones_audio:
            print("archivo:", archivo)

            # Normaliza el audio y calcula métricas de calidad
            quality = normalizacion_audio(
                archivo,
                directorio_origen,
                directorio_destino
            )

            # Extrae parámetros acústicos usando OpenSMILE (eGeMAPSv02 - 88 características esenciales)
            features = opensmile_parameters(quality["audio_normalizado"])

            # ⚠️ OPCIONAL: Extrae parámetros del set Compare 2016 de OpenSMILE (6373 características)
            # Comentado por defecto porque es demasiado grande y puede causar overfitting
            # Descomentar solo si necesitas análisis muy detallado
            # features2 = opensmile_parameters_Compare_2016(
            #     quality["audio_normalizado"]
            # )

            # Obtiene el nombre del archivo sin extensión
            nombre_audio = archivo.stem.strip()
            
            # Detectar si el audio es de paciente con demencia o sin demencia
            # basándose en la estructura de carpetas
            ruta_str = str(archivo).lower()
            if "dementia" in ruta_str and "nodementia" not in ruta_str:
                etiqueta_dementia = "dementia"
            elif "nodementia" in ruta_str:
                etiqueta_dementia = "nodementia"
            else:
                etiqueta_dementia = ""

            # Diccionario principal con metadatos y estructuras vacías
            data = {
                # Identificador único del registro
                "uuid": str(uuid.uuid4()),

                # Nombre del audio normalizado
                "audio": quality["nombre_audio"],

                # Nombre del hablante normalizado
                "name": normalizar_nombre_audio(Path(nombre_audio)),

                # Etiqueta de demencia (detectada automáticamente)
                "dementia": etiqueta_dementia,


                # Género estimado a partir del pitch
                "gender": identificar_genero_pitch(archivo),

                # Etnicidad (placeholder)
                "ethnicity": "",

                # Score global de calidad del audio
                "score": quality["score"],

                # Métrica de calidad del audio
                "calidad": quality["calidad"],

                # Diccionarios para almacenar los distintos parámetros
                "parametros_librosa": {},
                "parametros_opensmile": {},
                # ⚠️ OPCIONAL: ComParE 2016 (comentado por defecto - demasiadas características)
                # "parametros_opensmile_compare": {},
                "parametros_whisperSpacy": {}
            }

            # Convierte y guarda los parámetros OpenSMILE en formato JSON-serializable
            data["parametros_opensmile"].update({
                k: float(v.iloc[0]) if hasattr(v, "iloc") else float(v)
                for k, v in features.items()
            })

            # ⚠️ OPCIONAL: Convierte y guarda los parámetros OpenSMILE Compare 2016
            # Descomentar si activaste features2 arriba
            # data["parametros_opensmile_compare"].update({
            #     k: float(v.iloc[0]) if hasattr(v, "iloc") else float(v)
            #     for k, v in features2.items()
            # })

            # Extrae y guarda características acústicas con librosa
            librosa_feats = extract_all_librosa_features(quality["audio_normalizado"])
            data["parametros_librosa"].update(librosa_feats)
            
            # --- NUEVO: CALCULAR PAUSAS AVANZADAS (Skewness y Kurtosis) ---
            pause_feats = get_pause_features(quality["audio_normalizado"])
            data["parametros_librosa"].update(pause_feats)

            # Extrae características lingüísticas con Whisper + spaCy
            whisper_feats = extract_whisper_spacy_features(quality["audio_normalizado"])
            
            # --- NUEVO: CALCULAR COHERENCIA LOCAL Y FILLERS ---
            # Recuperamos el texto transcrito (guardado internamente en whisper_feats)
            texto_transcrito = whisper_feats.get("_transcription_internal", "")
            
            if texto_transcrito:
                # Calcular características avanzadas de texto (fillers, coherencia y errores léxicos)
                advanced_text = get_advanced_text_features(texto_transcrito, nlp)
                whisper_feats.update(advanced_text)
            
            # Eliminar la transcripción interna antes de guardar (no debe ir al JSON)
            whisper_feats.pop("_transcription_internal", None)
            
            data["parametros_whisperSpacy"].update(whisper_feats)

            # Añade el registro completo a la lista final
            resultados.append(data)

    # Guarda todos los resultados en un archivo JSON en output_data/
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_filename = f"ADReSSo21_{timestamp}.json"
    json_path = OUTPUT_DATA_DIR / json_filename
    
    print(f"\n💾 Guardando resultados en: {json_path}")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=4)
    
    # También guardar una copia con nombre fijo (última versión)
    json_latest_path = OUTPUT_DATA_DIR / "ADReSSo21_latest.json"
    with open(json_latest_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=4)
    
    print(f"✅ JSON guardado:")
    print(f"   - Versión con timestamp: {json_filename}")
    print(f"   - Última versión: ADReSSo21_latest.json")
    print(f"   - Total de registros: {len(resultados)}")


# Llamada a la función usando el directorio de origen
construir_json_desde_directorio(directorio_origen)
