"""
Silver — Procesa audios de S3 Bronze y guarda features en S3 Silver
====================================================================

Este script se ejecuta DENTRO del SageMaker Notebook:
  1. Descarga audios de S3 Bronze
  2. Extrae features con Librosa, OpenSMILE, Whisper y spaCy
  3. Sube JSON con features a S3 Silver

Uso (dentro del Notebook):
    conda_pytorch_p310

  Celda 1: %pip install librosa opensmile openai-whisper spacy soundfile scipy tqdm
  Celda 2: import sys
    !conda install --yes --prefix {sys.prefix} -c conda-forge librosa openai-whisper tiktoken
  Celda 3: !python -m spacy download en_core_web_md
  cELDA 4: %pip install -U spacy
        !python -m spacy download en_core_web_md --force
  Celda 5: %run process_silver.py
"""

import boto3
import json
import os
import uuid
import warnings
import tempfile
from pathlib import Path
from collections import Counter

import librosa
import soundfile as sf
import opensmile
import numpy as np
import pandas as pd
import spacy
import whisper
from scipy.stats import skew, kurtosis
from tqdm import tqdm

warnings.filterwarnings('ignore')

# --- Configuración ---
BRONZE_BUCKET = 'tfm-dementia-bronze'
SILVER_BUCKET = 'tfm-dementia-silver'
SILVER_KEY = 'features/ADReSSo21_features.json'

# --- Cargar modelos ---
print("📦 Cargando modelos...")
import en_core_web_md
nlp = en_core_web_md.load()
whisper_model = whisper.load_model("base")
smile = opensmile.Smile(
    feature_set=opensmile.FeatureSet.eGeMAPSv02,
    feature_level=opensmile.FeatureLevel.Functionals
)
print("✅ Modelos cargados")


def normalizar_nombre_audio(nombre):
    """Normaliza el nombre para obtener identificador del hablante."""
    import re
    nombre = re.sub(r"^N_", "", nombre)     
    nombre = re.sub(r"_\d+$", "", nombre)  
    nombre = re.sub(r"([a-z])([A-Z])", r"\1 \2", nombre)
    return nombre.lower().strip()


def identificar_genero_pitch(audio_path):
    """Estima género basado en el pitch medio (< 165Hz = male)."""
    y, sr = librosa.load(audio_path)
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_values = pitches[magnitudes > np.median(magnitudes)]
    if len(pitch_values) > 0:
        pitch_mean = np.mean(pitch_values)
        return "male" if pitch_mean < 165 else "female"
    return "unknown"


def audio_quality_score(y, sr):
    score = 100
    detalles = {}

    rms = np.sqrt(np.mean(y**2))
    detalles["rms"] = rms
    if rms < 0.05 or rms > 0.15:
        score -= 30

    clipping = np.any(np.abs(y) >= 1.0)
    detalles["clipping"] = clipping
    if clipping:
        score -= 40

    duration = len(y) / sr
    detalles["duracion"] = duration
    if duration < 2.0:
        score -= 20

    peak95 = np.percentile(np.abs(y), 95)
    detalles["peak95"] = peak95
    if peak95 > 1.0:
        score -= 10

    score = max(0, score)

    if score >= 80:
        calidad = "Excelente"
    elif score >= 60:
        calidad = "Usable"
    else:
        calidad = "Mala"

    return score, calidad


def descargar_audios_bronze(tmp_dir):
    """Descarga todos los .wav de S3 Bronze a una carpeta local."""
    s3 = boto3.client('s3')
    response = s3.list_objects_v2(Bucket=BRONZE_BUCKET)
    
    archivos = []
    for obj in response.get('Contents', []):
        key = obj['Key']
        # Solo descargar los archivos ya procesados por la Lambda en norm/
        if key.startswith('norm/') and key.endswith('.wav'):
            local_path = Path(tmp_dir) / key
            local_path.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(BRONZE_BUCKET, key, str(local_path))
            
            # Determinar categoría desde la ruta
            categoria = 'dementia' if 'dementia' in key else 'nodementia'
            archivos.append({
                'path': str(local_path),
                'key': key,
                'categoria': categoria
            })
            print(f"  📥 {key}")
    
    print(f"✅ {len(archivos)} audios descargados")
    return archivos


