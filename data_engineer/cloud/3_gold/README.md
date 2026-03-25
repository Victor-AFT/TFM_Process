# 🥇 Gold — Datos Listos para ML

Lee el JSON de S3 Silver, filtra las ~44 variables más importantes,
y guarda un JSON limpio y plano en S3 Gold.

## Archivos

| Archivo | Qué hace |
|---------|----------|
| `01_lambda_gold.py` | Lambda: filtra variables Silver → Gold |
| `02_deploy_lambda_gold.py` | Despliega la Lambda con boto3 |

## Variables que selecciona

| Categoría | Nº | Ejemplos |
|-----------|-----|----------|
| Metadatos | 2 | audio, dementia |
| Librosa | 19 | MFCCs, pitch, jitter, pausas |
| OpenSMILE | 13 | F0, loudness, formantes |
| Whisper+spaCy | 10 | TTR, coherencia, fillers |
| **Total** | **~44** | |

## Uso Automático

1. Ejecutar el script para crear la Lambda y configurar su Trigger S3:
```bash
python 02_deploy_lambda_gold.py
```

2. A partir de ese momento, la Lambda Gold es **100% automática**. Cada vez que el Notebook de SageMaker suba un JSON (con miles de variables estrujadas desde el audio) a `s3://tfm-dementia-silver/features/`, esta función despertará instantáneamente y guardará la versión limpia en la capa Gold sin intervención humana.
