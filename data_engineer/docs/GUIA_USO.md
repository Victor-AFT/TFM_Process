# 🚀 Próximos Pasos con los Datos Procesados

Ahora que tienes el JSON con todas las características extraídas, aquí tienes un roadmap completo de qué puedes hacer:

---

## 📊 1. Análisis Exploratorio de Datos (EDA)

### Objetivo: Entender tus datos antes de modelar

**Script sugerido:** `01_EDA.py`

```python
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Cargar datos
with open('ADReSSo21.json', 'r') as f:
    data = json.load(f)

# Convertir a DataFrame
df = pd.json_normalize(data)

# Análisis básico
print("=== RESUMEN DEL DATASET ===")
print(f"Total de audios: {len(df)}")
print(f"Con demencia: {df['dementia'].value_counts()}")
print(f"Calidad de audios: {df['calidad'].value_counts()}")

# Estadísticas descriptivas
print("\n=== ESTADÍSTICAS DESCRIPTIVAS ===")
print(df.describe())

# Visualizaciones
# 1. Distribución de clases
plt.figure(figsize=(10, 6))
df['dementia'].value_counts().plot(kind='bar')
plt.title('Distribución de Clases')
plt.show()

# 2. Correlación entre características nuevas y demencia
new_features = ['Skewness_pause_duration', 'Kurtosis_pause_duration', 
                'Filler_frequency', 'Local_coherence', 'Lexical_errors']
# ... más código
```

**Qué descubrirás:**
- ✅ Balance de clases (¿hay suficientes ejemplos de cada tipo?)
- ✅ Valores faltantes o anómalos
- ✅ Distribuciones de las características
- ✅ Correlaciones entre features y la variable objetivo

---

## 🔍 2. Feature Engineering y Selección

### Objetivo: Optimizar las características para el modelo

**Script sugerido:** `02_feature_selection.py`

```python
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.preprocessing import StandardScaler
import pandas as pd

# Preparar datos
X = df.drop(['dementia', 'uuid', 'audio', 'name'], axis=1)
y = df['dementia'].map({'dementia': 1, 'nodementia': 0})

# Selección de características más importantes
selector = SelectKBest(f_classif, k=50)  # Top 50 características
X_selected = selector.fit_transform(X, y)

# Ver qué características fueron seleccionadas
selected_features = X.columns[selector.get_support()]
print("Características más importantes:")
print(selected_features)
```

**Qué hacer:**
- ✅ Normalizar/escalar características
- ✅ Seleccionar las features más relevantes
- ✅ Crear nuevas features derivadas si es necesario
- ✅ Manejar valores faltantes

---

## 🤖 3. Entrenamiento de Modelos de Machine Learning

### Objetivo: Crear modelos predictivos

**Script sugerido:** `03_train_models.py`

### Opción A: Modelos Clásicos (Recomendado para empezar)

```python
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

# Dividir datos
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Modelos a probar
models = {
    'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
    'Gradient Boosting': GradientBoostingClassifier(random_state=42),
    'SVM': SVC(probability=True, random_state=42),
    'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000)
}

# Entrenar y evaluar
results = {}
for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    results[name] = {
        'accuracy': model.score(X_test, y_test),
        'roc_auc': roc_auc_score(y_test, y_proba),
        'report': classification_report(y_test, y_pred)
    }
    print(f"\n=== {name} ===")
    print(results[name]['report'])
```

### Opción B: Deep Learning (Si tienes suficientes datos)

```python
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

# Crear modelo de red neuronal
model = keras.Sequential([
    layers.Dense(128, activation='relu', input_shape=(X_train.shape[1],)),
    layers.Dropout(0.3),
    layers.Dense(64, activation='relu'),
    layers.Dropout(0.3),
    layers.Dense(32, activation='relu'),
    layers.Dense(1, activation='sigmoid')
])

model.compile(
    optimizer='adam',
    loss='binary_crossentropy',
    metrics=['accuracy']
)

# Entrenar
history = model.fit(
    X_train, y_train,
    epochs=50,
    batch_size=32,
    validation_split=0.2,
    verbose=1
)
```

**Qué modelos probar:**
- ✅ Random Forest (buen punto de partida)
- ✅ Gradient Boosting (XGBoost, LightGBM)
- ✅ SVM
- ✅ Redes Neuronales (si tienes >1000 muestras)
- ✅ Ensemble de modelos

---

## 📈 4. Evaluación y Métricas

### Objetivo: Medir el rendimiento del modelo

**Script sugerido:** `04_evaluate.py`

