"""
Análisis completo de Identificacion_Idioma_y_Texto.json
Dataset: ADReSSo21 - Identificación de idioma y transcripción de audios
"""

import json
import statistics
import os
from collections import Counter, defaultdict

# ─────────────────────────────────────────────────────────────
# 1. CARGA DE DATOS
# ─────────────────────────────────────────────────────────────
JSON_PATH = r"C:\Users\vfuen\Documents\Master_VS\TFM\Identificacion_Idioma_y_Texto.json"

print("=" * 65)
print("  ANÁLISIS: Identificacion_Idioma_y_Texto.json")
print("=" * 65)

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

items = data["items"]

# ─────────────────────────────────────────────────────────────
# 2. METADATOS GLOBALES
# ─────────────────────────────────────────────────────────────
print("\n── 2. METADATOS GLOBALES ──────────────────────────────────")
print(f"  Modelo Whisper usado       : {data['model']}")
print(f"  Directorio de entrada      : {data['input_root']}")
print(f"  Total de audios            : {data['total_audios']}")
print(f"  Procesados correctamente   : {data['processed']}")
print(f"  Fallidos                   : {data['failed']}")

# ─────────────────────────────────────────────────────────────
# 3. DISTRIBUCIÓN DE IDIOMAS
# ─────────────────────────────────────────────────────────────
print("\n── 3. DISTRIBUCIÓN DE IDIOMAS ─────────────────────────────")
lang_counter = Counter(item["data"]["language"] for item in items)
for lang, count in lang_counter.most_common():
    pct = count / len(items) * 100
    bar = "█" * int(pct / 2)
    print(f"  {lang:>4}  {count:>4} audios  ({pct:5.1f}%)  {bar}")

non_english = [(item["id"], item["data"]["language"])
               for item in items if item["data"]["language"] != "en"]
print(f"\n  ⚠  Audios NO en inglés: {len(non_english)}")
if non_english:
    for audio_id, lang in non_english:
        print(f"       • {audio_id}  →  {lang}")

# ─────────────────────────────────────────────────────────────
# 4. ESTADÍSTICAS DE DURACIÓN
# ─────────────────────────────────────────────────────────────
print("\n── 4. ESTADÍSTICAS DE DURACIÓN (segundos) ─────────────────")
durations = [item["data"]["duration"] for item in items]
print(f"  Mínima    : {min(durations):.2f} s")
print(f"  Máxima    : {max(durations):.2f} s")
print(f"  Media     : {statistics.mean(durations):.2f} s")
print(f"  Mediana   : {statistics.median(durations):.2f} s")
print(f"  Desv. std : {statistics.stdev(durations):.2f} s")
total_min = sum(durations) / 60
print(f"  Total     : {sum(durations):.0f} s  ({total_min:.1f} min)")

# Distribución en rangos
buckets = [(0,20,"0-20s"), (20,40,"20-40s"), (40,60,"40-60s"),
           (60,90,"60-90s"), (90,float('inf'),"≥90s")]
print("\n  Distribución por rangos:")
for lo, hi, label in buckets:
    n = sum(1 for d in durations if lo <= d < hi)
    bar = "▪" * n
    print(f"    {label:>6}: {n:>3}  {bar[:50]}")

# ─────────────────────────────────────────────────────────────
# 5. ESTADÍSTICAS DE PAUSE_PROB
# ─────────────────────────────────────────────────────────────
print("\n── 5. PROBABILIDAD DE PAUSA (pause_prob) ──────────────────")
pauses = [item["data"]["pause_prob"] for item in items]
print(f"  Mínima    : {min(pauses):.4f}")
print(f"  Máxima    : {max(pauses):.4f}")
print(f"  Media     : {statistics.mean(pauses):.4f}")
print(f"  Mediana   : {statistics.median(pauses):.4f}")
print(f"  Desv. std : {statistics.stdev(pauses):.4f}")

# Top 10 audios con más pausas
sorted_by_pause = sorted(items, key=lambda x: x["data"]["pause_prob"], reverse=True)
print("\n  Top 10 audios con mayor pause_prob:")
for item in sorted_by_pause[:10]:
    print(f"    {item['id']:>20}  →  {item['data']['pause_prob']:.4f}")

# ─────────────────────────────────────────────────────────────
# 6. ANÁLISIS DE SEGMENTOS Y HABLANTES
# ─────────────────────────────────────────────────────────────
print("\n── 6. ANÁLISIS DE SEGMENTOS Y HABLANTES ───────────────────")
num_segments = [len(item["data"]["segments"]) for item in items]
print(f"  Segmentos totales     : {sum(num_segments)}")
print(f"  Media por audio       : {statistics.mean(num_segments):.1f}")
print(f"  Mínimo en un audio    : {min(num_segments)}")
print(f"  Máximo en un audio    : {max(num_segments)}")

