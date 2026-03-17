import json
import os
import re
import shutil
import tempfile
import warnings
from pathlib import Path
import librosa
import numpy as np
import pandas as pd
import opensmile
import soundfile as sf
import spacy
import textstat
import whisper
from scipy.stats import kurtosis, skew
from wordfreq import zipf_frequency
import imageio_ffmpeg

warnings.filterwarnings('ignore')

# =====================================================================
# CONFIGURACIÓN AUTOMÁTICA DE FFMPEG PARA WHISPER
# =====================================================================
# Obtenemos el ejecutable que descarga imageio_ffmpeg
ffmpeg_exe_original = imageio_ffmpeg.get_ffmpeg_exe()
ffmpeg_dir = os.path.dirname(ffmpeg_exe_original)

# Whisper requiere que el ejecutable se llame exactamente "ffmpeg.exe".
# Creamos una copia con el nombre correcto en la misma carpeta si no existe.
ffmpeg_alias = os.path.join(ffmpeg_dir, "ffmpeg.exe")

if not os.path.exists(ffmpeg_alias):
    try:
        shutil.copyfile(ffmpeg_exe_original, ffmpeg_alias)
    except Exception as e:
        print(f"Advertencia: no se pudo crear el alias de ffmpeg: {e}")

# Añadimos la carpeta de ffmpeg al PRINCIPIO del PATH del sistema
os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
# =====================================================================

print("Cargando modelo de Whisper (medium)...")
model_whisper = whisper.load_model("medium")

print("Cargando modelo de SpaCy (en_core_web_lg)...")
nlp = spacy.load("en_core_web_lg")
nlp.add_pipe("sentencizer", before="parser")

print("Cargando modelo de OpenSMILE...")
smile = opensmile.Smile(
    feature_set=opensmile.FeatureSet.eGeMAPSv02,
    feature_level=opensmile.FeatureLevel.Functionals,
)

# =====================================================================
# 1. ESTANDARIZACIÓN DE AUDIO
# =====================================================================
def standardize_audio_to_wav(in_path, out_path, target_sr=16000, mono=True, peak=0.99, silence_eps=1e-6):
    in_p = Path(in_path)
    out_p = Path(out_path)

    y, sr_orig = librosa.load(str(in_p), sr=None, mono=mono)

    if sr_orig != target_sr and len(y):
        y = librosa.resample(y, orig_sr=sr_orig, target_sr=target_sr)

    if len(y):
        max_abs = float(np.max(np.abs(y)))
    else:
        max_abs = 0.0

    is_silent = bool(max_abs < silence_eps)

    if not is_silent and len(y):
        y = y / (max_abs + 1e-12) * peak

    sf.write(str(out_p), y, target_sr, subtype="PCM_16")
    return str(out_p)

# =====================================================================
# 2. EXTRACCIÓN LIBROSA
# =====================================================================
def _segments_from_mask(mask):
    mask = mask.astype(bool)
    if mask.size == 0: return []
    diff = np.diff(mask.astype(int))
    starts = np.where(diff == 1)[0] + 1
    ends = np.where(diff == -1)[0] + 1
    if mask[0]: starts = np.r_[0, starts]
    if mask[-1]: ends = np.r_[ends, mask.size]
    return list(zip(starts, ends))

def _segment_stats_from_mask(mask, hop_length, sr, prefix):
    segs = _segments_from_mask(mask)
    lengths_frames = np.array([e - s for s, e in segs], dtype=float)
    if len(lengths_frames) == 0:
        return {f"{prefix}_segments_n": 0, f"{prefix}_dur_mean_s": 0.0, f"{prefix}_dur_std_s": 0.0, f"{prefix}_dur_max_s": 0.0}
    lengths_s = lengths_frames * (hop_length / sr)
    return {
        f"{prefix}_segments_n": int(len(lengths_s)),
        f"{prefix}_dur_mean_s": float(np.mean(lengths_s)),
        f"{prefix}_dur_std_s": float(np.std(lengths_s)),
        f"{prefix}_dur_max_s": float(np.max(lengths_s)),
    }

def _durations_s_from_mask(mask, hop_length, sr):
    segs = _segments_from_mask(mask)
    if len(segs) == 0: return np.array([], dtype=float)
    lengths_frames = np.array([e - s for s, e in segs], dtype=float)
    return lengths_frames * (hop_length / sr)

