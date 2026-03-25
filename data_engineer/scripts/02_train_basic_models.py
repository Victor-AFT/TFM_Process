"""
Script para entrenar modelos básicos de Machine Learning
Usa los datos procesados para crear modelos predictivos
"""

import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report, confusion_matrix, 
    roc_auc_score, roc_curve, accuracy_score
)
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from pathlib import Path

def load_and_prepare_data(json_path='ADReSSo21.json'):
    """Carga y prepara los datos para entrenamiento"""
    print("📂 Cargando datos...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Convertir a DataFrame
    df = pd.json_normalize(data)
    
    print(f"✅ Datos cargados: {len(df)} registros")
    return df

def prepare_features(df):
    """Prepara las características para el modelo"""
    print("\n🔧 Preparando características...")
    
    # Excluir columnas no numéricas y metadatos
    exclude_cols = ['uuid', 'audio', 'name', 'dementia', 'gender', 'ethnicity', 
                   'calidad', 'score', 'parametros_opensmile_compare']
    
    # Obtener todas las columnas numéricas
    feature_cols = [col for col in df.columns 
                   if col not in exclude_cols 
                   and df[col].dtype in ['float64', 'int64']]
    
    # Filtrar columnas con muchos valores faltantes
    feature_cols = [col for col in feature_cols 
                   if df[col].isnull().sum() / len(df) < 0.5]
    
    X = df[feature_cols].copy()
    
    # Manejar valores faltantes (rellenar con la media)
    X = X.fillna(X.mean())
    
    # Variable objetivo
    y = df['dementia'].map({'dementia': 1, 'nodementia': 0})
    
    print(f"✅ Características preparadas: {X.shape[1]} features")
    print(f"✅ Clases: {y.value_counts().to_dict()}")
    
    return X, y, feature_cols

def train_models(X_train, X_test, y_train, y_test):
    """Entrena múltiples modelos y compara resultados"""
    print("\n🤖 Entrenando modelos...")
    
    # Escalar características
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Modelos a probar
    models = {
        'Random Forest': RandomForestClassifier(
            n_estimators=100, 
            random_state=42, 
            max_depth=10,
            class_weight='balanced'
        ),
        'Gradient Boosting': GradientBoostingClassifier(
            n_estimators=100,
            random_state=42,
            max_depth=5
        ),
        'SVM': SVC(
            probability=True, 
            random_state=42,
            class_weight='balanced'
        ),
        'Logistic Regression': LogisticRegression(
            random_state=42, 
            max_iter=1000,
            class_weight='balanced'
        )
    }
    
    results = {}
    
    for name, model in models.items():
        print(f"\n  📊 Entrenando {name}...")
        
        # Entrenar (usar escalado para SVM y Logistic Regression)
        if name in ['SVM', 'Logistic Regression']:
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            y_proba = model.predict_proba(X_test_scaled)[:, 1]
        else:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            y_proba = model.predict_proba(X_test)[:, 1]
        
        # Métricas
        accuracy = accuracy_score(y_test, y_pred)
        roc_auc = roc_auc_score(y_test, y_proba)
        
        results[name] = {
            'model': model,
            'scaler': scaler if name in ['SVM', 'Logistic Regression'] else None,
            'y_pred': y_pred,
            'y_proba': y_proba,
            'accuracy': accuracy,
            'roc_auc': roc_auc,
            'report': classification_report(y_test, y_pred)
        }
        
        print(f"    ✅ Accuracy: {accuracy:.4f}")
        print(f"    ✅ ROC-AUC: {roc_auc:.4f}")
    
    return results

def evaluate_models(results, y_test):
    """Evalúa y visualiza resultados de los modelos"""
    print("\n📈 Evaluando modelos...")
    
    # Comparar modelos
    comparison = pd.DataFrame({
        'Model': list(results.keys()),
        'Accuracy': [r['accuracy'] for r in results.values()],
        'ROC-AUC': [r['roc_auc'] for r in results.values()]
    }).sort_values('ROC-AUC', ascending=False)
    
    print("\n" + "=" * 80)
    print("COMPARACIÓN DE MODELOS")
    print("=" * 80)
    print(comparison.to_string(index=False))
    
    # Visualizar comparación
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    comparison.set_index('Model').plot(kind='bar', ax=axes[0])
    axes[0].set_title('Comparación de Métricas')
    axes[0].set_ylabel('Score')
    axes[0].legend(['Accuracy', 'ROC-AUC'])
    axes[0].tick_params(axis='x', rotation=45)
    
    # Curvas ROC
    for name, result in results.items():
        fpr, tpr, _ = roc_curve(y_test, result['y_proba'])
        axes[1].plot(fpr, tpr, label=f"{name} (AUC={result['roc_auc']:.3f})")
    
    axes[1].plot([0, 1], [0, 1], 'k--', label='Random')
    axes[1].set_xlabel('False Positive Rate')
    axes[1].set_ylabel('True Positive Rate')
    axes[1].set_title('Curvas ROC')
    axes[1].legend()
    axes[1].grid(True)
    
    plt.tight_layout()
    plt.savefig('comparacion_modelos.png', dpi=300, bbox_inches='tight')
    print("\n✅ Gráfico guardado: comparacion_modelos.png")
    plt.show()
    
    # Matrices de confusión
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    
    for idx, (name, result) in enumerate(results.items()):
        cm = confusion_matrix(y_test, result['y_pred'])
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[idx])
        axes[idx].set_title(f'{name}\nAccuracy: {result["accuracy"]:.3f}')
        axes[idx].set_ylabel('Real')
        axes[idx].set_xlabel('Predicho')
    
    plt.tight_layout()
    plt.savefig('matrices_confusion.png', dpi=300, bbox_inches='tight')
    print("✅ Gráfico guardado: matrices_confusion.png")
    plt.show()
    
    return comparison

