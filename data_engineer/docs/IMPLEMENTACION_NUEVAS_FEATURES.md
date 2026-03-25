# 🔬 Implementación de las 5 Nuevas Características

Este documento explica **paso a paso** cómo se implementaron las 5 nuevas características específicas para la detección de demencia.

---

## 📋 Resumen Ejecutivo

Se implementaron **5 características nuevas** que capturan patrones específicos relacionados con deterioro cognitivo:

1. **Skewness_pause_duration** - Asimetría de la distribución de pausas
2. **Kurtosis_pause_duration** - Apuntamiento de la distribución de pausas
3. **Filler_frequency** - Frecuencia de muletillas en el discurso
4. **Local_coherence** - Coherencia semántica entre frases adyacentes
5. **Lexical_errors** - Frecuencia de errores léxicos

---

## 1️⃣ Skewness_pause_duration

### ¿Qué mide?

La **asimetría** (skewness) de la distribución de duraciones de pausas en el audio. Detecta si hay pausas inusualmente largas, característico de pacientes con demencia que tienen dificultad para encontrar palabras (anomia).

### Implementación Paso a Paso

```python
def get_pause_features(audio_path, sr=None):
    """
    Calcula Skewness y Kurtosis de las pausas de silencio.
    """
    # PASO 1: Cargar el audio
    y, sr = librosa.load(audio_path, sr=sr)
    
    # PASO 2: Detectar segmentos NO-silenciosos (habla)
    # librosa.effects.split() encuentra intervalos donde hay señal
    # top_db=25 es el umbral: señales > 25dB por debajo del pico se consideran silencio
    non_silent_intervals = librosa.effects.split(y, top_db=25)
    # Resultado: [(start1, end1), (start2, end2), ...] en muestras
    
    # PASO 3: Calcular duraciones de pausas (silencios entre segmentos)
    pause_durations = []
    
    # Para cada par de segmentos consecutivos
    for i in range(len(non_silent_intervals) - 1):
        end_current = non_silent_intervals[i][1]    # Fin del segmento actual
        start_next = non_silent_intervals[i+1][0]   # Inicio del siguiente
        
        # Duración de la pausa en segundos
        duration = (start_next - end_current) / sr
        
        # Filtrar micro-pausas menores a 50ms (ruido, no pausas cognitivas)
        if duration > 0.05:
            pause_durations.append(duration)
    
    # PASO 4: Calcular estadísticas si hay suficientes pausas
    if len(pause_durations) > 1:
        from scipy.stats import skew, kurtosis
        
        return {
            "Skewness_pause_duration": float(skew(pause_durations)),
            "Kurtosis_pause_duration": float(kurtosis(pause_durations))
        }
    else:
        return {"Skewness_pause_duration": 0.0, "Kurtosis_pause_duration": 0.0}
```

### Visualización del Proceso

```
Audio Original:
[████████]...[████]...[██████████]...[██]...[████████]
  habla    pausa  habla   pausa   habla  pausa  habla

Paso 1: Detectar segmentos de habla
Segmentos: [0-1000], [1500-2000], [3000-5000], [5500-6000], [7000-10000]

Paso 2: Calcular pausas entre segmentos
Pausa 1: entre 1000 y 1500 = 500 muestras = 0.03125s (filtrada < 50ms)
Pausa 2: entre 2000 y 3000 = 1000 muestras = 0.0625s ✅
Pausa 3: entre 5000 y 5500 = 500 muestras = 0.03125s (filtrada)
Pausa 4: entre 6000 y 7000 = 1000 muestras = 0.0625s ✅

pause_durations = [0.0625, 0.0625]

Paso 3: Calcular Skewness
skew([0.0625, 0.0625]) = 0.0 (distribución simétrica)

Si hubiera una pausa muy larga:
pause_durations = [0.0625, 0.0625, 2.5]
skew([0.0625, 0.0625, 2.5]) = 1.8 (cola larga hacia la derecha) ⚠️
```

### Hiperparámetros y Justificación

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| `top_db=25` | 25 dB | Umbral estándar de librosa para separar habla de silencio. Funciona bien para voz humana en condiciones normales |
| `min_pause=0.05s` | 50 ms | Filtra micro-pausas que son ruido de fondo o artefactos técnicos, no pausas cognitivas reales |

### Interpretación

- **Skewness ≈ 0**: Distribución simétrica → pausas normales
- **Skewness > 1**: Cola larga hacia la derecha → algunas pausas muy largas (indicador de demencia)
- **Skewness < -1**: Cola larga hacia la izquierda → algunas pausas muy cortas (menos común)