def extract_librosa_features(audio_path, target_sr=16000, n_fft=2048, hop_length=512):
    y, sr = librosa.load(audio_path, sr=target_sr, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)
    
    rms = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=hop_length)[0]
    rms_threshold = np.percentile(rms, 25)
    silence_mask = rms < rms_threshold
    silence_ratio = float(np.mean(silence_mask))
    
    silence_stats = _segment_stats_from_mask(silence_mask, hop_length=hop_length, sr=sr, prefix="silence")
    pause_durations_s = _durations_s_from_mask(silence_mask, hop_length=hop_length, sr=sr)
    
    if len(pause_durations_s) >= 3:
        silence_skew = float(skew(pause_durations_s, bias=False))
        silence_kurt = float(kurtosis(pause_durations_s, fisher=True, bias=False))
    else:
        silence_skew = np.nan
        silence_kurt = np.nan
        
    f0, voiced_flag, _ = librosa.pyin(y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), frame_length=n_fft, hop_length=hop_length)
    voiced_ratio = float(np.mean(voiced_flag))
    voiced_stats = _segment_stats_from_mask(voiced_flag, hop_length=hop_length, sr=sr, prefix="voiced")
    
    voiced_mean = voiced_stats.get("voiced_dur_mean_s", 0.0)
    voiced_std = voiced_stats.get("voiced_dur_std_s", 0.0)
    voiced_dur_cv = float(voiced_std / voiced_mean) if voiced_mean and voiced_mean > 0 else np.nan

    return {
        "duracion_s": float(duration),
        "pause_count": silence_stats["silence_segments_n"],
        "pause_duration_mean": silence_stats["silence_dur_mean_s"],
        "pause_time_ratio": float(silence_ratio),
        "speech_segment_duration_mean": voiced_mean,
        "speech_segment_duration_cv": voiced_dur_cv,
        "pause_duration_skewness": silence_skew,
        "pause_duration_kurtosis": silence_kurt,
        "voiced_ratio": float(voiced_ratio)
    }

# =====================================================================
# 3. EXTRACCIÓN OPENSMILE
# =====================================================================
def extract_opensmile_features(audio_path):
    df_feat = smile.process_file(str(audio_path)).copy()
    row = df_feat.iloc[0].to_dict()
    return {
        "f0_mean": row.get("F0semitoneFrom27.5Hz_sma3nz_amean", np.nan),
        "f0_std": row.get("F0semitoneFrom27.5Hz_sma3nz_stddevNorm", np.nan),
        "f0_range": row.get("F0semitoneFrom27.5Hz_sma3nz_pctlrange0-2", np.nan),
        "loudness_mean": row.get("loudness_sma3_amean", np.nan),
        "loudness_std": row.get("loudness_sma3_stddevNorm", np.nan),
        "jitter_local": row.get("jitterLocal_sma3nz_amean", np.nan),
        "shimmer_local": row.get("shimmerLocaldB_sma3nz_amean", np.nan),
        "hnr": row.get("HNRdBACF_sma3nz_amean", np.nan),
        "alpha_ratio": row.get("alphaRatioUV_sma3nz_amean", np.nan),
        "hammarberg_index": row.get("hammarbergIndexV_sma3nz_amean", np.nan),
        "spectral_slope_mean": row.get("slopeV0-500_sma3nz_amean", np.nan),
        "spectral_slope_std": row.get("slopeV0-500_sma3nz_stddevNorm", np.nan)
    }

# =====================================================================
# 4. EXTRACCIÓN WHISPER
# =====================================================================
def transcribe_whisper(audio_path):
    result = model_whisper.transcribe(str(audio_path), task="transcribe", verbose=False, fp16=False)
    segments = result.get("segments", [])
    pause_prob = np.mean([s["no_speech_prob"] for s in segments]) if segments else 0.0
    duration = segments[-1]["end"] if segments else 1e-12
    return {
        "transcript": result.get("text", "").strip(),
        "duration": duration,
        "pause_prob": pause_prob
    }

# =====================================================================
# 5. LINGÜÍSTICA (SPACY / TEXTSTAT / WORDFREQ)
# =====================================================================
def clean_text_basic(text):
    if not isinstance(text, str): return ""
    return re.sub(r"\s+", " ", text.strip())

FILLERS_RE = [re.compile(p, flags=re.IGNORECASE) for p in [r"\bum\b", r"\buh\b", r"\berm\b", r"\bah\b", r"\byou know\b", r"\bi mean\b", r"\blike\b"]]
REFORMULATIONS_RE = [re.compile(p, flags=re.IGNORECASE) for p in [r"\bi mean\b", r"\bor rather\b", r"\bthat is\b", r"\bi guess\b", r"\bi think\b", r"\bno\,\b", r"\bno\.\b"]]

def count_patterns(text, patterns_re):
    if not text: return 0
    return int(sum(len(rx.findall(text)) for rx in patterns_re))

