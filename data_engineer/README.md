# 🧠 TFM: Detección de Demencia mediante Análisis de Voz

**Proyecto ADReSSo Challenge - Master en Big Data e Inteligencia Artificial**

## 📋 Descripción del Proyecto

Este proyecto implementa un sistema completo de extracción y análisis de características acústicas y lingüísticas a partir de audios de habla espontánea para la detección temprana de demencia. El sistema procesa archivos de audio, extrae múltiples tipos de características (acústicas, prosódicas y lingüísticas) y genera un dataset estructurado listo para entrenar modelos de machine learning.

---

## 🎯 Objetivos

1. **Extraer características multimodales** de audios de habla espontánea
2. **Implementar características específicas** para detección de demencia:
   - Distribución de pausas (Skewness, Kurtosis)
   - Frecuencia de muletillas (Fillers)
   - Coherencia semántica local
   - Errores léxicos
3. **Optimizar el conjunto de características** para evitar overfitting
4. **Generar dataset estructurado** para análisis y modelado

---

## 🏗️ Arquitectura del Sistema

### Arquitectura Medallion (AWS)

> 📐 **[Ver diagrama interactivo de la Arquitectura Medallion](docs/arquitectura_medallion.drawio)**
>
> El diagrama muestra el flujo completo del pipeline: **Ingesta & Bronze** (archivos raw + normalización) → **Silver** (extracción de features con Librosa, OpenSMILE, Whisper y spaCy) → **Gold** (datos ML-ready para entrenar modelos).
>
> *Haz clic en el enlace para ver el diagrama renderizado en GitHub, o ábrelo con [draw.io](https://app.diagrams.net/) para editarlo.*

#### Flujo resumido

```
Audio Original (.wav)
    ↓
[1] Normalización (RMS, calidad)
    ↓
[2] Extracción de Features
    ├── Librosa (MFCCs, espectrales, pitch, jitter, shimmer)
    ├── OpenSMILE eGeMAPSv02 (88 características clínicas)
    └── Whisper + spaCy (transcripción + análisis lingüístico)
    ↓
[3] Características Avanzadas
    ├── Skewness/Kurtosis de pausas
    ├── Filler frequency
    ├── Local coherence
    └── Lexical errors
    ↓
JSON Estructurado → Análisis → Modelos ML
```

---

## 📁 Estructura del Proyecto

```
TFM/
├── scripts/                      # Scripts de procesamiento y análisis
│   ├── Process_Parametros_.py   # ⭐ Script principal de extracción
│   ├── 01_EDA_basico.py         # Análisis exploratorio de datos
│   └── 02_train_basic_models.py # Entrenamiento de modelos ML
│
├── output_data/                  # ✅ TODOS LOS OUTPUTS
│   ├── ADReSSo21_latest.json    # JSON principal (última versión)
│   ├── ADReSSo21_*.json         # Versiones históricas
│   ├── figures/                 # Gráficos y visualizaciones
│   ├── reports/                 # Reportes de análisis
│   └── processed_data/          # Datos procesados (CSV)
│
├── TAILBANK/                     # Audios originales
├── dementibank_normalizado/      # Audios normalizados
│
├── static/                       # Documentación del proyecto
│   └── project_information/
│
└── docs/                         # Documentación técnica
    ├── CARACTERISTICAS.md        # Características implementadas
    └── GUIA_USO.md               # Guía de uso del sistema
```

---

## 🚀 Inicio Rápido

### 1. Instalación de Dependencias

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_md  # Para Local_coherence
```

### 2. Procesar Audios

```bash
python scripts/Process_Parametros_.py
```

Esto generará:
- Audios normalizados en `dementibank_normalizado/`
- JSON con características en `output_data/ADReSSo21_latest.json`

### 3. Análisis Exploratorio

```bash
python scripts/01_EDA_basico.py
```

Genera visualizaciones y reportes en `output_data/`

### 4. Entrenar Modelos

```bash
python scripts/02_train_basic_models.py
```

---

## 🎯 Características Implementadas

### Características Nuevas (Específicas para Demencia)

| Característica | Tipo | Descripción |
|---------------|------|-------------|
| `Skewness_pause_duration` | Audio | Asimetría de la distribución de pausas |
| `Kurtosis_pause_duration` | Audio | Apuntamiento de la distribución de pausas |
| `Filler_frequency` | Texto | Frecuencia de muletillas (um, uh, er...) |
| `Local_coherence` | Texto | Coherencia semántica entre frases adyacentes |
| `Lexical_errors` | Texto | Frecuencia de errores léxicos |

### Características Estándar

- **Librosa** (~30 features): MFCCs, características espectrales, pitch, jitter, shimmer, HNR
- **OpenSMILE eGeMAPSv02** (88 features): Conjunto estándar para análisis clínico
- **Whisper/spaCy** (~12 features): Métricas de texto, TTR, MATTR, ratios POS

**Total: ~135 características esenciales** (optimizado desde ~6536)

---

## 📊 Pipeline de Procesamiento

### Paso 1: Normalización de Audio
- Normalización RMS (energía)
- Evaluación de calidad
- Guardado en `dementibank_normalizado/`

### Paso 2: Extracción de Características
- **Acústicas** (Librosa): MFCCs, espectrales, pitch, calidad vocal
- **Prosódicas** (OpenSMILE): eGeMAPSv02 (88 características)
- **Lingüísticas** (Whisper + spaCy): Transcripción + análisis NLP

### Paso 3: Características Avanzadas
- Detección de pausas y cálculo de estadísticas
- Análisis de muletillas y coherencia semántica
- Detección de errores léxicos

### Paso 4: Generación de JSON
- Estructuración de todos los datos
- Guardado en `output_data/ADReSSo21_latest.json`

---

## 📈 Resultados y Outputs

Todos los resultados se guardan en `output_data/`:

- **JSON Principal**: `ADReSSo21_latest.json` - Dataset completo
- **Figuras**: `figures/` - Visualizaciones del EDA
- **Reportes**: `reports/` - Análisis estadísticos y resúmenes
- **Datos Procesados**: `processed_data/` - CSVs para análisis

---

## 🔧 Configuración

### Hiperparámetros Principales

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `top_db` | 25 dB | Umbral para detección de pausas |
| `min_pause` | 50 ms | Filtro de micro-pausas |
| Modelo spaCy | `en_core_web_md` | Requerido para Local_coherence |
| Ventana MATTR | 50 palabras | Tamaño de ventana para diversidad léxica |

### Características Opcionales

Las características menos esenciales están **comentadas** en el código con `# ⚠️ OPCIONAL:`. Para activarlas:
1. Abre `scripts/Process_Parametros_.py`
2. Busca `# ⚠️ OPCIONAL:`
3. Descomenta las líneas correspondientes

Ver `docs/CARACTERISTICAS.md` para más detalles.

---

## 📚 Documentación

Toda la documentación técnica está organizada en `docs/`:

- **[docs/IMPLEMENTACION_NUEVAS_FEATURES.md](docs/IMPLEMENTACION_NUEVAS_FEATURES.md)** ⭐ - **Cómo se implementaron las 5 nuevas características** (paso a paso)
- **[docs/arquitectura_medallion.drawio](docs/arquitectura_medallion.drawio)** 📐 - **Diagrama de la Arquitectura Medallion** (AWS S3 + Lambda + SageMaker)
- **[docs/CARACTERISTICAS.md](docs/CARACTERISTICAS.md)** - Documentación completa de todas las características
- **[docs/GUIA_USO.md](docs/GUIA_USO.md)** - Guía detallada de uso y próximos pasos
- **[docs/ESTRUCTURA_PROYECTO.md](docs/ESTRUCTURA_PROYECTO.md)** - Estructura y organización del proyecto

---

## 🛠️ Tecnologías Utilizadas

- **Python 3.x**
- **librosa** - Procesamiento de audio
- **OpenSMILE** - Extracción de características acústicas
- **Whisper** - Transcripción de audio a texto
- **spaCy** - Procesamiento de lenguaje natural
- **scikit-learn** - Machine learning
- **pandas/numpy** - Manipulación de datos
- **matplotlib/seaborn** - Visualización

---

## 📝 Requisitos

Ver `requirements.txt` para la lista completa de dependencias.

**Dependencias principales:**
- librosa
- opensmile-python
- openai-whisper
- spacy
- scikit-learn
- pandas
- numpy
- matplotlib
- seaborn

---

## 🎓 Uso para TFM

Este proyecto implementa:

1. ✅ **Extracción de características multimodales** (audio + texto)
2. ✅ **Características específicas para demencia** (5 nuevas)
3. ✅ **Optimización de features** (reducción del 98%)
4. ✅ **Pipeline completo** de procesamiento
5. ✅ **Análisis exploratorio** automatizado
6. ✅ **Preparación para ML** (dataset estructurado)

**Próximos pasos sugeridos:**
- Entrenar modelos de clasificación
- Análisis de importancia de características
- Validación cruzada
- Comparación de modelos

---

## 📄 Licencia

Proyecto académico - TFM Master en Big Data e Inteligencia Artificial

---

## 👥 Autor

Proyecto desarrollado para el TFM del Master en Big Data e Inteligencia Artificial

---

## 📞 Contacto y Soporte

Para preguntas sobre el proyecto, consulta la documentación en `docs/` o revisa los comentarios en el código.

---

*Última actualización: Marzo 2026*