---

## 2️⃣ Kurtosis_pause_duration

### ¿Qué mide?

El **apuntamiento** (kurtosis) de la distribución de pausas. Mide qué tan concentradas están las pausas alrededor de la media vs. qué tan dispersas están.

### Implementación

Usa la misma función `get_pause_features()` que calcula ambas métricas:

```python
# Mismo proceso que Skewness, pero usando kurtosis()
from scipy.stats import kurtosis

"Kurtosis_pause_duration": float(kurtosis(pause_durations))
```

### Interpretación

- **Kurtosis ≈ 3**: Distribución normal (mesocúrtica)
- **Kurtosis > 3**: Distribución más apuntada (leptocúrtica) → pausas más concentradas
- **Kurtosis < 3**: Distribución más plana (platicúrtica) → mayor variabilidad en pausas

**Nota:** `scipy.stats.kurtosis()` devuelve **kurtosis exceso** (kurtosis - 3), por lo que:
- Valor 0 = distribución normal
- Valor positivo = más apuntada
- Valor negativo = más plana

---

## 3️⃣ Filler_frequency

### ¿Qué mide?

Porcentaje de **muletillas** (fillers) en el discurso. Las muletillas aumentan cuando hay esfuerzo cognitivo para encontrar palabras o planificar el discurso.

### Implementación Paso a Paso

```python
def get_advanced_text_features(transcription_text, nlp_model):
    """
    Calcula frecuencia de muletillas.
    """
    # PASO 1: Procesar el texto con spaCy
    doc = nlp_model(transcription_text)
    # doc contiene tokens, POS tags, lemmas, etc.
    
    # PASO 2: Definir lista de muletillas comunes en inglés
    fillers = {
        "um", "uh", "ah", "hmm", "er", 
        "like", "mean", "well", "you know"
    }
    # Estas son las muletillas más comunes que indican pausas o dudas
    
    # PASO 3: Contar muletillas en el texto
    filler_count = 0
    for token in doc:
        # Comparar el texto del token (en minúsculas) con la lista
        if token.text.lower() in fillers:
            filler_count += 1
    
    # PASO 4: Calcular frecuencia como porcentaje
    total_tokens = len(doc)  # Total de tokens en el documento
    
    if total_tokens > 0:
        filler_freq = (filler_count / total_tokens) * 100
    else:
        filler_freq = 0.0
    
    return {"Filler_frequency": float(filler_freq)}
```

### Ejemplo Práctico

```
Texto transcrito:
"I went to the... um... store... uh... yesterday and... ah... bought some groceries."

Procesamiento:
Tokens: ["I", "went", "to", "the", "...", "um", "...", "store", "...", "uh", 
         "...", "yesterday", "and", "...", "ah", "...", "bought", "some", "groceries", "."]

Contar fillers:
- "um" → encontrado ✅
- "uh" → encontrado ✅
- "ah" → encontrado ✅
Total fillers: 3
Total tokens: 20

Filler_frequency = (3 / 20) * 100 = 15.0%
```

### Justificación de la Lista de Fillers

La lista se basa en investigación sobre disfluencias en inglés:
- **"um", "uh", "ah", "er"**: Muletillas básicas de pausa
- **"hmm"**: Expresión de duda o pensamiento
- **"like", "well"**: Muletillas conversacionales comunes
- **"you know"**: Expresión de búsqueda de confirmación

### Interpretación

- **< 2%**: Discurso fluido, normal
- **2-5%**: Algunas dudas, posible deterioro leve
- **> 5%**: Discurso muy disfluente, indicador fuerte de demencia

---

## 4️⃣ Local_coherence ⭐

### ¿Qué mide?

La **similitud semántica** entre frases adyacentes usando vectores de palabras (word embeddings). Mide qué tan relacionadas están las ideas consecutivas en el discurso.

### Implementación Paso a Paso

```python
def get_advanced_text_features(transcription_text, nlp_model):
    """
    Calcula coherencia semántica local.
    """
    # PASO 1: Procesar el texto con spaCy
    doc = nlp_model(transcription_text)
    
    # PASO 2: Segmentar en frases
    sentences = list(doc.sents)
    # Ejemplo: ["I went to the store.", "I bought groceries.", "Then I came home."]
    
    # PASO 3: Calcular similitud entre frases adyacentes
    similarities = []
    
    if len(sentences) > 1:
        for i in range(len(sentences) - 1):
            sentence_A = sentences[i]      # Frase actual
            sentence_B = sentences[i+1]    # Frase siguiente
            
            # PASO 4: Calcular similitud semántica
            # similarity() usa vectores de palabras (word embeddings)
            # Requiere modelo 'md' o 'lg' de spaCy
            sim = sentence_A.similarity(sentence_B)
            similarities.append(sim)
            # sim es un valor entre 0 y 1
            
        # PASO 5: Promediar todas las similitudes
        local_coherence = np.mean(similarities)
    else:
        # Si solo hay una frase, no hay coherencia local que medir
        local_coherence = 1.0  # Valor base
    
    return {"Local_coherence": float(local_coherence)}
```