# Conteo por hablante
speaker_counts = defaultdict(int)
speaker_duration = defaultdict(float)
no_speech_probs = []

for item in items:
    for seg in item["data"]["segments"]:
        spk = seg.get("speaker", "unknown")
        dur = seg["end"] - seg["start"]
        speaker_counts[spk] += 1
        speaker_duration[spk] += dur
        no_speech_probs.append(seg.get("no_speech_prob", 0))

print("\n  Por hablante:")
for spk in sorted(speaker_counts):
    cnt = speaker_counts[spk]
    dur = speaker_duration[spk]
    print(f"    {spk:>15} : {cnt:>5} segmentos  |  {dur/60:6.1f} min de habla")

print(f"\n  no_speech_prob  →  media: {statistics.mean(no_speech_probs):.4f}  "
      f"|  mediana: {statistics.median(no_speech_probs):.4f}")

# Segmentos con alta no_speech_prob (>0.5, posible silencio/ruido)
high_no_speech = sum(1 for p in no_speech_probs if p > 0.5)
print(f"  Segmentos con no_speech_prob > 0.5 : {high_no_speech} "
      f"({high_no_speech/len(no_speech_probs)*100:.1f}%)")

# ─────────────────────────────────────────────────────────────
# 7. LONGITUD DE TRANSCRIPCIONES
# ─────────────────────────────────────────────────────────────
print("\n── 7. LONGITUD DE TRANSCRIPCIONES ─────────────────────────")
word_counts = [len(item["data"]["transcript"].split()) for item in items]
char_counts = [len(item["data"]["transcript"]) for item in items]
print(f"  Palabras  →  min: {min(word_counts)}  max: {max(word_counts)}  "
      f"media: {statistics.mean(word_counts):.1f}")
print(f"  Caracteres→  min: {min(char_counts)}  max: {max(char_counts)}  "
      f"media: {statistics.mean(char_counts):.1f}")

# Top 5 transcripciones más largas
sorted_by_words = sorted(items, key=lambda x: len(x["data"]["transcript"].split()), reverse=True)
print("\n  Top 5 transcripciones más largas (en palabras):")
for item in sorted_by_words[:5]:
    wc = len(item["data"]["transcript"].split())
    print(f"    {item['id']:>20}  →  {wc} palabras")

# ─────────────────────────────────────────────────────────────
# 8. PALABRAS POR MINUTO (velocidad de habla del paciente)
# ─────────────────────────────────────────────────────────────
print("\n── 8. VELOCIDAD DE HABLA (palabras/min) ───────────────────")
wpm_list = []
for item in items:
    dur_min = item["data"]["duration"] / 60
    if dur_min > 0:
        wpm = len(item["data"]["transcript"].split()) / dur_min
        wpm_list.append((item["id"], wpm))

wpm_vals = [x[1] for x in wpm_list]
print(f"  Media     : {statistics.mean(wpm_vals):.1f} palabras/min")
print(f"  Mediana   : {statistics.median(wpm_vals):.1f} palabras/min")
print(f"  Mínima    : {min(wpm_vals):.1f} palabras/min")
print(f"  Máxima    : {max(wpm_vals):.1f} palabras/min")

# Clasificación por ritmo
slow   = sum(1 for v in wpm_vals if v < 80)
normal = sum(1 for v in wpm_vals if 80 <= v < 150)
fast   = sum(1 for v in wpm_vals if v >= 150)
print(f"\n  Ritmo lento  (<80 wpm)   : {slow} audios")
print(f"  Ritmo normal (80-150 wpm): {normal} audios")
print(f"  Ritmo rápido (≥150 wpm)  : {fast} audios")

# ─────────────────────────────────────────────────────────────
# 9. RESUMEN EJECUTIVO
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  RESUMEN EJECUTIVO")
print("=" * 65)
print(f"  ✔ {len(items)} audios analizados con Whisper '{data['model']}'")
print(f"  ✔ {lang_counter.get('en',0)} en inglés ({lang_counter.get('en',0)/len(items)*100:.1f}%)")
print(f"  ✔ {len(non_english)} audios en otro idioma")
print(f"  ✔ Duración media: {statistics.mean(durations):.1f}s  |  Total: {total_min:.1f} min")
print(f"  ✔ {sum(num_segments)} segmentos totales (media {statistics.mean(num_segments):.1f}/audio)")
print(f"  ✔ Velocidad media del habla: {statistics.mean(wpm_vals):.1f} palabras/min")
print(f"  ✔ pause_prob media: {statistics.mean(pauses):.4f}")
print("=" * 65)
