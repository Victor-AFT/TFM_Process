# ☁️ TFM Cloud Architecture - AWS Medallion

Implementación de la arquitectura AWS nativa para procesamiento de audio y detección de demencia.

**Región AWS**: `eu-central-1` (Frankfurt)

---

## 📁 Estructura

```
cloud/
├── bronze/          # Capa Bronze - Almacenamiento de audios RAW
├── silver/          # Capa Silver - Transcripción y extracción de features
├── gold/            # Capa Gold - Datos transformados en Parquet
└── orchestration/   # Orquestación con Lambda y Step Functions
```

---

## 🗺️ Mapa de Arquitectura (Medallion)

Esta arquitectura sigue el patrón **Bronze-Silver-Gold** para transformar datos crudos en insights valiosos, todo centralizado en AWS.

```mermaid
graph TD
    subgraph Ingesta["🥉 Ingesta & Bronze Layer (Raw)"]
        A[📱 Web App Streamlit] -->|Sube Audio| B(🪣 S3 Bronze: raw/)
        Drive[☁️ Google Drive] -->|Sube API| B
        B -->|Trigger Automático| C[⚡ AWS Lambda Normalizer]
        C -->|RMS 0.1 a 16kHz| D(🪣 S3 Bronze: norm/)
        B -.->|0 Días Lifecycle| E(❄️ Amazon S3 Glacier: raw/)
    end

    subgraph Procesamiento["🥈 Silver Layer (Transformed)"]
        D -->|Lee audios norm/| G[🧠 SageMaker Notebook]
        G -.->|🎵 Librosa/OpenSMILE| I[Extracción Features]
        G -.->|📝 Whisper/spaCy| J[Trascripción y NLP]
        I --> K(🪣 S3 Silver: features.json)
        J --> K
    end

    subgraph Transformacion["🥇 Gold Layer (Business Ready)"]
        K -->|Trigger Automático| M[⚡ AWS Lambda Gold]
        M -->|Filtra Variables| O[📦 Formato JSON limpio]
        O --> P(🪣 S3 Gold: gold_features.json)
    end

    subgraph Consumo["📊 Consumo & Visualización"]
        P -->|Crawls| Q[🕷️ AWS Glue Crawler]
        Q -->|Catálogo| R[📚 AWS Glue Data Catalog]
        R -->|Consultas| S[🔍 Amazon Athena SQL]
        S -->|Data| T[📈 Modelos ML]
    end

    style B fill:#cd7f32,stroke:#333,stroke-width:2px
    style D fill:#cd7f32,stroke:#333,stroke-width:2px
    style E fill:#00ffff,stroke:#333,stroke-width:1px
    style K fill:#c0c0c0,stroke:#333,stroke-width:2px
    style P fill:#ffd700,stroke:#333,stroke-width:2px
```

### Explicación del Flujo

1.  **🥉 Bronze Layer (Raw)**:
    *   La Web App (o la API de Drive) sube los `.wav` originales a S3 en `raw/`.
    *   S3 congela los archivos crudos en `Glacier` la misma noche para ahorrar costes.
    *   Una Lambda desencadenada automáticamente normaliza el audio al momento y lo guarda en `norm/`.

2.  **🥈 Silver Layer (Refined)**:
    *   El Notebook de SageMaker lee **únicamente** los audios limpios de la subcarpeta `norm/`.

3.  **🥇 Gold Layer (Curated)**:
    *   **AWS Glue (ETL)** cruza features acústicas con transcripciones y metadatos clínicos.
    *   Limpia, agrega y optimiza los datos en formato **Parquet** (columnar y comprimido).
    *   Particiona los datos para consultas eficientes.

4.  **📊 Capa de Visualización (Athena)**:
    *   Un **Glue Crawler** cataloga automáticamente los archivos Parquet.
    *   **Athena** permite consultar estos archivos usando SQL estándar (Serverless).
    *   Desde aquí conectas herramientas de BI (QuickSight) o Notebooks de Ciencia de Datos.

---

## 🚀 Orden de Implementación

1. **Bronze**: Crear buckets y subir audios
2. **Silver (Lambda)**: Transcripción automática con Whisper
3. **Silver (SageMaker)**: Extracción de features acústicas
4. **Gold**: ETL con Glue/Spark
5. **Catalog**: Configurar catálogo y queries

---

## 💰 Costos Estimados

| Servicio | Configuración | Costo/mes |
|----------|--------------|-----------|
| S3 | 5 GB storage | $0.12 |
| Lambda | 1 GB RAM, 100 invocaciones | $0.20 |
| SageMaker | ml.m5.large, 2 horas | $0.46 |
| Glue | 10 DPU-hours | $0.44 |
| **Total** | Primera ejecución | **~$1.22** |

---

Consulta los subdirectorios para scripts específicos de cada capa.