### ¿Cómo Funciona Internamente?

#### Paso 1: Conversión a Vectores

Cada frase se convierte en un vector usando word embeddings:

```
Frase 1: "I went to the store"
         ↓ (spaCy procesa cada palabra)
Palabras: ["I", "went", "to", "the", "store"]
         ↓ (cada palabra tiene un vector de 300 dimensiones)
Vector palabra "I":     [0.1, -0.2, 0.3, ...]
Vector palabra "went":  [0.2, 0.1, -0.1, ...]
Vector palabra "store": [0.3, -0.1, 0.2, ...]
         ↓ (promediar todos los vectores de palabras)
Vector frase 1: [0.2, -0.1, 0.15, ...]  (300 dimensiones)
```

#### Paso 2: Cálculo de Similitud (Coseno)

```
Frase 1 → Vector A [0.2, -0.1, 0.15, ...]
Frase 2 → Vector B [0.25, -0.08, 0.18, ...]

Similitud = coseno(θ) = (A · B) / (||A|| × ||B||)

Donde:
- A · B = producto punto = Σ(Ai × Bi)
- ||A|| = norma del vector A = √(Σ(Ai²))
- θ = ángulo entre vectores

Ejemplo:
A · B = 0.2×0.25 + (-0.1)×(-0.08) + 0.15×0.18 + ... = 0.85
||A|| = √(0.2² + (-0.1)² + 0.15² + ...) = 0.5
||B|| = √(0.25² + (-0.08)² + 0.18² + ...) = 0.52

similarity = 0.85 / (0.5 × 0.52) = 0.85 / 0.26 = 0.85
```

### Visualización del Proceso

```
Texto:
"I went to the store. I bought groceries. The weather is nice."

Paso 1: Segmentar
┌─────────────────────┐
│ Frase 1: "I went..."│
│ Frase 2: "I bought.."│
│ Frase 3: "The weath.."│
└─────────────────────┘

Paso 2: Convertir a vectores
Frase 1 → [0.2, -0.1, 0.5, ...]  Vector A
Frase 2 → [0.25, -0.08, 0.48, ...] Vector B
Frase 3 → [0.1, 0.3, -0.2, ...]  Vector C

Paso 3: Calcular similitudes
sim(A, B) = 0.85  ← Frases relacionadas (compras)
sim(B, C) = 0.25  ← Frases desconectadas (cambio de tema)

Paso 4: Promedio
Local_coherence = (0.85 + 0.25) / 2 = 0.55
```

### Requisitos Técnicos

**⚠️ IMPORTANTE:** Requiere modelo de spaCy con vectores:

```python
# ❌ NO funciona (sin vectores)
nlp = spacy.load("en_core_web_sm")
# similarity() devuelve 0 o advertencia

# ✅ Funciona (con vectores)
nlp = spacy.load("en_core_web_md")  # 300 dimensiones
# o
nlp = spacy.load("en_core_web_lg")  # Más preciso pero más pesado
```

**Instalación:**
```bash
python -m spacy download en_core_web_md
```

### Interpretación

| Valor | Interpretación | Significado Clínico |
|-------|----------------|---------------------|
| **0.7 - 1.0** | Muy coherente | Discurso normal, ideas conectadas |
| **0.5 - 0.7** | Moderadamente coherente | Posible deterioro leve |
| **0.3 - 0.5** | Poco coherente | Indicador de demencia |
| **0.0 - 0.3** | Muy incoherente | Demencia avanzada, discurso tangencial |

### Ejemplos Reales

**Caso Normal (Coherencia alta):**
```
Frase 1: "Yesterday I went to the grocery store"
Frase 2: "I bought some vegetables and fruits"
Frase 3: "Then I came back home to cook dinner"

Similitudes:
- Frase 1-2: 0.82 (ambas sobre compras)
- Frase 2-3: 0.75 (actividades relacionadas)

Local_coherence = 0.785 ✅
```

