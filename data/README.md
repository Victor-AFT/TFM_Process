# Carpeta de Datos / Data Folder

Este directorio contiene los datos utilizados en el proyecto de análisis de características de audio y lingüísticas para la detección de demencia siguiendo una arquitectura de medallón de datos.

## Estructura de Carpetas

### 📁 `bronze/`
**Datos Raw / Datos Originales**

Contiene los datasets en su estado más próximo al original antes de procesamiento significativo.

- **`audio_features_ivanova_dataset.csv`**: Dataset tabulado basado en el dataset de Ivanova con características de audio y lingüísticas extraídas de muestras de habla para individuos con y sin demencia.
  - **Contenido**: Más de 50 características incluyendo:
    - Metadatos: `sujeto`, `audio_file`, `dementia`, `label`, `gender`, `age`
    - Características lingüísticas: `total_words`, `sentence_length_mean`, `type_token_ratio`, `noun_ratio`, `mean_word_length`, etc.
    - Características de audio: `f0_mean`, `f0_std`, `loudness_mean`, `jitter_local`, `shimmer_local`, `hnr`, etc.
    - Métricas clínicas: `mmse_df_info`, `schooling_years`
  - **Objetivo**: Clasificación binaria de demencia (AD vs. control)

### 📁 `silver/`
**Datos Procesados / Datos Aumentados**

Contiene datasets que han sido procesados, transformados o aumentados para su uso en modelos de machine learning.

- **`data_aumentada_castellano.csv`**: Versión procesada y aumentada del dataset en castellano.
  - **Características principales**:
    - Datos preparados para modelos (sin valores faltantes críticos)
    - Características normalizadas/estandarizadas donde corresponda
    - Datos aumentados para mejorar el balance y la representatividad
    - Compatible con pipelines de ML estándar
  - **Uso recomendado**: Entrenamiento y validación de modelos

## Nomenclatura

- **Bronze**: Capa de datos raw sin procesamiento
- **Silver**: Capa de datos limpios, procesados y listos para análisis
- **Gold** (si aplica): Capa de datos agregados y finales para reportes

## Notas Importantes

- Los datos contienen información sensible de pacientes (edad, género, métricas cognitivas)
- Asegurar cumplimiento de regulaciones de privacidad (GDPR, HIPAA) al manipular estos datos
- Las características de audio fueron extraídas de archivos `.wav` usando análisis acústico propietario
- El balance de clases debe considerarse en el entrenamiento de modelos

## Contacto

Para preguntas sobre el origen o procesamiento de estos datos, consultar la documentación de proyecto correspondiente.
