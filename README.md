# TFM_Process: Procesamiento de Audio y Modelado para la Detección de Deterioro Cognitivo

Este repositorio contiene el código fuente, notebooks y scripts desarrollados como parte de un Trabajo de Fin de Máster (TFM) enfocado en el análisis de voz y lenguaje de cara a la detección de enfermedades neurodegenerativas o deterioro cognitivo (como la demencia o el Alzheimer). 

Mediante pipelines de procesamiento de audio y de Inteligencia Artificial (Speech-to-Text y NLP), el repositorio procesa bases de datos clínicas (tales como ADReSSo21/DementiaBank, BioHermes e Ivanova Dataset) para extraer cientos de biomarcadores (acústicos, espectrales, prosódicos y lingüísticos) e introducirlos a modelos predictivos de Machine Learning y Deep Learning. 

## 📂 Contenido del Repositorio

### Scripts de Extracción y Preprocesamiento
* **`single_audio_pipeline.py`**: Es el flujo de datos integral para procesar un solo archivo de audio a la vez. Estandariza la señal, calcula el RMS, identifica las pausas y segmentos audibles, procesa variables de OpenSMILE y Librosa, extrae la transcripción usando `Whisper` y calcula características discursivas con `spaCy`. Devuelve y guarda un archivo JSON limpio con todas estas variables combinadas.
* **`Process_Parametros_.py`**: Script de procesamiento masivo y por lotes que recorre directorios completos (diseñado inicialmente para el conjunto ADReSSo21/DementiaBank). Mide la calidad del audio (clipping, durabilidad o RMS), descarta los audios deficientes, los normaliza y genera un fichero `.json` global con los resultados integrados de las transcripciones y extracciones acústicas.
* **`preprocess_v1.py`**: Agrupa funciones principales para el Análisis Exploratorio de Datos (EDA) e Imputación de valores faltantes (numéricos y categóricos). Incluye herramientas para generar gráficos estadísticos como histogramas o diagrama de cajas.

### Análisis, Modelado de Datos y Gráficos (Jupyter Notebooks)
* **`Analysis_tfm_v1.ipynb`** y **`Analysis_tfm_NN.ipynb`**: Cuadernos principales dedicados a la construcción y evaluación de modelos analíticos (CatBoost / Redes Neuronales). Incluyen validaciones cruzadas, exploración de las características predictivas más importantes y rendimiento general en la fase de test.
* **`model_pca.ipynb`**: Análisis de Componentes Principales (PCA) enfocado en reducir la dimensionalidad de los múltiples vectores extraídos y evaluar la varianza explicada.
* **`data_augmentation.ipynb`**: Cuaderno dedicado al aumento de datos (Data Augmentation) utilizando métodos probabilísticos (Cópulas o Modelos de Mezcla Gaussiana GMM) para lidiar con el desbalance de clases clínico o con la falta de instancias.
* **`tfm_merge_var.ipynb`**, **`demential_dataset.ipynb`** o **`analysis_biohermes.ipynb`**: Se encargan de la estructuración global de los datasets (limpieza, cruces entre tablas y exploración específica para bancos de datos individuales).

### Datos y Resultados
Se incluyen varios archivos tabulares de tipo `.csv` (`audio_features_ivanova_dataset.csv`, `bio_hermes_summary.csv` y archivos como `data_aumentada.csv` o `datos_synteticos_gmm.csv`) que contienen matrices resultantes de la extracción del audio o la generación que alimentarán a los modelos. También se almacena metadata en el directorio `catboost_info` originada a partir de entrenamientos.

## 🛠️ Librerías Utilizadas y Tecnologías

El pipeline está fundamentado en grandes módulos del ecosistema Python:

### 1. Procesamiento Acústico y Audio
* **`librosa`**: Usada para extraer duraciones de silencios, ratios de voz, métricas en el dominio del tiempo (RMS, Zero-Crossing Rate), F0/Pitch, y coeficientes Mel (MFCCs y deltas).
* **`opensmile` / `smile`**: Ejecuta los perfiles probados y validados científicamente `eGeMAPSv02` (y en algunas ocasiones `ComParE_2016`) para extraer medias, varianzas, asimetrías o percentiles de variables paralingüísticas avanzadas (shimmer, jitter, spectral slope). 
* **`soundfile`**: Para lecturas, formateo y guardado rápido y fiel de archivos estandarizados en `.wav`. 
* **`imageio_ffmpeg` / `ffmpeg`**: Elemento base y vital para decodificar diferentes extensiones de audio antes de su consumo por otras utilidades.

### 2. Reconocimiento de Voz (ASR) y Lenguaje Natural (NLP)
* **`whisper` (OpenAI)**: Transcripción automática y detección de las palabras con "timestamps" para localizar duraciones y ratios de pausas en alta precisión.
* **`spacy` (`en_core_web_sm`, `en_core_web_lg`)**: Herramienta de Modelado de Lenguaje. Realiza "Sentencizer" o "POS tagging" (reconocimiento verbal, adverbios, pronombres...) lo cual permite generar un ratio sobre palabras clave, encontrar repeticiones y rastrear biomarcadores de discurso lento u olvidadizo.
* **`textstat`**: Evalúa métricas numéricas del texto como la legibilidad `Flesch-Kincaid`.
* **`wordfreq`**: Identifica frecuencias y rareza en las palabras pronunciadas comparándolas en el lenguaje de uso común (`lexical_error_rate_oov`).

### 3. Machine Learning y Flujo de Trabajo
* **`catboost`**: Principal librería de modelado; implementa modelos de agrupamiento basado en gradiente de árboles ("Gradient Boosting Trees"), muy rápida y que soporta predictores categóricos de forma nativa. 
* **`scikit-learn`** (en los notebooks): Componentes principales, divisiones conjuntas y métricas.
* **`pandas` y `numpy`**: Tratamiento avanzado para la tabla combinada con todos los vectores extraídos mediante OpenSmile+Librosa y limpieza posterior.
* **`scipy`**: Análisis estadístico puro (como la evaluación de asimetría o curtosis en las curvas de duración silenciosa).
* **`seaborn` y `matplotlib`**: Implementación de gráficos estadísticos EDA que evalúan la calidad de las instancias recolectadas (curvas ROC, Feature Importances, correlaciones).