def extract_librosa_features(audio_path):
    """Extrae features acústicas con Librosa."""
    y, sr = librosa.load(audio_path, sr=None)
    
    features = {}
    
    # MFCCs (13 coeficientes)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    for i in range(13):
        features[f'mfcc_{i+1}_mean'] = float(np.mean(mfccs[i]))
        features[f'mfcc_{i+1}_std'] = float(np.std(mfccs[i]))
    
    # Spectral
    features['spectral_centroid_mean'] = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    features['spectral_rolloff_mean'] = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)))
    features['spectral_bandwidth_mean'] = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)))
    features['zcr_mean'] = float(np.mean(librosa.feature.zero_crossing_rate(y)))
    
    # Pitch
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_values = pitches[magnitudes > np.median(magnitudes)]
    pitch_values = pitch_values[pitch_values > 0]
    if len(pitch_values) > 0:
        features['pitch_mean'] = float(np.mean(pitch_values))
        features['pitch_std'] = float(np.std(pitch_values))
    else:
        features['pitch_mean'] = 0.0
        features['pitch_std'] = 0.0
    
    # Jitter y Shimmer
    if len(pitch_values) > 1:
        pitch_diffs = np.diff(pitch_values)
        features['jitter'] = float(np.mean(np.abs(pitch_diffs)) / np.mean(pitch_values))
    else:
        features['jitter'] = 0.0
    
    rms = librosa.feature.rms(y=y)[0]
    if len(rms) > 1:
        rms_diffs = np.diff(rms)
        features['shimmer'] = float(np.mean(np.abs(rms_diffs)) / (np.mean(rms) + 1e-10))
    else:
        features['shimmer'] = 0.0
    
    # Energía y duración
    features['rms_mean'] = float(np.mean(rms))
    features['duration'] = float(len(y) / sr)
    
    # HNR
    harmonic = librosa.effects.harmonic(y)
    noise = y - harmonic
    hnr = np.mean(harmonic**2) / (np.mean(noise**2) + 1e-10)
    features['hnr_db'] = float(10 * np.log10(hnr + 1e-10))
    
    # Tempo
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    features['tempo'] = float(tempo) if np.isscalar(tempo) else float(tempo[0])
    
    return features


def extract_opensmile_features(audio_path):
    """Extrae features con OpenSMILE (eGeMAPSv02)."""
    try:
        result = smile.process_file(audio_path)
        return {col: float(result[col].values[0]) for col in result.columns}
    except Exception as e:
        print(f"  ⚠️ OpenSMILE error: {e}")
        return {}


def keyword_repetitions(doc):
    """Calcula la proporción de repeticiones de palabras clave."""
    words = [
        t.lemma_.lower()
        for t in doc
        if t.is_alpha and not t.is_stop and t.pos_ in {"NOUN", "VERB", "ADJ"}
    ]
    if not words: return 0.0
    counts = Counter(words)
    repeated = sum(c - 1 for c in counts.values() if c > 1)
    return repeated / len(words)