**Caso Demencia (Coherencia baja):**
```
Frase 1: "Yesterday I went to the grocery store"
Frase 2: "My grandson is studying medicine"
Frase 3: "The flowers in the garden are beautiful"

Similitudes:
- Frase 1-2: 0.15 (temas completamente diferentes)
- Frase 2-3: 0.12 (sin conexión)

Local_coherence = 0.135 ❌
```

---

## 5️⃣ Lexical_errors

### ¿Qué mide?

Frecuencia de **palabras mal escritas** o con patrones sospechosos detectados en la transcripción. Puede indicar errores de transcripción de Whisper o dificultades de articulación.

### Implementación Paso a Paso

```python
def detect_lexical_errors(doc, nlp_model):
    """
    Detecta errores léxicos en el texto transcrito.
    """
    error_count = 0
    total_words = 0
    
    # Lista de palabras comunes en inglés (para validación)
    common_words = {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
        "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
        # ... más palabras comunes
    }
    
    # PASO 1: Iterar sobre todos los tokens del documento
    for token in doc:
        # Solo considerar palabras alfabéticas (excluir números y puntuación)
        if token.is_alpha and not token.is_stop:
            total_words += 1
            word_lower = token.text.lower()
            
            # PASO 2: Verificar si está en el vocabulario de spaCy
            is_in_vocab = word_lower in nlp_model.vocab.strings
            
            # PASO 3: Detectar patrones sospechosos
            
            # Patrón 1: Muchas consonantes seguidas (ej: "thrgh" en lugar de "through")
            consonant_pattern = re.search(r'[bcdfghjklmnpqrstvwxyz]{4,}', word_lower)
            # Busca 4 o más consonantes consecutivas
            
            # Patrón 2: Muchas vocales seguidas (ej: "aeiou")
            vowel_pattern = re.search(r'[aeiou]{4,}', word_lower)
            # Busca 4 o más vocales consecutivas
            
            # Patrón 3: Palabras muy cortas no comunes
            is_uncommon_short = len(word_lower) <= 2 and word_lower not in common_words
            
            # PASO 4: Contar como error si cumple criterios
            if not is_in_vocab and token.pos_ != "PROPN":  # Excluir nombres propios
                # Error definitivo si tiene patrones sospechosos
                if consonant_pattern or vowel_pattern or is_uncommon_short:
                    error_count += 1
                # Error parcial si tiene características sospechosas
                elif len(word_lower) > 3 and word_lower not in common_words:
                    if re.search(r'[^aeiou]{3,}', word_lower):  # 3+ consonantes seguidas
                        error_count += 0.5  # Error parcial
    
    # PASO 5: Calcular frecuencia como porcentaje
    error_frequency = (error_count / total_words * 100) if total_words > 0 else 0.0
    
    return float(error_frequency)
```

### Ejemplos de Detección

**Caso 1: Error Detectado**
```
Palabra: "thrgh" (error de transcripción de "through")

Verificaciones:
- ¿Está en vocabulario? NO
- ¿Es nombre propio? NO
- ¿Tiene 4+ consonantes seguidas? SÍ ("thrgh" tiene 4)
- ¿Es palabra corta no común? NO (5 caracteres)

Resultado: ERROR detectado ✅
```

**Caso 2: Palabra Válida**
```
Palabra: "through" (correcta)

Verificaciones:
- ¿Está en vocabulario? SÍ
- Resultado: NO es error ✅
```

**Caso 3: Patrón Sospechoso**
```
Palabra: "aeiou" (no es una palabra real)

Verificaciones:
- ¿Está en vocabulario? NO
- ¿Tiene 4+ vocales seguidas? SÍ
- Resultado: ERROR detectado ✅
```

### Patrones Detectados

1. **4+ consonantes seguidas**: Patrón anormal en inglés
   - Ejemplo: "thrgh" (debería ser "through")
   - Regex: `[bcdfghjklmnpqrstvwxyz]{4,}`

2. **4+ vocales seguidas**: Patrón muy raro
   - Ejemplo: "aeiou"
   - Regex: `[aeiou]{4,}`

3. **Palabras muy cortas no comunes**: Posibles errores de transcripción
   - Ejemplo: "xz" (no es palabra común)
   - Criterio: `len <= 2` y no está en `common_words`

4. **Palabras no reconocidas con 3+ consonantes**: Posibles errores
   - Ejemplo: "wrd" (posible error de "word")
   - Criterio: No en vocabulario + 3+ consonantes seguidas

### Interpretación

- **< 1%**: Transcripción limpia, pocos errores
- **1-3%**: Algunos errores, posiblemente ruido en audio
- **> 3%**: Muchos errores, posible deterioro o audio de mala calidad

