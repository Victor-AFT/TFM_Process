"""
Análisis Exploratorio de Datos (EDA) básico
Para entender los datos antes de entrenar modelos

Autor: TFM ADReSSo Challenge
Fecha: 2025
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from datetime import datetime
import sys

# Configuración de rutas siguiendo buenas prácticas
PROJECT_ROOT = Path(__file__).parent.parent  # Subir un nivel desde scripts/
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output_data"
FIGURES_DIR = OUTPUT_DIR / "figures"
REPORTS_DIR = OUTPUT_DIR / "reports"
PROCESSED_DATA_DIR = OUTPUT_DIR / "processed_data"

# Crear directorios si no existen
OUTPUT_DIR.mkdir(exist_ok=True)
FIGURES_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

# Configuración de visualización
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'

def load_data(json_path=None):
    """
    Carga el JSON y lo convierte a DataFrame
    
    Busca el archivo JSON en el siguiente orden:
    1. Ruta especificada por el usuario
    2. output_data/ADReSSo21_latest.json (última versión)
    3. output_data/ADReSSo21_*.json (más reciente con timestamp)
    4. PROJECT_ROOT/ADReSSo21.json (raíz del proyecto, compatibilidad)
    
    Args:
        json_path: Ruta al archivo JSON. Si es None, busca automáticamente.
    
    Returns:
        DataFrame con los datos normalizados
    """
    if json_path is None:
        # Buscar en output_data primero
        latest_json = OUTPUT_DIR / "ADReSSo21_latest.json"
        
        if latest_json.exists():
            json_path = latest_json
            print(f"📂 Usando última versión: {json_path}")
        else:
            # Buscar el más reciente con timestamp
            json_files = list(OUTPUT_DIR.glob("ADReSSo21_*.json"))
            if json_files:
                # Ordenar por fecha de modificación y tomar el más reciente
                json_path = max(json_files, key=lambda p: p.stat().st_mtime)
                print(f"📂 Usando archivo más reciente: {json_path}")
            else:
                # Fallback a la raíz del proyecto (compatibilidad)
                json_path = PROJECT_ROOT / "ADReSSo21.json"
                if json_path.exists():
                    print(f"📂 Usando archivo en raíz del proyecto: {json_path}")
                else:
                    raise FileNotFoundError(
                        f"No se encontró ningún archivo ADReSSo21.json.\n"
                        f"Buscado en:\n"
                        f"  - {OUTPUT_DIR / 'ADReSSo21_latest.json'}\n"
                        f"  - {OUTPUT_DIR / 'ADReSSo21_*.json'}\n"
                        f"  - {PROJECT_ROOT / 'ADReSSo21.json'}"
                    )
    else:
        json_path = Path(json_path)
    
    if not json_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {json_path}")
    
    print(f"📂 Cargando datos desde: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Normalizar JSON anidado a DataFrame plano
    df = pd.json_normalize(data)
    print(f"✅ Datos cargados: {len(df)} registros, {len(df.columns)} columnas")
    return df

def basic_statistics(df, save_report=True):
    """
    Estadísticas básicas del dataset
    
    Args:
        df: DataFrame con los datos
        save_report: Si True, guarda el reporte en un archivo de texto
    
    Returns:
        dict: Diccionario con las estadísticas calculadas
    """
    print("=" * 80)
    print("RESUMEN DEL DATASET")
    print("=" * 80)
    
    stats = {
        'total_audios': len(df),
        'total_features': len(df.columns),
        'distribucion_clase': df['dementia'].value_counts().to_dict(),
        'distribucion_calidad': df['calidad'].value_counts().to_dict() if 'calidad' in df.columns else {},
        'distribucion_genero': df['gender'].value_counts().to_dict() if 'gender' in df.columns else {}
    }
    
    print(f"\nTotal de audios procesados: {stats['total_audios']}")
    print(f"Total de características: {stats['total_features']}")
    print(f"\nDistribución por clase:")
    print(df['dementia'].value_counts())
    if 'calidad' in df.columns:
        print(f"\nDistribución por calidad:")
        print(df['calidad'].value_counts())
    if 'gender' in df.columns:
        print(f"\nDistribución por género:")
        print(df['gender'].value_counts())
    
    # Guardar reporte si se solicita
    if save_report:
        report_path = REPORTS_DIR / f"eda_basic_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("RESUMEN DEL DATASET - EDA\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Fecha de análisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Total de audios procesados: {stats['total_audios']}\n")
            f.write(f"Total de características: {stats['total_features']}\n\n")
            f.write("Distribución por clase:\n")
            f.write(str(df['dementia'].value_counts()) + "\n\n")
            if 'calidad' in df.columns:
                f.write("Distribución por calidad:\n")
                f.write(str(df['calidad'].value_counts()) + "\n\n")
            if 'gender' in df.columns:
                f.write("Distribución por género:\n")
                f.write(str(df['gender'].value_counts()) + "\n")
        print(f"\n✅ Reporte guardado en: {report_path}")
    
    return stats

def analyze_new_features(df, save_report=True):
    """
    Analiza las nuevas características añadidas
    
    Args:
        df: DataFrame con los datos
        save_report: Si True, guarda el análisis en un archivo
    
    Returns:
        dict: Diccionario con los resultados del análisis
    """
    new_features = [
        'parametros_librosa.Skewness_pause_duration',
        'parametros_librosa.Kurtosis_pause_duration',
        'parametros_whisperSpacy.Filler_frequency',
        'parametros_whisperSpacy.Local_coherence',
        'parametros_whisperSpacy.Lexical_errors'
    ]
    
    print("\n" + "=" * 80)
    print("ANÁLISIS DE NUEVAS CARACTERÍSTICAS")
    print("=" * 80)
    
    # Separar por clase
    dementia_df = df[df['dementia'] == 'dementia']
    normal_df = df[df['dementia'] == 'nodementia']
    
    analysis_results = {}
    
    from scipy import stats
    
    for feat in new_features:
        if feat in df.columns:
            feat_name = feat.split('.')[-1]
            print(f"\n--- {feat_name} ---")
            
            dementia_mean = dementia_df[feat].mean()
            dementia_std = dementia_df[feat].std()
            normal_mean = normal_df[feat].mean()
            normal_std = normal_df[feat].std()
            
            print(f"Dementia - Media: {dementia_mean:.4f}, Std: {dementia_std:.4f}")
            print(f"Normal    - Media: {normal_mean:.4f}, Std: {normal_std:.4f}")
            
            # Test estadístico
            t_stat, p_value = stats.ttest_ind(
                dementia_df[feat].dropna(), 
                normal_df[feat].dropna()
            )
            significance = '***' if p_value < 0.001 else '**' if p_value < 0.01 else '*' if p_value < 0.05 else ''
            print(f"Test t: t={t_stat:.4f}, p={p_value:.4f} {significance}")
            
            analysis_results[feat_name] = {
                'dementia_mean': dementia_mean,
                'dementia_std': dementia_std,
                'normal_mean': normal_mean,
                'normal_std': normal_std,
                't_statistic': t_stat,
                'p_value': p_value,
                'significant': p_value < 0.05
            }
    
    # Guardar análisis si se solicita
    if save_report and analysis_results:
        report_path = REPORTS_DIR / f"eda_new_features_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ANÁLISIS DE NUEVAS CARACTERÍSTICAS\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Fecha de análisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for feat_name, results in analysis_results.items():
                f.write(f"--- {feat_name} ---\n")
                f.write(f"Dementia - Media: {results['dementia_mean']:.4f}, Std: {results['dementia_std']:.4f}\n")
                f.write(f"Normal    - Media: {results['normal_mean']:.4f}, Std: {results['normal_std']:.4f}\n")
                f.write(f"Test t: t={results['t_statistic']:.4f}, p={results['p_value']:.4f}\n")
                f.write(f"Significativo (p<0.05): {'SÍ' if results['significant'] else 'NO'}\n\n")
        print(f"\n✅ Análisis guardado en: {report_path}")
    
    return analysis_results

def visualize_distributions(df, save_fig=True, show_fig=False):
    """
    Visualiza distribuciones de las nuevas características
    
    Args:
        df: DataFrame con los datos
        save_fig: Si True, guarda la figura
        show_fig: Si True, muestra la figura (puede causar problemas en algunos entornos)
    """
    new_features = {
        'Skewness_pause_duration': 'parametros_librosa.Skewness_pause_duration',
        'Kurtosis_pause_duration': 'parametros_librosa.Kurtosis_pause_duration',
        'Filler_frequency': 'parametros_whisperSpacy.Filler_frequency',
        'Local_coherence': 'parametros_whisperSpacy.Local_coherence',
        'Lexical_errors': 'parametros_whisperSpacy.Lexical_errors'
    }
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()
    
    for idx, (name, col) in enumerate(new_features.items()):
        if col in df.columns:
            ax = axes[idx]
            
            # Boxplot por clase
            df.boxplot(column=col, by='dementia', ax=ax)
            ax.set_title(f'{name} por Clase')
            ax.set_xlabel('')
            ax.set_ylabel(name)
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=0)
    
    # Ocultar último subplot si hay menos de 5 características
    if len(new_features) < 6:
        axes[-1].axis('off')
    
    plt.suptitle('Distribución de Nuevas Características por Clase', fontsize=16)
    plt.tight_layout()
    
    if save_fig:
        fig_path = FIGURES_DIR / f"eda_distributions_new_features_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico guardado: {fig_path}")
    
    if show_fig:
        plt.show()
    else:
        plt.close()

def correlation_analysis(df, save_fig=True, save_data=True, show_fig=False):
    """
    Análisis de correlación entre características nuevas
    
    Args:
        df: DataFrame con los datos
        save_fig: Si True, guarda la figura
        save_data: Si True, guarda la matriz de correlación en CSV
        show_fig: Si True, muestra la figura
    """
    new_features_cols = [
        'parametros_librosa.Skewness_pause_duration',
        'parametros_librosa.Kurtosis_pause_duration',
        'parametros_whisperSpacy.Filler_frequency',
        'parametros_whisperSpacy.Local_coherence',
        'parametros_whisperSpacy.Lexical_errors'
    ]
    
    # Filtrar solo las que existen
    available_features = [f for f in new_features_cols if f in df.columns]
    
    if len(available_features) > 1:
        corr_matrix = df[available_features].corr()
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, 
                   square=True, linewidths=1, cbar_kws={"shrink": 0.8})
        plt.title('Matriz de Correlación - Nuevas Características', fontsize=14)
        plt.tight_layout()
        
        if save_fig:
            fig_path = FIGURES_DIR / f"eda_correlation_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(fig_path, dpi=300, bbox_inches='tight')
            print(f"✅ Gráfico guardado: {fig_path}")
        
        if save_data:
            csv_path = PROCESSED_DATA_DIR / f"correlation_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            corr_matrix.to_csv(csv_path)
            print(f"✅ Matriz de correlación guardada: {csv_path}")
        
        if show_fig:
            plt.show()
        else:
            plt.close()
        
        return corr_matrix
    else:
        print("⚠️ No hay suficientes características nuevas para análisis de correlación")
        return None

def missing_values_analysis(df, save_report=True):
    """
    Analiza valores faltantes
    
    Args:
        df: DataFrame con los datos
        save_report: Si True, guarda el análisis en CSV
    
    Returns:
        DataFrame con el análisis de valores faltantes
    """
    print("\n" + "=" * 80)
    print("ANÁLISIS DE VALORES FALTANTES")
    print("=" * 80)
    
    missing = df.isnull().sum()
    missing_pct = (missing / len(df)) * 100
    
    missing_df = pd.DataFrame({
        'feature': missing.index,
        'valores_faltantes': missing.values,
        'porcentaje': missing_pct.values
    }).sort_values('valores_faltantes', ascending=False)
    
    # Mostrar solo las que tienen valores faltantes
    missing_df_filtered = missing_df[missing_df['valores_faltantes'] > 0]
    
    if len(missing_df_filtered) > 0:
        print(f"\nTotal de características con valores faltantes: {len(missing_df_filtered)}")
        print(missing_df_filtered.head(20).to_string(index=False))
        
        if save_report:
            csv_path = PROCESSED_DATA_DIR / f"missing_values_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            missing_df_filtered.to_csv(csv_path, index=False)
            print(f"\n✅ Análisis guardado en: {csv_path}")
    else:
        print("✅ No hay valores faltantes en el dataset")
    
    return missing_df

def main():
    """Función principal"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("=" * 80)
    print("🔍 ANÁLISIS EXPLORATORIO DE DATOS (EDA)")
    print("=" * 80)
    print(f"Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Directorio de salida: {OUTPUT_DIR}")
    print()
    
    try:
        # Cargar datos
        df = load_data()
        
        # Análisis básico
        stats = basic_statistics(df, save_report=True)
        
        # Análisis de nuevas características
        feature_analysis = analyze_new_features(df, save_report=True)
        
        # Análisis de valores faltantes
        missing_analysis = missing_values_analysis(df, save_report=True)
        
        # Visualizaciones
        print("\n📊 Generando visualizaciones...")
        visualize_distributions(df, save_fig=True, show_fig=False)
        corr_matrix = correlation_analysis(df, save_fig=True, save_data=True, show_fig=False)
        
        # Guardar DataFrame procesado
        csv_path = PROCESSED_DATA_DIR / f"processed_data_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        print(f"\n✅ Datos procesados guardados en: {csv_path}")
        
        # Guardar resumen ejecutivo
        summary_path = REPORTS_DIR / f"eda_summary_{timestamp}.txt"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("RESUMEN EJECUTIVO - EDA\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Fecha de análisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Total de registros: {stats['total_audios']}\n")
            f.write(f"Total de características: {stats['total_features']}\n\n")
            f.write("Archivos generados:\n")
            f.write(f"  - Datos procesados: {csv_path.name}\n")
            f.write(f"  - Figuras: {FIGURES_DIR.name}/\n")
            f.write(f"  - Reportes: {REPORTS_DIR.name}/\n")
            f.write(f"  - Datos procesados: {PROCESSED_DATA_DIR.name}/\n")
        
        print(f"\n✅ Resumen ejecutivo guardado en: {summary_path}")
        
        print("\n" + "=" * 80)
        print("✅ EDA COMPLETADO EXITOSAMENTE")
        print("=" * 80)
        print(f"\n📁 Todos los resultados se han guardado en: {OUTPUT_DIR}")
        print(f"   - Figuras: {FIGURES_DIR}")
        print(f"   - Reportes: {REPORTS_DIR}")
        print(f"   - Datos procesados: {PROCESSED_DATA_DIR}")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print(f"💡 Asegúrate de que el archivo ADReSSo21.json existe en: {PROJECT_ROOT}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