def lexical_repetitions(lemmas):
    if not lemmas or len(lemmas) < 2: return 0
    return int(sum(1 for i in range(1, len(lemmas)) if lemmas[i] == lemmas[i - 1]))

def subordination_ratio(doc):
    if doc is None or len(list(doc.sents)) == 0: return np.nan
    dep_markers = {"mark", "advcl", "ccomp", "xcomp", "acl", "relcl"}
    sents = list(doc.sents)
    count = sum(1 for sent in sents if any(t.pos_ == "SCONJ" or t.dep_ in dep_markers for t in sent))
    return float(count / len(sents))

def local_coherence(doc, ngram_n=2):
    if doc is None or len(list(doc.sents)) < 2: return np.nan
    sents = list(doc.sents)
    def sent_ngrams(sent):
        toks = [t.lemma_.lower() for t in sent if t.is_alpha]
        return [tuple(toks[i:i+ngram_n]) for i in range(len(toks)-ngram_n+1)] if len(toks) >= ngram_n else []
    def cosine(a, b):
        inter = set(a.keys()) & set(b.keys())
        num = sum(a[k]*b[k] for k in inter)
        den = (sum(v*v for v in a.values())**0.5) * (sum(v*v for v in b.values())**0.5)
        return float(num / den) if den > 0 else 0.0
    vecs = []
    for sent in sents:
        d = {}
        for g in sent_ngrams(sent): d[g] = d.get(g, 0) + 1
        vecs.append(d)
    sims = [cosine(vecs[i], vecs[i+1]) for i in range(len(vecs)-1)]
    return float(np.mean(sims)) if sims else np.nan

def lexical_error_rate_oov(words_text, lang="en", zipf_threshold=2.0):
    if not words_text: return np.nan
    rare = sum(1 for w in words_text if zipf_frequency(w.lower(), lang) < zipf_threshold)
    return float(rare / len(words_text))

def incomplete_sentence_ratio(doc):
    if doc is None or not list(doc.sents): return np.nan
    sents = list(doc.sents)
    inc = sum(1 for sent in sents if not any(t.pos_ in {"VERB", "AUX"} for t in sent))
    return float(inc / len(sents))

def moving_ttr(tokens, window=50):
    if len(tokens) < 2: return np.nan
    if len(tokens) <= window: return len(set(tokens)) / len(tokens)
    return float(np.mean([len(set(tokens[i:i+window])) / window for i in range(len(tokens) - window + 1)]))

def extract_spacy_features(text):
    text = clean_text_basic(text)
    doc = nlp(text)
    words = [t for t in doc if t.is_alpha]
    lemmas = [t.lemma_.lower() for t in words]
    word_texts = [t.text for t in words]
    n_words = len(words)
    sents = list(doc.sents)
    n_sents = len(sents)

    sent_lengths = [len([t for t in sent if t.is_alpha]) for sent in sents]
    mean_wps = float(n_words / n_sents) if n_sents > 0 else np.nan
    std_wps = float(np.std(sent_lengths)) if len(sent_lengths) > 1 else 0.0
    
    ttr = float(len(set(lemmas)) / n_words) if n_words > 0 else np.nan
    mattr = float(moving_ttr(lemmas, window=50)) if n_words > 0 else np.nan

    pos_counts = {}
    for t in words: pos_counts[t.pos_] = pos_counts.get(t.pos_, 0) + 1
    
    noun_ratio = float(pos_counts.get("NOUN", 0) / n_words) if n_words > 0 else np.nan
    verb_ratio = float(pos_counts.get("VERB", 0) / n_words) if n_words > 0 else np.nan
    adj_adv_ratio = float((pos_counts.get("ADJ", 0) + pos_counts.get("ADV", 0)) / n_words) if n_words > 0 else np.nan
    function_ratio = float(sum(1 for t in words if t.pos_ in {"DET","ADP","PRON","AUX","CCONJ","SCONJ","PART"}) / n_words) if n_words > 0 else np.nan
    
    idea_density = float((pos_counts.get("NOUN",0) + pos_counts.get("VERB",0) + pos_counts.get("ADJ",0) + pos_counts.get("ADV",0)) / n_words) if n_words > 0 else np.nan
    pronoun_to_propn_ratio = float(pos_counts.get("PRON",0) / (pos_counts.get("PROPN",0) + 1e-12)) if n_words > 0 else np.nan

    return {
        "total_words": int(n_words),
        "total_sentences": int(n_sents),
        "sentence_length_mean": mean_wps,
        "sentence_length_std": std_wps,
        "type_token_ratio": ttr,
        "mattr_50": mattr,
        "noun_ratio": noun_ratio,
        "content_verb_ratio": verb_ratio,
        "adj_adv_ratio": adj_adv_ratio,
        "function_word_ratio": function_ratio,
        "subordinate_sentence_ratio": subordination_ratio(doc),
        "lexical_repetitions": lexical_repetitions(lemmas),
        "reformulations": count_patterns(text, REFORMULATIONS_RE),
        "fillers": count_patterns(text, FILLERS_RE),
        "idea_density": idea_density,
        "local_coherence_bigram": local_coherence(doc, ngram_n=2),
        "lexical_error_rate": lexical_error_rate_oov(word_texts),
        "pronoun_to_propn_ratio": pronoun_to_propn_ratio,
        "mean_word_length": float(np.mean([len(w) for w in word_texts])) if word_texts else np.nan,
        "readability_fk_grade": float(textstat.flesch_kincaid_grade(text)) if text else np.nan,
        "incomplete_sentence_ratio": incomplete_sentence_ratio(doc),
    }

