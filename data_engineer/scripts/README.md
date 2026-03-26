# 📊 Scripts de Ingeniería de Datos - TFM ADReSSo Challenge

Conjunto de scripts Python para procesamiento, análisis y modelado de datos acústicos y lingüísticos del dataset **ADReSSo21** (Alzheimer's Dementia Recognition through Spontaneous Speech).

---

## 📋 Índice de Scripts

| Script | Descripción | Tipo |
|--------|-------------|------|
| `01_EDA_basico.py` | Análisis Exploratorio de Datos (EDA) | Exploración |
| `02_train_basic_models.py` | Entrenamiento de modelos ML | Machine Learning |
| `analisis_json.py` | Análisis del JSON de idioma y texto | Análisis |
| `Process_OpenSmile_DE.py` | Procesamiento y normalización de audio | Procesamiento |
| `Process_Parametros_.py` | Extracción de características acústicas avanzadas | Procesamiento |
| `recopila_info_json_ADReSSo21.py` | Recopilación de información del dataset | Integración |
| `single_audio_pipeline.py` | Pipeline completo de procesamiento de audio individual | Procesamiento |

---

## 🔍 Descripción Detallada de Scripts

### 1️⃣ `01_EDA_basico.py`
**Análisis Exploratorio de Datos (EDA) básico**

**Propósito:** Comprender los datos antes de entrenar modelos de Machine Learning.

**Funcionalidades principales:**
- Carga automática de JSON (`ADReSSo21.json` o más reciente con timestamp)
- Creación de reportes estadísticos
- Visualización de distribuciones de variables
- Generación de figuras de análisis
- Identificación de valores faltantes y outliers

**Outputs:**
- `output_data/figures/` - Gráficos de análisis
- `output_data/reports/` - Reportes estadísticos
- `output_data/processed_data/` - Datos procesados

**Dependencias:**
- pandas, matplotlib, seaborn, numpy
- pathlib, datetime

---

### 2️⃣ `02_train_basic_models.py`
**Entrenamiento de Modelos Básicos de Machine Learning**

**Propósito:** Crear y entrenar modelos predictivos usando datos procesados.

**Características:**
- Carga y preparación automática de datos desde JSON
- Selección inteligente de características (features)
- Filtrado de columnas con valores faltantes (>50%)
- Exclusión de columnas no numéricas y metadatos

**Modelos implementados:**
- Random Forest
- Gradient Boosting
- Support Vector Machine (SVM)
- Regresión Logística

**Métricas y validación:**
- Cross-validation
- Classification Report
- Confusion Matrix
- ROC-AUC Score
- ROC Curves

**Inputs esperados:**
- `ADReSSo21.json` con datos procesados

**Dependencias:**
- scikit-learn, pandas, numpy, matplotlib, seaborn, joblib

---

### 3️⃣ `analisis_json.py`
**Análisis Completo del JSON de Identificación de Idioma y Texto**

**Propósito:** Analizar detalladamente el archivo JSON `Identificacion_Idioma_y_Texto.json` del dataset ADReSSo21.

**Análisis realizados:**
- Metadatos globales (modelo Whisper, directorio de entrada, total de audios)
- Distribución de idiomas detectados
- Identificación de audios en idiomas no ingleses
- Estadísticas de transcripción
- Procesamiento y análisis de texto

**Outputs:**
- Reporte completo en consola con visualización de datos

**Inputs esperados:**
- Ruta: `C:\Users\vfuen\Documents\Master_VS\TFM\Identificacion_Idioma_y_Texto.json`

**Dependencias:**
- json, statistics, collections, os

---

### 4️⃣ `Process_OpenSmile_DE.py`
**Procesamiento y Normalización de Audio**

**Propósito:** Procesar audios del dataset y asignar puntuaciones de calidad.

**Funcionalidades principales:**

**Puntuación de Calidad de Audio:**
- 1. **RMS (Root Mean Square)**: Detecta volumen muy bajo o saturado
  - Rango saludable: 0.05 - 0.15
  - Penalización: -30 puntos si está fuera de rango
  
- 2. **Clipping Detection**: Detecta saturación digital (distorsión)
  - Verifica si la señal alcanza ±1.0
  - Penalización: -40 puntos (muy crítico para jitter y shimmer)

- 3. **Duración útil**: Audios demasiado cortos no permiten estimaciones estables
  - Penalización basada en duración insuficiente

**Directorios:**
- Entrada: `Repo_Demential/`, `Repo_Nodemential/`
- Salida normalizada: `Repo_Demential_Normalizado/`

**Outputs:**
- Audios normalizados
- Puntuaciones de calidad por audio

**Dependencias:**
- librosa, soundfile, opensmile, pandas, numpy, pathlib, uuid, json

---

### 5️⃣ `Process_Parametros_.py`
**Extracción de Características Acústicas Avanzadas**

**Propósito:** Pipeline completo para extraer características lingüísticas y acústicas de audios individuales.

**Módulos principales:**

**1. Características Acústicas (OpenSMILE):**
- Análisis de frecuencia y energía
- Jitter, Shimmer, HNR (Harmonics-to-Noise Ratio)
- MFCC (Mel-Frequency Cepstral Coefficients)
- Spectral descriptors

**2. Características Lingüísticas (Whisper + spaCy):**
- Transcripción de audio a texto con Whisper (modelo "base")
- Análisis lingüístico con spaCy
- Extracción de entidades nombradas (NER)
- Análisis sintáctico y de dependencias

**3. Características de Texto:**
- Legibilidad (Flesch Reading Ease)
- Complejidad lexical
- Diversity de vocabulario
- Errores lingüísticos

**Manejo de Modelos:**
- Intento automático de cargar `en_core_web_md` (más completo)
- Fallback a `en_core_web_sm` si no está disponible
- Descarga automática si es posible

**Outputs:**
- DataFrame con todas las características extraídas
- JSON con información detallada
- Archivo CSV con características por audio

**Dependencias principales:**
- librosa, soundfile, opensmile, pandas, numpy
- spacy, whisper, scipy, pathlib

---

### 6️⃣ `recopila_info_json_ADReSSo21.py`
**Recopilación de Información del Dataset ADReSSo21**

**Propósito:** Construir dataset integrado desde archivos CSV y audios del directorio ADReSSo21.

**Funcionalidades:**

**1. Búsqueda de Audios:**
- Función `find_audio()` para localizar audios por ID
- Soporta múltiples formatos: .wav, .mp3, .flac
- Permite filtrar por palabras clave en la ruta (ej: "normalizado")

**2. Construcción de Dataset:**
- Lee archivos CSV con metadatos de audios
- Clasifica audios como "decline" o "no_decline"
- Busca versiones normalizadas y sin normalizar
- Integra información de audios con metadatos

**3. Organización:**
- Estructura jerárquica del directorio ADReSSo21
- Soporte para audios normalizados y sin normalizar
- Manejo robusto de errores en lectura de CSV

**Outputs:**
- Dataset dictionary con estructura:
  ```python
  {
    "audio_id": {
      "label": "decline/no_decline",
      "audio_path": "...",
      "audio_normalized": "...",
      "metadata": {...}
    }
  }
  ```

**Dependencias:**
- os, json, pandas, pathlib

---

### 7️⃣ `single_audio_pipeline.py`
**Pipeline Completo de Procesamiento de Audio Individual**

**Propósito:** Pipeline integral que procesa un audio individual y extrae todas sus características (acústicas y lingüísticas).

**Configuración Automática:**
- Setup automático de **FFmpeg** para Whisper
  - Detecta ejecutable de FFmpeg mediante `imageio_ffmpeg`
  - Crea alias con nombre correcto (`ffmpeg.exe`)
  - Configura PATH del sistema automáticamente

**Modelos Cargados:**
- **Whisper**: Modelo "medium" para transcripción
- **spaCy**: Modelo "en_core_web_lg" para análisis lingüístico
- **OpenSMILE**: Para extracción de características acústicas

**Características Extraídas:**

**Acústicas:**
- MFCCs (Mel-Frequency Cepstral Coefficients)
- Spectral features (centroid, rolloff, bandwidth)
- Temporal features (RMS, zero crossing rate)
- Pitch y formantes

**Lingüísticas:**
- Transcripción completa del audio
- Análisis de sentimiento
- Entidades nombradas
- Análisis sintáctico
- Métricas de legibilidad
- Complejidad lexical
- Frecuencias de palabras

**Procesamiento:**
- Manejo robusto de audios con diferentes formatos
- Normalización de audio
- Segmentación y análisis en ventanas
- Interpolación de características sobre frames

**Warnings Suprimidos:**
- "FP16 is not supported on CPU" (común en sistemas sin GPU)

**Outputs:**
- JSON con todas las características
- CSV para análisis posterior
- Metadatos del audio

**Dependencias principales:**
- librosa, soundfile, opensmile, pandas, numpy
- spacy, whisper, textstat, scipy
- wordfreq, imageio_ffmpeg, tempfile, shutil

---

## 🚀 Flujo de Trabajo Recomendado

```
1. Recopilar datos (recopila_info_json_ADReSSo21.py)
   ↓
2. Procesar audios individuales (single_audio_pipeline.py o Process_Parametros_.py)
   ↓
3. Normalizar audios (Process_OpenSmile_DE.py)
   ↓
4. Análisis exploratorio (01_EDA_basico.py)
   ↓
5. Entrenar modelos (02_train_basic_models.py)
```

---

## 📦 Requisitos Principales

### Python Packages
```bash
pip install librosa soundfile opensmile pandas numpy scikit-learn
pip install matplotlib seaborn
pip install spacy whisper
pip install textstat wordfreq
pip install scipy imageio-ffmpeg
```

### Modelos de NLP (spaCy)
```bash
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_md   # Recomendado
python -m spacy download en_core_web_lg   # Para pipeline completo
```

### FFmpeg
Para Whisper, se requiere FFmpeg:
- **Windows**: Instalación automática via `imageio_ffmpeg`
- **Linux/Mac**: `sudo apt-get install ffmpeg` o equivalente

---

## 📁 Estructura de Directorios Esperada

```
TFM_Process/
├── scripts/
│   ├── 01_EDA_basico.py
│   ├── 02_train_basic_models.py
│   ├── analisis_json.py
│   ├── Process_OpenSmile_DE.py
│   ├── Process_Parametros_.py
│   ├── recopila_info_json_ADReSSo21.py
│   ├── single_audio_pipeline.py
│   └── README.md
├── data/
│   └── [archivos de entrada]
├── output_data/
│   ├── processed_data/
│   ├── figures/
│   ├── reports/
│   └── models/
└── ADReSSo21/
    ├── audio/
    ├── decline/
    └── no_decline/
```

---

## ⚙️ Configuración y Uso

### Variables de Entorno y Rutas
Los scripts utilizan `Path(__file__).parent` para configurar rutas automáticamente, lo que permite:
- Ejecutarlos desde cualquier directorio
- Mantener compatibilidad entre sistemas (Windows, Linux, Mac)
- Evitar hardcoding de rutas

### Ejemplo de Uso Básico

```python
# 1. Análisis exploratorio
python 01_EDA_basico.py

# 2. Procesar archivos JSON
python analisis_json.py

# 3. Entrenar modelos
python 02_train_basic_models.py
```

---

## 🔧 Características Especiales

### ✅ Robustez
- Manejo automático de rutas relativas/absolutas
- Creación automática de directorios
- Fallback automático para modelos de spaCy
- Supresión inteligente de warnings

### ✅ Compatibilidad
- Soporte multi-plataforma (Windows, Linux, Mac)
- Detección automática de FFmpeg
- Soporte para múltiples formatos de audio

### ✅ Estabilidad
- Manejo robusto de excepciones
- Validación de datos
- Filtrado automático de características inválidas (NaN, >50% missing)

---

## 📝 Notas Importantes

1. **Dataset ADReSSo21**: Los scripts están diseñados para el dataset de Alzheimer's Dementia Recognition
2. **Modelos Pre-entrenados**: Requieren descargas iniciales (Whisper, spaCy)
3. **GPU Optional**: Pueden ejecutarse en CPU, pero GPUs aceleran significativamente
4. **Memoria**: Los modelos de IA (Whisper, spaCy-lg) requieren 4-8 GB de RAM

---

## 👥 Autor
**TFM ADReSSo Challenge** - Trabajo Fin de Máster

---

## 📚 Referencias
- ADReSSo21 Challenge: Alzheimer's Dementia Recognition through Spontaneous Speech
- OpenSMILE: Eyben, F., Wöllmer, M., & Schuller, B. (2010)
- Whisper: Radford, A., et al. (2022)
- spaCy: NLP library for Python