def detect_lexical_errors(doc, nlp_model):
    """Detecta errores léxicos en el texto."""
    import re
    error_count = 0
    total_words = 0
    common_words = {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
        "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
        "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
        "or", "an", "will", "my", "one", "all", "would", "there", "their"
    }
    
    for token in doc:
        if token.is_alpha and not token.is_stop:
            total_words += 1
            word_lower = token.text.lower()
            is_in_vocab = word_lower in nlp_model.vocab.strings
            consonant_pattern = re.search(r'[bcdfghjklmnpqrstvwxyz]{4,}', word_lower)
            vowel_pattern = re.search(r'[aeiou]{4,}', word_lower)
            is_uncommon_short = len(word_lower) <= 2 and word_lower not in common_words
            
            if not is_in_vocab and token.pos_ != "PROPN":
                if consonant_pattern or vowel_pattern or is_uncommon_short:
                    error_count += 1
                elif len(word_lower) > 3 and word_lower not in common_words:
                    if re.search(r'[^aeiou]{3,}', word_lower):
                        error_count += 0.5
    
    return float((error_count / total_words * 100)) if total_words > 0 else 0.0


def extract_whisper_spacy_features(audio_path):
    """Transcribe con Whisper y analiza con spaCy."""
    try:
        result = whisper_model.transcribe(str(audio_path), language='en')
        text = result.get('text', '').strip()
        import re
        text_clean = re.sub(r"\s+", " ", text)
    except Exception as e:
        print(f"  ⚠️ Whisper error: {e}")
        return {}
    
    if not text_clean:
        return {'n_words': 0, 'transcription': ''}
    
    doc = nlp(text_clean)
    words = [t for t in doc if t.is_alpha]
    sents = list(doc.sents)
    tokens = [t for t in doc if not t.is_punct and not t.is_space]
    
    features = {
        'transcription': text_clean,
        'n_chars': len(text_clean),
        'n_tokens': len(tokens),
        'n_words': len(words),
        'n_sents': len(sents),
        'mean_words_per_sent': len(words) / max(len(sents), 1) if sents else 0.0,
    }
    
    # Diversidad léxica
    word_forms = [t.text.lower() for t in words]
    unique_words = set(word_forms)
    features['ttr'] = len(unique_words) / len(word_forms) if word_forms else 0.0
    
    window = 50
    if len(word_forms) >= window:
        ttrs = [len(set(word_forms[i:i + window])) / window for i in range(len(word_forms) - window + 1)]
        features['mattr_50'] = float(np.mean(ttrs))
    else:
        features['mattr_50'] = features['ttr']
        
    features['keyword_repetitions'] = keyword_repetitions(doc)
    
    # POS ratios
    pos_counts = Counter(t.pos_ for t in words)
    total = max(len(words), 1)
    features['noun_ratio'] = pos_counts.get('NOUN', 0) / total
    features['verb_ratio'] = pos_counts.get('VERB', 0) / total
    features['adj_ratio'] = pos_counts.get('ADJ', 0) / total
    features['adv_ratio'] = pos_counts.get('ADV', 0) / total
    features['content_ratio'] = sum(pos_counts.get(p, 0) for p in ["NOUN", "VERB", "ADJ", "ADV"]) / total
    
    # Fillers (advanced features)
    fillers = {"um", "uh", "ah", "hmm", "er", "like", "mean", "well", "you know"}
    filler_count = sum(1 for t in doc if t.text.lower() in fillers)
    features['Filler_frequency'] = (filler_count / len(doc)) * 100 if len(doc) > 0 else 0.0
    
    # Coherencia local
    similarities = []
    if len(sents) > 1:
        for i in range(len(sents) - 1):
            try:
                sim = sents[i].similarity(sents[i+1])
                similarities.append(sim)
            except:
                similarities.append(0.5)
        features['Local_coherence'] = float(np.mean(similarities)) if similarities else 0.5
    else:
        features['Local_coherence'] = 1.0
    
    # Errores léxicos (algoritmo original)
    features['Lexical_errors'] = detect_lexical_errors(doc, nlp)
    
    return features


