# 📊 Documentación Completa de Características

Este documento describe **todas** las características implementadas en el sistema de detección de demencia, incluyendo las nuevas características específicas y las características estándar optimizadas.

---

## 🎯 Nuevas Características (Específicas para Demencia)

### 1. Skewness_pause_duration
**Tipo:** Audio | **Fuente:** Librosa + scipy.stats

Mide la **asimetría** de la distribución de duraciones de pausas. Valores altos indican presencia de pausas inusualmente largas, característico de pacientes con demencia que tienen dificultad para encontrar palabras (anomia).

**Hiperparámetros:**
- `top_db=25`: Umbral para separar habla de silencio (estándar librosa)
- `min_pause=0.05s`: Filtra micro-pausas menores a 50ms

**Interpretación:**
- Skewness > 1: Distribución con cola larga → indicador de demencia
- Skewness ≈ 0: Distribución simétrica → normal

---

### 2. Kurtosis_pause_duration
**Tipo:** Audio | **Fuente:** Librosa + scipy.stats

Mide el **apuntamiento** de la distribución de pausas. Indica qué tan concentradas están las pausas alrededor de la media.

**Interpretación:**
- Kurtosis > 3: Distribución más apuntada
- Kurtosis < 3: Distribución más plana (mayor variabilidad)

---

### 3. Filler_frequency
**Tipo:** Texto | **Fuente:** Whisper + spaCy

Frecuencia de **muletillas** (fillers) en el discurso como porcentaje del total de tokens. Las muletillas aumentan cuando hay esfuerzo cognitivo para encontrar palabras.

**Muletillas detectadas:** "um", "uh", "ah", "hmm", "er", "like", "mean", "well", "you know"

**Interpretación:**
- < 2%: Discurso fluido, normal
- 2-5%: Posible deterioro leve
- > 5%: Indicador fuerte de demencia

---

### 4. Local_coherence ⭐
**Tipo:** Texto | **Fuente:** Whisper + spaCy

Mide la **similitud semántica** entre frases adyacentes usando vectores de palabras (word embeddings). La demencia causa pérdida del hilo conductor y cambios de tema abruptos.

**Requisitos:**
- Modelo spaCy `en_core_web_md` o `en_core_web_lg` (requiere vectores)
- Métrica: Coseno entre vectores de frases

**Cómo funciona:**
1. Segmenta el texto en frases
2. Convierte cada frase a un vector de 300 dimensiones
3. Calcula similitud (coseno) entre frases adyacentes
4. Promedia todas las similitudes

**Interpretación:**
- 0.7-1.0: Muy coherente (normal)
- 0.5-0.7: Moderadamente coherente (posible deterioro)
- 0.3-0.5: Poco coherente (demencia)
- 0.0-0.3: Muy incoherente (demencia avanzada)

**Ejemplo:**
```
Coherente (0.8):
  "I went to the store. I bought groceries. Then I came home."

Incoherente (0.2):
  "I went to the store. My grandson studies medicine. The flowers are beautiful."
```

---

### 5. Lexical_errors
**Tipo:** Texto | **Fuente:** Whisper + spaCy

Frecuencia de **palabras mal escritas** o con patrones sospechosos detectados en la transcripción.

**Patrones detectados:**
- 4+ consonantes seguidas
- 4+ vocales seguidas
- Palabras muy cortas no comunes
- Palabras no reconocidas por spaCy

**Interpretación:**
- < 1%: Transcripción limpia
- 1-3%: Algunos errores
- > 3%: Muchos errores (posible deterioro o audio de mala calidad)

---

## 📊 Características Estándar

### Librosa (~30 características)

**MFCCs (13 características):**
- `mfcc_1_mean` hasta `mfcc_13_mean` (solo mean, sin std/min/max)

**Espectrales:**
- `spectral_centroid_mean` - Centro de masa del espectro
- `spectral_rolloff_mean` - Frecuencia del 85% de energía
- `spectral_bandwidth_mean` - Ancho de banda espectral
- `zcr_mean` - Tasa de cruces por cero
- `chroma_mean` - Energía de clases de pitch

**Pitch y Calidad Vocal:**
- `pitch_mean`, `pitch_std` - Frecuencia fundamental
- `jitter` - Variabilidad del pitch
- `shimmer` - Variabilidad de amplitud
- `hnr_db` - Harmonic-to-Noise Ratio
- `rms_mean`, `rms_std` - Energía RMS

**Básicas:**
- `duration` - Duración del audio
- `tempo` - Tempo estimado (BPM)

### OpenSMILE eGeMAPSv02 (88 características)

Conjunto estándar diseñado específicamente para análisis clínico y paralingüístico. **Todas se mantienen activas** (esenciales).

Incluye:
- Características de F0 (pitch)
- Formantes (F1, F2, F3)
- Energía y loudness
- Jitter y shimmer locales
- Características espectrales
- Segmentación voiced/unvoiced

### Whisper/spaCy (~12 características)

**Métricas básicas:**
- `n_chars`, `n_tokens`, `n_words`, `n_sents`
- `mean_words_per_sent`

**Diversidad léxica:**
- `ttr` - Type-Token Ratio
- `mattr_50` - Moving-Average Type-Token Ratio (ventana de 50)

**Análisis lingüístico:**
- `keyword_repetitions` - Repeticiones de palabras clave
- `noun_ratio`, `verb_ratio`, `adj_ratio`, `adv_ratio`
- `content_ratio` - Ratio de palabras de contenido

---

## ⚠️ Características Opcionales (Comentadas)

Para reducir el riesgo de overfitting, algunas características están comentadas con `# ⚠️ OPCIONAL:`:

### Librosa - Estadísticas Detalladas
- `mfcc_X_std`, `mfcc_X_min`, `mfcc_X_max` (solo se mantiene mean)
- `spectral_*_std` (solo se mantiene mean)
- `spectral_contrast`, `spectral_flatness`
- `pitch_min`, `pitch_max`, `pitch_median`, `pitch_skew`
- `energy` (redundante con rms_mean)

### OpenSMILE ComParE 2016
- **Completamente comentado** (6373 características - demasiado grande)

### Whisper/spaCy - Detallados
- `pron_ratio`, `propn_ratio`
- `noun_pron_ratio`
- `transcription` (solo para debugging)

**Para activar:** Busca `# ⚠️ OPCIONAL:` en `scripts/Process_Parametros_.py` y descomenta.

---

## 📈 Resumen de Optimización

| Categoría | Antes | Después | Reducción |
|-----------|-------|---------|-----------|
| Librosa | ~60 | ~30 | 50% |
| OpenSMILE eGeMAPS | 88 | 88 | 0% |
| OpenSMILE ComParE | 6373 | 0 | 100% |
| Whisper/spaCy | ~15 | ~12 | 20% |
| Nuevas | 0 | 5 | +5 |
| **TOTAL** | **~6536** | **~135** | **98%** |

---

## 🔍 Referencias

- **Pausas**: Investigación sobre anomia en demencia
- **Fillers**: Estudios sobre disfluencias en habla espontánea
- **Coherencia**: Análisis de coherencia semántica en Alzheimer
- **eGeMAPSv02**: Eyben et al. (2016) - The Geneva Minimalistic Acoustic Parameter Set
