# Data Augmentation for Audio Features - Castellano

## Descripción General

Este notebook implementa técnicas de **data augmentation** para datos médicos de características de audio. El objetivo principal es generar datos sintéticos que amplíen el conjunto de datos original, mejorando la robustez y el rendimiento de los modelos de clasificación en la detección de demencia.

## Objetivo del Proyecto

Aumentar artificialmente el conjunto de datos mediante técnicas de interpolación basadas en vecinos más cercanos (KNN), generando muestras sintéticas que mantengan las propiedades estadísticas del dataset original para mejorar la predicción de demencia basada en características acústicas.

## Estructura del Notebook

### 1. **Importación de Librerías**
- Ciencia de datos: `pandas`, `numpy`, `scikit-learn`
- Visualización: `seaborn`, `matplotlib`
- Modelado ML: `XGBoost`, `LightGBM`, `sklearn` (múltiples algoritmos)
- Preprocessing: Encoders, Scalers, Imputers

### 2. **Carga y Exploración de Datos**
- Lectura del dataset de características de audio (`audio_features_ivanova_dataset.csv`)
- Análisis descriptivo y detección de características relevantes
- Limpieza inicial: eliminación de columnas no relevantes

### 3. **Clase MedicalDataAugmentor**
Implementación de un augmentador personalizado para datos médicos con:
- **Manejo de valores faltantes** (valores NaN en variables categóricas y numéricas)
- **Encoding** de variables categóricas (`gender`, `label`)
- **Normalización** de variables continuas
- **Generación de muestras sintéticas** mediante:
  - Búsqueda de vecinos más cercanos (KNN)
  - Interpolación lineal con perturbación gaussiana
- **Asignación de labels** basada en similitud con muestras originales

### 4. **Aplicación del Data Augmentor**
- Generación de 2000 muestras sintéticas
- Visualización de resultados iniciales

### 5. **Validación de Datos Aumentados**
Funciones de validación que verifican:
- Estadísticas descriptivas (media, distribuciones)
- Distribuciones de variables categóricas
- Balance de clases
- Comportamiento de modelos

### 6. **Modelado y Evaluación**
Entrenamiento y evaluación de múltiples modelos de clasificación:
- Regresión Logística
- Árboles de Decisión
- Random Forest
- XGBoost
- LightGBM
- SVM (Linear y RBF)
- KNN
- Stacking de Modelos

**Métricas de Evaluación:**
- Accuracy
- Precision, Recall, F1-Score
- Matriz de Confusión
- ROC-AUC
- Validación cruzada

### 7. **Selección y Optimización de Modelos**
- GridSearchCV y RandomizedSearchCV para hiperparametrizacion
- Validación cruzada
- Selección de características (SelectKBest, RFE, SelectFromModel)

### 8. **Análisis de Resultados**
- Comparación de rendimiento entre modelos
- Análisis de características más relevantes
- Visualización de resultados

## Variables Principales

### Variables Categóricas
- `gender`: Género del sujeto
- `label`: Clasificación o etiqueta
- `dementia`: Variable objetivo (Sí/No)

### Variables Continuas
- Características acústicas extraídas del audio (MFCC, pitch, Energy, etc.)

## Instalaciones Requeridas

```bash
# Librerías principales
pandas
numpy
scikit-learn
xgboost
lightgbm
matplotlib
seaborn
scipy

# Instalación opcional (convertir notebook a otros formatos)
pip install nbconvert
```

## Flujo de Ejecución

1. **Preparación**: Carga y limpieza de datos
2. **Aumento**: Generación de datos sintéticos con MedicalDataAugmentor
3. **Validación**: Verificación de calidad de datos generados
4. **Modelado**: Entrenamiento de modelos de clasificación
5. **Optimización**: Búsqueda de hiperparámetros óptimos
6. **Evaluación**: Análisis comparativo de rendimiento

## Consideraciones Importantes

⚠️ **Ruta de Datos**: Actualizar la ruta del archivo CSV según su entorno:
```python
# Línea a modificar:
dt_merge = pd.read_csv("/ruta/correcta/audio_features_ivanova_dataset.csv")
```

⚠️ **Parámetros de Augmentación**:
- `n_neighbors`: Número de vecinos para KNN (por defecto: 5)
- `target_size`: Cantidad de muestras sintéticas a generar (por defecto: 2000)
- Estos valores pueden ajustarse según su dataset

## Metodología de Augmentación

El proceso de generación de datos sintéticos incluye:

1. **Preparación** de datos (encoding, normalización)
2. **Búsqueda de vecinos** más cercanos en el espacio de características
3. **Interpolación** entre puntos para generar nuevas muestras
4. **Perturbación** con ruido gaussiano pequeño (σ = 0.01)
5. **Reversión de transformaciones** a escala original
6. **Asignación inteligente de labels** basada en similitud

## Salidas Esperadas

- Dataset sintético aumentado con configuración balanceada
- Modelos entrenados con métricas de rendimiento
- Reportes de validación de calidad de datos
- Análisis de importancia de características

## Autor

Proyecto TFM - Trabajo Final de Máster

## Licencia

Este código es parte de un proyecto académico y su uso debe estar alineado con los términos de la institución.

---

**Nota**: Este notebook está optimizado para procesamiento de datos médicos de audio. Se recomienda revisar y ajustar el tamaño de las muestras sintéticas según los recursos computacionales disponibles.