def feature_importance_analysis(best_model, feature_cols, X_train):
    """Analiza la importancia de las características"""
    print("\n🎯 Analizando importancia de características...")
    
    if hasattr(best_model, 'feature_importances_'):
        importance_df = pd.DataFrame({
            'feature': feature_cols,
            'importance': best_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # Top 20 características más importantes
        top_features = importance_df.head(20)
        
        plt.figure(figsize=(10, 8))
        plt.barh(top_features['feature'], top_features['importance'])
        plt.xlabel('Importancia')
        plt.title('Top 20 Características Más Importantes')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig('feature_importance.png', dpi=300, bbox_inches='tight')
        print("✅ Gráfico guardado: feature_importance.png")
        plt.show()
        
        # Verificar nuevas características
        new_features = [
            'Skewness_pause_duration',
            'Kurtosis_pause_duration',
            'Filler_frequency',
            'Local_coherence',
            'Lexical_errors'
        ]
        
        print("\n" + "=" * 80)
        print("POSICIÓN DE LAS NUEVAS CARACTERÍSTICAS")
        print("=" * 80)
        
        for feat in new_features:
            # Buscar en todas las columnas (puede estar en diferentes niveles)
            matching = importance_df[importance_df['feature'].str.contains(feat, case=False, na=False)]
            if len(matching) > 0:
                for idx, row in matching.iterrows():
                    rank = importance_df.index.get_loc(idx) + 1
                    print(f"{row['feature']}: Posición #{rank}, Importancia: {row['importance']:.6f}")
            else:
                print(f"{feat}: No encontrada en las características")
        
        return importance_df
    else:
        print("⚠️ Este modelo no tiene feature_importances_")
        return None

def save_best_model(results, scaler, feature_cols):
    """Guarda el mejor modelo"""
    # Encontrar el mejor modelo por ROC-AUC
    best_name = max(results.keys(), key=lambda k: results[k]['roc_auc'])
    best_result = results[best_name]
    
    print(f"\n💾 Guardando mejor modelo: {best_name}")
    
    # Guardar modelo
    joblib.dump(best_result['model'], 'mejor_modelo.pkl')
    
    # Guardar scaler si existe
    if best_result['scaler'] is not None:
        joblib.dump(best_result['scaler'], 'scaler.pkl')
    
    # Guardar nombres de características
    with open('feature_names.txt', 'w') as f:
        f.write('\n'.join(feature_cols))
    
    print("✅ Modelo guardado: mejor_modelo.pkl")
    print("✅ Scaler guardado: scaler.pkl")
    print("✅ Nombres de características guardados: feature_names.txt")
    
    return best_name, best_result

def main():
    """Función principal"""
    print("=" * 80)
    print("🚀 ENTRENAMIENTO DE MODELOS DE MACHINE LEARNING")
    print("=" * 80)
    
    # 1. Cargar datos
    df = load_and_prepare_data()
    
    # 2. Preparar características
    X, y, feature_cols = prepare_features(df)
    
    # 3. Dividir datos
    print("\n✂️ Dividiendo datos en train/test...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"✅ Train: {len(X_train)} muestras")
    print(f"✅ Test: {len(X_test)} muestras")
    
    # 4. Entrenar modelos
    results = train_models(X_train, X_test, y_train, y_test)
    
    # 5. Evaluar modelos
    comparison = evaluate_models(results, y_test)
    
    # 6. Análisis de importancia
    best_name = comparison.iloc[0]['Model']
    best_model = results[best_name]['model']
    feature_importance_analysis(best_model, feature_cols, X_train)
    
    # 7. Guardar mejor modelo
    save_best_model(results, None, feature_cols)
    
    # 8. Mostrar reporte detallado del mejor modelo
    print("\n" + "=" * 80)
    print(f"REPORTE DETALLADO - {best_name}")
    print("=" * 80)
    print(results[best_name]['report'])
    
    print("\n" + "=" * 80)
    print("✅ ENTRENAMIENTO COMPLETADO")
    print("=" * 80)
    print(f"\nMejor modelo: {best_name}")
    print(f"Accuracy: {results[best_name]['accuracy']:.4f}")
    print(f"ROC-AUC: {results[best_name]['roc_auc']:.4f}")

if __name__ == "__main__":
    main()