```python
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, roc_auc_score, roc_curve, confusion_matrix
)
import matplotlib.pyplot as plt

def evaluate_model(model, X_test, y_test):
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    metrics = {
        'Accuracy': accuracy_score(y_test, y_pred),
        'Precision': precision_score(y_test, y_pred),
        'Recall': recall_score(y_test, y_pred),
        'F1-Score': f1_score(y_test, y_pred),
        'ROC-AUC': roc_auc_score(y_test, y_proba)
    }
    
    # Matriz de confusión
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.title('Matriz de Confusión')
    plt.show()
    
    # Curva ROC
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    plt.plot(fpr, tpr)
    plt.title('Curva ROC')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.show()
    
    return metrics
```

**Métricas importantes:**
- ✅ **Accuracy**: Precisión general
- ✅ **Precision**: De los predichos como demencia, ¿cuántos realmente lo son?
- ✅ **Recall**: De los que tienen demencia, ¿cuántos detectamos?
- ✅ **F1-Score**: Balance entre precision y recall
- ✅ **ROC-AUC**: Área bajo la curva ROC (mejor métrica para problemas desbalanceados)

---

## 🎯 5. Análisis de Importancia de Características

### Objetivo: Entender qué características son más importantes

**Script sugerido:** `05_feature_importance.py`

```python
import matplotlib.pyplot as plt
import pandas as pd

# Con Random Forest
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)

# Obtener importancia
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': rf_model.feature_importances_
}).sort_values('importance', ascending=False)

# Visualizar top 20
plt.figure(figsize=(10, 8))
top_features = feature_importance.head(20)
plt.barh(top_features['feature'], top_features['importance'])
plt.xlabel('Importancia')
plt.title('Top 20 Características Más Importantes')
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()

# Verificar si las nuevas características están en el top
new_features = ['Skewness_pause_duration', 'Kurtosis_pause_duration', 
                'Filler_frequency', 'Local_coherence', 'Lexical_errors']
print("\n=== Posición de las Nuevas Características ===")
for feat in new_features:
    if feat in feature_importance['feature'].values:
        rank = feature_importance[feature_importance['feature'] == feat].index[0] + 1
        importance = feature_importance[feature_importance['feature'] == feat]['importance'].values[0]
        print(f"{feat}: Posición #{rank}, Importancia: {importance:.4f}")
```

---

## 📊 6. Visualizaciones Avanzadas

### Objetivo: Comunicar resultados de forma visual

**Script sugerido:** `06_visualizations.py`

```python
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Comparación de características entre grupos
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=('Skewness Pause', 'Filler Frequency', 
                    'Local Coherence', 'Lexical Errors')
)

features_to_plot = [
    'Skewness_pause_duration',
    'Filler_frequency', 
    'Local_coherence',
    'Lexical_errors'
]

for idx, feat in enumerate(features_to_plot):
    row = (idx // 2) + 1
    col = (idx % 2) + 1
    
    dementia_values = df[df['dementia'] == 'dementia'][feat]
    normal_values = df[df['dementia'] == 'nodementia'][feat]
    
    fig.add_trace(
        go.Box(y=dementia_values, name='Dementia', showlegend=(idx==0)),
        row=row, col=col
    )
    fig.add_trace(
        go.Box(y=normal_values, name='Normal', showlegend=(idx==0)),
        row=row, col=col
    )

fig.update_layout(height=800, title_text="Comparación de Características Nuevas")
fig.show()

# 2. Matriz de correlación de características nuevas
new_features_df = df[new_features + ['dementia']]
corr_matrix = new_features_df.corr()
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0)
plt.title('Correlación entre Nuevas Características')
plt.show()
```

---

## 🔬 7. Análisis Estadístico

### Objetivo: Validar diferencias estadísticas

**Script sugerido:** `07_statistical_analysis.py`

```python
from scipy import stats

# Test t para comparar grupos
def compare_groups(feature_name):
    dementia_group = df[df['dementia'] == 'dementia'][feature_name]
    normal_group = df[df['dementia'] == 'nodementia'][feature_name]
    
    # Test t de Student
    t_stat, p_value = stats.ttest_ind(dementia_group, normal_group)
    
    print(f"\n=== {feature_name} ===")
    print(f"Media Dementia: {dementia_group.mean():.4f}")
    print(f"Media Normal: {normal_group.mean():.4f}")
    print(f"t-statistic: {t_stat:.4f}")
    print(f"p-value: {p_value:.4f}")
    print(f"Significativo (p<0.05): {'SÍ' if p_value < 0.05 else 'NO'}")

# Probar nuevas características
for feat in new_features:
    compare_groups(feat)
```

---

## 🚀 8. Pipeline Completo de ML

### Objetivo: Crear un pipeline reutilizable

**Script sugerido:** `08_ml_pipeline.py`

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV

# Pipeline completo
pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('selector', SelectKBest(f_classif, k=50)),
    ('classifier', RandomForestClassifier(random_state=42))
])

# Hiperparámetros para optimizar
param_grid = {
    'selector__k': [30, 50, 70],
    'classifier__n_estimators': [100, 200],
    'classifier__max_depth': [10, 20, None]
}

# Búsqueda de hiperparámetros
grid_search = GridSearchCV(
    pipeline, param_grid, 
    cv=5, scoring='roc_auc', 
    n_jobs=-1, verbose=1
)

grid_search.fit(X_train, y_train)

print(f"Mejores parámetros: {grid_search.best_params_}")
print(f"Mejor score: {grid_search.best_score_}")
```

---

## 📝 9. Guardar Modelo Entrenado

### Objetivo: Reutilizar el modelo

```python
import joblib
import pickle

# Guardar modelo
best_model = grid_search.best_estimator_
joblib.dump(best_model, 'modelo_demencia.pkl')

# Guardar también el scaler y selector por separado
joblib.dump(scaler, 'scaler.pkl')
joblib.dump(selector, 'feature_selector.pkl')

# Para cargar después:
# model = joblib.load('modelo_demencia.pkl')
# prediction = model.predict(new_data)
```

---

## 🌐 10. Crear API o Dashboard

### Opción A: API REST con Flask/FastAPI

**Script sugerido:** `09_api.py`

```python
from flask import Flask, request, jsonify
import joblib
import numpy as np

app = Flask(__name__)
model = joblib.load('modelo_demencia.pkl')

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    features = np.array([data['features']])
    prediction = model.predict(features)[0]
    probability = model.predict_proba(features)[0]
    
    return jsonify({
        'prediction': 'dementia' if prediction == 1 else 'nodementia',
        'probability': float(probability[1]),
        'confidence': 'high' if max(probability) > 0.8 else 'medium'
    })

if __name__ == '__main__':
    app.run(debug=True)
```

### Opción B: Dashboard con Streamlit

**Script sugerido:** `10_dashboard.py`

```python
import streamlit as st
import pandas as pd
import joblib

st.title('🔬 Detector de Demencia por Voz')

# Cargar modelo
model = joblib.load('modelo_demencia.pkl')

# Input de características
st.sidebar.header('Características del Audio')
skewness = st.sidebar.slider('Skewness Pause', -2.0, 5.0, 0.0)
filler_freq = st.sidebar.slider('Filler Frequency', 0.0, 10.0, 2.0)
coherence = st.sidebar.slider('Local Coherence', 0.0, 1.0, 0.7)
# ... más inputs

# Predicción
if st.button('Predecir'):
    features = np.array([[skewness, filler_freq, coherence, ...]])
    prediction = model.predict(features)[0]
    probability = model.predict_proba(features)[0]
    
    st.success(f'Predicción: {"Demencia" if prediction == 1 else "Normal"}')
    st.info(f'Probabilidad: {probability[1]*100:.2f}%')
```

---

## 📚 Recursos y Bibliotecas Necesarias

```bash
pip install pandas numpy matplotlib seaborn scikit-learn scipy plotly streamlit flask joblib xgboost lightgbm
```

---

## 🎯 Checklist de Próximos Pasos

- [ ] **Paso 1**: Hacer EDA básico para entender los datos
- [ ] **Paso 2**: Preparar y limpiar los datos
- [ ] **Paso 3**: Entrenar modelos básicos (Random Forest, SVM)
- [ ] **Paso 4**: Evaluar modelos con métricas apropiadas
- [ ] **Paso 5**: Analizar importancia de características
- [ ] **Paso 6**: Optimizar hiperparámetros
- [ ] **Paso 7**: Validar con test set independiente
- [ ] **Paso 8**: Crear visualizaciones para presentación
- [ ] **Paso 9**: Guardar modelo final
- [ ] **Paso 10**: Crear API o dashboard (opcional)

---

## 💡 Tips Importantes

1. **Balance de clases**: Si tienes desbalance, usa técnicas como SMOTE o ajustar class_weight
2. **Validación cruzada**: Usa k-fold CV para evaluar mejor tus modelos
3. **Feature importance**: Verifica que tus nuevas características sean importantes
4. **Interpretabilidad**: Considera usar SHAP values para explicar predicciones
5. **Documentación**: Documenta todo el proceso para reproducibilidad

---

## 🎓 Para tu TFM

Estos pasos te permitirán:
- ✅ Demostrar un pipeline completo de ML
- ✅ Comparar diferentes modelos
- ✅ Analizar la importancia de las nuevas características
- ✅ Crear visualizaciones profesionales
- ✅ Desplegar una solución funcional

---

*¡Buena suerte con tu proyecto! 🚀*