# =====================================================================
# 6. INFORMACIÓN DEL ARCHIVO
# =====================================================================
def extract_file_metadata(audio_path, sujeto=None, dementia=None, gender=None):
    p = Path(audio_path)
    return {
        "audio_file": p.name,
        "sujeto": sujeto,
        "dementia": dementia,
        "gender": gender
    }

# =====================================================================
# 7. PIPELINE PRINCIPAL Y GLOBAL
# =====================================================================
def process_audio_pipeline(audio_path, output_json="features_output.json", sujeto=None, dementia=None, gender=None):
    print(f"-> Procesando audio: {audio_path}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_wav = os.path.join(temp_dir, "temp.wav")
        print("  1. Estandarizando audio...")
        standardize_audio_to_wav(audio_path, temp_wav)
        
        print("  2. Extrayendo características de OpenSMILE...")
        opensmile_feats = extract_opensmile_features(temp_wav)
        
        print("  3. Extrayendo características Acústicas (Librosa)...")
        librosa_feats = extract_librosa_features(temp_wav)
        
        print("  4. Transcribiendo con Whisper...")
        whisper_data = transcribe_whisper(temp_wav)
        transcript = whisper_data["transcript"]
        
        print("  5. Extrayendo características lingüísticas (SpaCy)...")
        spacy_feats = extract_spacy_features(transcript)
        
        print("  6. Extrayendo metadatos del archivo...")
        file_metadata = extract_file_metadata(audio_path, sujeto=sujeto, dementia=dementia, gender=gender)
        
        # Combinar variables
        all_features = {}
        all_features.update(file_metadata)
        all_features.update(opensmile_feats)
        all_features.update(librosa_feats)
        all_features.update(spacy_feats)
        
        # Cálculos derivados
        duration_s = librosa_feats.get("duracion_s", 0)
        n_words = spacy_feats.get("total_words", 0)
        
        if duration_s > 0:
            all_features["speech_rate_wpm"] = (n_words / duration_s) * 60.0
        else:
            all_features["speech_rate_wpm"] = np.nan
            
        # Filtrar exactamente a las variables solicitadas en el orden especificado
        expected_keys = [
            "duracion_s", "sujeto", "audio_file", "dementia", "pause_count", "pause_duration_mean", 
            "pause_time_ratio", "speech_segment_duration_mean", "speech_segment_duration_cv", 
            "pause_duration_skewness", "pause_duration_kurtosis", "voiced_ratio", "f0_mean", 
            "f0_std", "f0_range", "loudness_mean", "loudness_std", "jitter_local", "shimmer_local", 
            "hnr", "alpha_ratio", "hammarberg_index", "spectral_slope_mean", "spectral_slope_std", 
            "gender", "total_words", "total_sentences", "sentence_length_mean", "sentence_length_std", 
            "type_token_ratio", "mattr_50", "noun_ratio", "content_verb_ratio", "adj_adv_ratio", 
            "function_word_ratio", "subordinate_sentence_ratio", "lexical_repetitions", "reformulations", 
            "fillers", "idea_density", "local_coherence_bigram", "lexical_error_rate", 
            "pronoun_to_propn_ratio", "mean_word_length", "readability_fk_grade", 
            "incomplete_sentence_ratio", "speech_rate_wpm"
        ]
        
        final_features = {}
        for k in expected_keys:
            v = all_features.get(k, np.nan)
            if pd.isna(v):
                final_features[k] = None
            else:
                final_features[k] = v

        if output_json:
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(final_features, f, indent=4, ensure_ascii=False)
            print(f"-> Guardado JSON en: {output_json}")

        return final_features


if __name__ == "__main__":
    process_audio_pipeline("adrsdt1.wav")