def get_pause_features(audio_path):
    """Calcula estadísticas de pausas (silencios)."""
    y, sr = librosa.load(audio_path, sr=None)
    
    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=512)[0]
    threshold = np.mean(rms) * 0.3
    is_silence = rms < threshold
    
    # Encontrar duraciones de silencios
    pause_durations = []
    current_pause = 0
    for silent in is_silence:
        if silent:
            current_pause += 512 / sr
        else:
            if current_pause > 0.1:  # Solo pausas > 100ms
                pause_durations.append(current_pause)
            current_pause = 0
    
    if len(pause_durations) > 2:
        return {
            'Skewness_pause_duration': float(skew(pause_durations)),
            'Kurtosis_pause_duration': float(kurtosis(pause_durations))
        }
    return {'Skewness_pause_duration': 0.0, 'Kurtosis_pause_duration': 0.0}


def procesar_audio(audio_info):
    """Procesa un audio completo: extrae todas las features de audios ya normalizados."""
    path = audio_info['path']
    nombre = Path(path).stem
    categoria = audio_info['categoria']
    
    print(f"\n🎵 Procesando: {nombre} ({categoria})")
    
    print("  🔉 Evaluando calidad...")
    y, sr = librosa.load(path, sr=16000, mono=True)
    score, calidad = audio_quality_score(y, sr)
    
    resultado = {
        'uuid': str(uuid.uuid4()),
        'audio': f"{nombre}.wav",
        'name': normalizar_nombre_audio(nombre),
        'dementia': categoria,
        'gender': identificar_genero_pitch(path),
        'ethnicity': "",
        'score': score,
        'calidad': calidad,
        'parametros_librosa': {},
        'parametros_opensmile': {},
        'parametros_whisperSpacy': {}
    }
    
    print("  📊 Librosa...")
    resultado['parametros_librosa'] = extract_librosa_features(path)
    
    pause_feat = get_pause_features(path)
    resultado['parametros_librosa'].update(pause_feat)
    
    print("  🔬 OpenSMILE...")
    resultado['parametros_opensmile'] = extract_opensmile_features(path)
    
    print("  📝 Whisper + spaCy...")
    resultado['parametros_whisperSpacy'] = extract_whisper_spacy_features(path)
        
    print(f"  ✅ {nombre} completado")
    return resultado


def main():
    """Función principal: descarga, procesa, sube."""
    print("=" * 50)
    print("🥈 Silver Layer — Procesamiento de Audios")
    print("=" * 50)
    
    # 1. Descargar audios de S3 Bronze
    print("\n1. Descargando audios de S3 Bronze...")
    tmp_dir = tempfile.mkdtemp()
    archivos = descargar_audios_bronze(tmp_dir)
    
    if not archivos:
        print("❌ No se encontraron audios en S3 Bronze")
        return
    
    # 2. Procesar cada audio
    print(f"\n2. Procesando {len(archivos)} audios...")
    resultados = []
    for audio in tqdm(archivos, desc="Procesando"):
        try:
            resultado = procesar_audio(audio)
            resultados.append(resultado)
        except Exception as e:
            print(f"  ❌ Error en {audio['key']}: {e}")
    
    # 3. Subir JSON a S3 Silver
    print(f"\n3. Subiendo JSON a S3 Silver...")
    s3 = boto3.client('s3')
    
    json_data = json.dumps(resultados, indent=2, ensure_ascii=False, default=str)
    
    s3.put_object(
        Bucket=SILVER_BUCKET,
        Key=SILVER_KEY,
        Body=json_data,
        ContentType='application/json'
    )
    
    print(f"✅ Subido: s3://{SILVER_BUCKET}/{SILVER_KEY}")
    print(f"   Registros: {len(resultados)}")
    
    # Resumen
    print("\n" + "=" * 50)
    print("✅ Silver Layer completado")
    print("=" * 50)
    for r in resultados:
        n_librosa = len(r.get('parametros_librosa', {}))
        n_opensmile = len(r.get('parametros_opensmile', {}))
        n_whisper = len(r.get('parametros_whisperSpacy', {}))
        print(f"  {r['audio']} ({r['dementia']}): "
              f"librosa={n_librosa}, opensmile={n_opensmile}, whisper={n_whisper}")


if __name__ == '__main__':
    main()
