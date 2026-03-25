# 📁 Estructura del Proyecto - TFM ADReSSo Challenge

Este documento describe la organización del proyecto siguiendo buenas prácticas de Data Science.

## 🗂️ Estructura de Directorios

```
TFM/
├── scripts/                      # Scripts de procesamiento y análisis
│   ├── Process_Parametros_.py   # ⭐ Script principal de extracción
│   ├── 01_EDA_basico.py         # Análisis exploratorio de datos
│   └── 02_train_basic_models.py # Entrenamiento de modelos ML
│
├── output_data/                  # ✅ TODOS LOS OUTPUTS AQUÍ
│   ├── ADReSSo21_latest.json   # JSON principal (última versión)
│   ├── ADReSSo21_*.json         # Versiones históricas con timestamp
│   ├── figures/                 # Gráficos y visualizaciones (PNG)
│   ├── reports/                 # Reportes de texto (TXT)
│   └── processed_data/         # Datos procesados (CSV)
│
├── docs/                         # 📚 Documentación técnica
│   ├── CARACTERISTICAS.md       # Documentación completa de características
│   ├── GUIA_USO.md              # Guía de uso del sistema
│   └── ESTRUCTURA_PROYECTO.md   # Este archivo
│
├── static/                       # Archivos estáticos
│   └── project_information/     # PDFs y documentación del proyecto
│
├── TAILBANK/                     # Audios originales
│   ├── dementia/
│   └── nodementia/
│
├── dementibank_normalizado/      # Audios normalizados
│   ├── dementia/
│   └── nodementia/
│
├── README.md                     # 📖 Documentación principal del proyecto
└── requirements.txt              # Dependencias del proyecto
```

## 📋 Convenciones de Nombres

### Scripts
- Formato: `{numero}_{nombre_descriptivo}.py`
- Ejemplo: `01_EDA_basico.py`, `02_train_basic_models.py`
- Uso de snake_case

### Archivos de Output
- Formato: `{script_name}_{tipo}_{timestamp}.{extension}`
- Ejemplo: `eda_distributions_new_features_20250126_143022.png`
- Incluyen timestamp para evitar sobrescrituras

### Directorios
- Nombres en minúsculas
- Separación con guiones bajos si es necesario
- Descriptivos y claros

## 🎯 Flujo de Trabajo

```
1. Datos Originales (TAILBANK/)
   ↓
2. Procesamiento (Process_Parametros_.py)
   ↓
3. Datos Procesados (ADReSSo21.json)
   ↓
4. Análisis (scripts/01_EDA_basico.py)
   ↓
5. Outputs Organizados (output_data/)
   ├── figures/
   ├── reports/
   └── processed_data/
```

## ✅ Buenas Prácticas Implementadas

1. **Separación de Concerns**
   - Scripts separados por funcionalidad
   - Datos originales vs procesados
   - Outputs organizados por tipo

2. **Versionado de Outputs**
   - Timestamps en nombres de archivos
   - No se sobrescriben resultados anteriores

3. **Rutas Relativas**
   - Scripts usan rutas relativas al proyecto
   - Fácil de mover o compartir

4. **Documentación**
   - README en cada directorio importante
   - Comentarios en código
   - Documentación de características

5. **Reproducibilidad**
   - Seeds aleatorios fijados
   - Parámetros documentados
   - Scripts ejecutables independientemente

## 📝 Notas Importantes

- **Nunca** guardar outputs en la raíz del proyecto
- **Siempre** usar `output_data/` para resultados
- Los scripts crean automáticamente los directorios necesarios
- Los archivos antiguos se pueden limpiar manualmente si es necesario

## 🔧 Configuración de Rutas

Los scripts detectan automáticamente la estructura:
```python
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output_data"
```

Esto permite ejecutar los scripts desde cualquier ubicación dentro del proyecto.