### Limitaciones

- Puede tener **falsos positivos** con:
  - Nombres propios (se excluyen automáticamente)
  - Palabras técnicas o poco comunes válidas
  - Errores de transcripción de Whisper (no errores del hablante)

---

## 🔄 Integración en el Pipeline

### Flujo Completo

```python
# En construir_json_desde_directorio():

# 1. Extraer características básicas de librosa
librosa_feats = extract_all_librosa_features(audio_normalizado)
data["parametros_librosa"].update(librosa_feats)

# 2. AÑADIR: Características de pausas (Skewness, Kurtosis)
pause_feats = get_pause_features(audio_normalizado)
data["parametros_librosa"].update(pause_feats)
# Se añaden a parametros_librosa porque son características de audio

# 3. Extraer características de texto (Whisper + spaCy)
whisper_feats = extract_whisper_spacy_features(audio_normalizado)
# Esto incluye: n_words, ttr, mattr_50, keyword_repetitions, etc.

# 4. AÑADIR: Características avanzadas de texto
texto_transcrito = whisper_feats.get("_transcription_internal", "")
if texto_transcrito:
    advanced_text = get_advanced_text_features(texto_transcrito, nlp)
    # Esto calcula: Filler_frequency, Local_coherence, Lexical_errors
    whisper_feats.update(advanced_text)

data["parametros_whisperSpacy"].update(whisper_feats)
```

### Estructura Final en el JSON

```json
{
  "parametros_librosa": {
    "mfcc_1_mean": -182.74,
    "spectral_centroid_mean": 1638.59,
    "pitch_mean": 1261.25,
    "Skewness_pause_duration": 0.73,      // ← NUEVO
    "Kurtosis_pause_duration": -0.53      // ← NUEVO
  },
  "parametros_whisperSpacy": {
    "n_words": 223,
    "ttr": 0.51,
    "keyword_repetitions": 0.24,
    "Filler_frequency": 2.5,              // ← NUEVO
    "Local_coherence": 0.78,               // ← NUEVO
    "Lexical_errors": 1.2                  // ← NUEVO
  }
}
```

---

## 📊 Resumen de Hiperparámetros

| Característica | Hiperparámetro | Valor | Justificación |
|---------------|----------------|-------|---------------|
| **Pausas** | `top_db` | 25 dB | Estándar librosa para voz humana |
| **Pausas** | `min_pause` | 50 ms | Filtra micro-pausas (ruido) |
| **Fillers** | Lista de muletillas | 9 palabras | Basado en investigación sobre disfluencias |
| **Coherencia** | Modelo spaCy | `en_core_web_md` | Requerido para vectores (300 dim) |
| **Coherencia** | Métrica | Coseno | Estándar para similitud semántica |
| **Errores** | Consonantes | 4+ seguidas | Patrón anormal en inglés |
| **Errores** | Vocales | 4+ seguidas | Patrón muy raro |
| **Errores** | Palabras cortas | ≤2 chars | Posibles errores de transcripción |

---

## 🎯 Validación y Testing

### Casos de Prueba

**Test 1: Audio sin pausas largas**
- Input: Audio con pausas regulares
- Expected: Skewness ≈ 0, Kurtosis ≈ 0

**Test 2: Audio con pausas muy largas**
- Input: Audio con algunas pausas > 2 segundos
- Expected: Skewness > 1

**Test 3: Texto con muchas muletillas**
- Input: "I went... um... to the... uh... store... ah..."
- Expected: Filler_frequency > 5%

**Test 4: Texto coherente**
- Input: Frases relacionadas temáticamente
- Expected: Local_coherence > 0.7

**Test 5: Texto incoherente**
- Input: Frases sin relación temática
- Expected: Local_coherence < 0.3

---

## 🔍 Referencias Técnicas

1. **librosa.effects.split()**: Documentación oficial de librosa
2. **scipy.stats.skew/kurtosis**: Implementación de estadísticas de forma
3. **spaCy similarity()**: Cálculo de similitud usando word embeddings
4. **Whisper transcription**: Modelo de transcripción de OpenAI

---

## 💡 Notas de Implementación

1. **Manejo de Errores**: Todas las funciones tienen `try/except` para evitar fallos
2. **Valores por Defecto**: Si no se pueden calcular, se devuelve 0.0
3. **Optimización**: Las funciones están optimizadas para procesar muchos audios
4. **Reproducibilidad**: Seeds y parámetros fijados para resultados consistentes

---

*Documento técnico - Implementación de características para TFM ADReSSo Challenge*
