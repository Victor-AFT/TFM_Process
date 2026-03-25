# 🥈 Silver — Procesamiento de Audios

Lee los audios de S3 Bronze, extrae features acústicas y lingüísticas,
y guarda un JSON con todas las features en S3 Silver.

## Archivos

| Archivo | Qué hace |
|---------|----------|
| `01_create_notebook.py` | Crea un SageMaker Notebook Instance |

## ¿Cómo funciona?

Un SageMaker Notebook es un **Jupyter Notebook en la nube**.
No necesita Docker. Abres el notebook, instalas librerías con `pip`, y ejecutas tu código.

1. Crear Notebook → `python 01_create_notebook.py` o desde la consola AWS (ver `GUIA_BASICA_AWS.md`)
2. Instalar dependencias en el Notebook con `pip`
3. Procesar audios con tu código de `process_silver.py`
4. Subir JSON resultado a `s3://tfm-dementia-silver/features/`

## Coste

~$0.05/hora (ml.t3.medium). **Apágalo cuando termines.**

---

## 🚀 Trabajo Futuro: Automatización Total (Producción)

En este TFM, el procesamiento Silver se ejecuta **manualmente** en un Notebook. Esto es ideal para realizar una demostración académica y visual ante el tribunal (permite enseñar el código y su ejecución en vivo paso a paso).

Sin embargo, en un entorno de **producción real**, un Notebook es un antipatrón para tareas de procesamiento de datos recurrentes, ya que la arquitectura debe ser **100% reactiva y guiada por eventos**.

**¿Cómo se haría en producción?**
En lugar de un Notebook interactivo, se utilizarían **Amazon SageMaker Processing Jobs** o contenedores efímeros en **AWS ECS/Fargate**:
1. El código de `process_silver.py` y dependencias de sistema pesado (`ffmpeg`, `whisper`, `opensmile`) se empaquetan en una imagen de **Docker**.
2. Se sube dicha imagen a Amazon ECR.
3. Se configura una regla en AWS EventBridge o un S3 Trigger que detecte cuándo un nuevo audio crudo ha sido normalizado con éxito en la capa Bronze.
4. AWS levanta una máquina efímera, inyecta el contenedor de Docker, procesa el audio extrayendo las variables, vuelca el JSON en la capa Silver, y la máquina se autodestruye en segundos.

**Ventajas de la alternativa automatizada**:
- Facturación estricta por segundo de cómputo, eliminando el riesgo de incurrir en altos costes por olvidar apagar la instancia.
- Nula intervención humana, logrando una arquitectura analítica Medallion verdaderamente autónoma de principio a fin.
