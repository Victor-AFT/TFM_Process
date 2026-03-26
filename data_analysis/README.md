# Data Analysis

Este directorio contiene el análisis exploratorio de datos (EDA) para el proyecto de Trabajo Fin de Máster (TFM) enfocado en la detección de demencia usando características de audio.

## Contenido

### `data_analysis.ipynb`
Notebook Jupyter con el análisis completo de los datos del dataset de Ivanova. El análisis incluye:

#### 1. **Carga y Preparación de Datos**
   - Importación del dataset de características de audio
   - Revisión inicial de estructura y esquemas

#### 2. **Análisis General**
   - Información sobre variables (tipos de datos, valores no nulos)
   - Estadísticas descriptivas
   - Distribución de las variables

#### 3. **Análisis de Variables Clave**
   - **Variable Dependiente (Demencia)**: Clasificación en 3 categorías
     - 0: Sin síntomas de demencia
     - 1: Síntomas de demencia
     - 2: Síntomas de demencia (nivel avanzado)
     - El dataset presenta un balance natural entre clases
   
   - **Edad**: Rango de 54-82 años con concentraciones en ciertos rangos
   - **Años de Escolaridad**: Predominio de 8 años de educación (>40% de la población)

#### 4. **Valores Perdidos**
   - Análisis de valores faltantes en las variables
   - Variables afectadas: `mmse_df_info`, `schooling_years`, `local_coherence_bigram`
   - Cálculo de porcentajes de pérdida para aplicar imputación

#### 5. **Detección de Outliers**
   - Métodos de detección basados en rango intercuartílico (IQR)
   - Identificación de anomalías en variables numéricas

#### 6. **Visualizaciones**
   - Gráficos de distribución (pie charts, bar plots)
   - Análisis gráfico de patrones en los datos

## Requisitos

Para ejecutar el notebook necesita:

- Python 3.x
- pandas
- numpy
- seaborn
- matplotlib

## Notas Importantes

- El dataset presenta un balance natural de clases, lo que evita la necesidad de balanceo equilibrar los datos
- El análisis está orientado a la preparación de datos para modelos de Machine Learning
- Los valores perdidos requieren imputación tras este análisis exploratorio

## Estructura del Proyecto TFM

```
TFM_Process-main/
├── data_analysis/          ← Estás aquí
│   ├── data_analysis.ipynb
│   └── README.md
└── [otros directorios del proyecto]
```
