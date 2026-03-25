# Memoria del Proyecto TFM: Detección de Demencia por Voz

## 1. Solución Técnica

El objetivo de este proyecto es desarrollar un sistema automatizado capaz de procesar grabaciones de voz de pacientes para extraer características acústicas y lingüísticas que ayuden en la detección temprana de la demencia (como el Alzheimer). 

Para lograrlo, se ha construido un pipeline (una tubería de datos) en la nube de Amazon Web Services (AWS) basado en la **Arquitectura Medallion**. Esta arquitectura divide el proceso en tres capas progresivas de calidad de datos:
- **Capa Bronze (Raw):** Donde aterrizan los audios crudos originales subidos por los médicos y se normaliza su volumen a un estándar unificado.
- **Capa Silver (Procesado):** Donde un entorno de Inteligencia Artificial (SageMaker) extrae todas las métricas de la voz (tono, pausas, texto transcrito) usando librerías avanzadas como Whisper u OpenSMILE.
- **Capa Gold (Consolidado):** Donde de forma automática se limpian y filtran exclusivamente las variables más importantes (unas 44 características clave) dejándolas listas para entrenar un modelo predictivo de Machine Learning.

## 2. Requerimientos

### Requisitos Funcionales (¿Qué debe hacer el sistema?)
1. **Ingesta de audios:** El sistema debe permitir subir archivos de audio en formato `.wav` a través de una interfaz web sencilla.
2. **Normalización automática:** Todo audio ingresado debe ser normalizado a un volumen estándar (0.1 RMS) de forma completamente automática sin intervención humana.
3. **Extracción de características (Features):** El sistema debe ser capaz de transcribir la voz a texto y extraer más de 100 parámetros físicos del sonido de la voz.
4. **Filtrado y limpieza:** El sistema debe depurar los datos, eliminando variables inútiles y aplanando la información para entregar un archivo final limpio que un modelo de Machine Learning pueda entender.
5. **Archivado en frío:** Los audios originales deben moverse automáticamente a un almacenamiento barato (Glacier) al acabar el día para ahorrar costes.

### Requisitos No Funcionales (¿Cómo debe comportarse?)
1. **Escalabilidad:** Al usar almacenamiento en S3 y funciones Lambda (Serverless), el sistema debe poder procesar desde 1 audio hasta miles de audios simultáneos sin que se sature.
2. **Seguridad:** Los accesos a los distintos servicios de procesado en la nube deben estar restringidos y protegidos mediante roles de seguridad de AWS (IAM Roles).
3. **Rendimiento y Automatización (Arquitectura basada en eventos):** El paso de la capa Bronze a la Silver, y de la Silver a la Gold, debe estar diseñado para reaccionar a eventos (Event-Driven). Es decir, los procesos deben dispararse solos en cuanto caiga un archivo nuevo, sin esperar procesos manuales ni servidores encendidos 24 horas.
4. **Bajo Coste (Eficiencia):** La infraestructura debe apagarse cuando no se usa (pago por uso) para garantizar que los costes operativos mensuales sean mínimos, del orden de céntimos en entornos de desarrollo.

## 3. Arquitectura y Elementos

El diseño del sistema sigue un planteamiento moderno de **Arquitectura Basada en Eventos (Event-Driven Architecture)**, lo que significa que no existe un servidor central dando órdenes (orquestador), sino que cada componente reacciona automáticamente cuando detecta datos nuevos. 

Los componentes interactúan de la siguiente manera:

1. **Frontend (Capa de Usuario):** Una aplicación interactiva desarrollada en Streamlit permite al usuario subir un archivo `.wav`. Mediante la librería `boto3`, la aplicación se conecta a la nube y deposita el archivo en Amazon S3. 
2. **Sistema de Almacenamiento (Amazon S3):** Actúa como el sistema circulatorio del proyecto. Se divide lógicamente en los niveles de la *Medallion Architecture*:
   - `s3://...-bronze/raw/` (Aterrizaje del audio original)
   - `s3://...-bronze/norm/` (Audio normalizado)
   - `s3://...-silver/features/` (JSON masivo con todas las features)
   - `s3://...-gold/features/` (JSON limpio para Machine Learning)
3. **Motores de Computación Reactiva (AWS Lambda):** Se utilizan dos microservicios *Serverless* programados en Python:
   - *Bronze Lambda:* Salta automáticamente al caer un audio en `raw/`, ejecutando la normalización de volumen (RMS 0.1).
   - *Gold Lambda:* Reacciona automáticamente al caer un JSON en Silver, y ejecuta un script de aplanado de datos para dejar únicamente las 44 variables necesarias.
4. **Motor de Inteligencia Artificial (Amazon SageMaker):** Actúa como puente entre Bronze y Silver. Se encarga del procesamiento computacional pesado descargando modelos acústicos, transcribiendo texto con Whisper y extrayendo frecuencias con OpenSMILE y Librosa.

*(Nota: En este apartado del documento Word se incluirá el diagrama visual exportado `arquitectura_medallion.drawio` con los logos oficiales de AWS).*

## 4. Infraestructura

La infraestructura se ha desplegado dividiendo tareas entre un entorno local y el poder de la nube.

- **Infraestructura Cloud (AWS):** Al ser servicios gestionados (*PaaS/SaaS*), no hay servidores tradicionales.
  - **Almacenamiento Ilimitado:** Amazon S3. Se complementa con Amazon S3 Glacier mediante una regla (*Lifecycle Rule*) que manda los audios crudos al archivo profundo a los 0 días de ser procesados para minimizar costes.
  - **Procesamiento de Eventos:** AWS Lambda, asignándole configuraciones de Memoria RAM de 128MB a 512MB.
  - **Entorno de Machine Learning:** Amazon SageMaker (*Notebook Instance ml.t3.medium*).
  - **Monitorización y Logs:** Amazon CloudWatch, usado para observar cada ejecución y auditar errores.

- **Entorno Local / Cliente:**
  - **Hardware del usuario:** Ordenador estándar con navegador web y micrófono.
  - **Visual Studio Code (VSCode):** El entorno de desarrollo gráfico (*IDE*) utilizado para picar todo el proyecto.

## 5. Volumetría y Escalabilidad

El conjunto de datos de entrenamiento esperado es el dataset **ADReSSo21** (Alzheimer's Dementia Recognition through Spontaneous Speech), con unos 237 audios originales (aprox. 500-800 MB de peso total). 
Sin embargo, el sistema ha sido diseñado como un cuello de botella abierto. Gracias al diseño *Serverless* (Lambdas) y el *Event-Driven*:
- **Fase de Ingesta y Bronze:** Las funciones Lambda admiten un nivel de concurrencia de hasta 1000 ejecuciones simultáneas. Podrían subirse cientos de audios al mismo tiempo y AWS levantaría automáticamente a cientos de Lambdas en paralelo.
- **Fase Silver:** En caso de llegar a producción de alto volumen, el Notebook de pruebas de SageMaker se encapsularía en un contenedor Docker y se transformaría en un *SageMaker Processing Job* automático, adaptando su memoria RAM sin límites.

## 6. Costes Operativos

El uso del modelo *Pay-as-you-go* de AWS garantiza una eficiencia radical, ideal para investigaciones médicas sin financiación de grandes clusters.

| Servicio | Coste Estimado Mensual | Justificación de Optimización |
| :--- | :--- | :--- |
| **Amazon S3** | < $0.05 | Almacenamiento Estándar para JSON. Los archivos `.wav` pesados se purgan a nivel Glacier para recortar un 90% el coste físico. |
| **AWS Lambda** | $0.00 (Free Tier) | El volumen de procesamiento (normalización y purgado de JSON) queda absorbido enteramente por el Tier Gratuito (1 millón de peticiones al mes). |
| **SageMaker Notebook**| ~$1.00 - $3.00 | Uso esporádico del servidor `ml.t3.medium` ($0.046/hora). Únicamente se enciende durante el procesamiento masivo de datos hacia Silver. |
| **Transferencia Datos**| $0.00 | La subida a AWS y tráfico interno entre regiones es gratuito o despreciable. |
| **TOTAL** | **< $5.00 mensuales** | Un coste mínimo e hiper-estratégico frente a servidores encendidos 24/7. |

## 7. Fuentes de Datos

La fuente primaria empleada es el dataset **ADReSSo** (proveniente del reto INTERSPEECH 2021), compuesto por grabaciones de lectura espontánea donde se pide al paciente describir la imagen del *"Robo de Galletas"*.
- **Formato y Calidad:** Archivos de audio digital `.wav`. Al venir de grabaciones diversas, se encuentran inconsistencias en los micrófonos, por lo cual la **fase fundamental de limpieza es la homogenización del volumen (Normalización a 0.1 RMS)** en la capa Bronze.
- **Etiquetado:** Clínicamente catalogados en dos universos: `dementia` y `nodementia`.

## 8. Productos y Librerías Necesarios

| Herramienta | Versión | Descripción |
| :--- | :--- | :--- |
| **Python** | 3.12 / 3.10 | Lenguaje principal del proyecto (3.12 en Lambdas, 3.10 en SageMaker). |
| **Jupyter** | — | Formato interactivo de los ficheros (.ipynb) para explorar datos. |
| **Google Colab** | — | Entorno alternativo de nube que se puede utilizar para aprovechar GPUs gratis y conexión a Drive si se requiriera modelado pesado externo. |
| **AWS (Diversos)** | Varios | Boto3 SDK, S3, IAM, CloudWatch, Lambda y SageMaker. Infraestructura central. |
| **FFmpeg** | — | Motor procesador en segundo plano, necesario para que Whisper descifre los `.wav`. |
| **Visual Code** | — | Entorno de desarrollo Gráfico (IDE) para el montaje de Streamlit y Lambdas. |
| **Streamlit** | 1.x | Framework web en Python utilizado para la App interactiva local de subida de audios. |
| **Whisper (OpenAI)**| Base | Librería de IA para la transcripción voz-a-texto de alta precisión. |
| **OpenSMILE & Librosa**| — | Frameworks top mundiales en psicoacústica para calcular *Features* de voz (Jitter, Shimmer, RMS). |

## 9. Plan de Trabajo

1. **Fase 1 (Semana 1-2):** Análisis de viabilidad de los datos acústicos (Inspirado en Papers del ADReSSo) y diseño del modelo Cloud en AWS.
2. **Fase 2 (Semana 3):** Creación del Landing Zone en S3 e implementación del Crawler local usando la Interfaz Streamlit y Boto3.
3. **Fase 3 (Semana 4):** Despliegue de Amazon Lambda (Capa Bronze) programada en Python para normalizar el volumen sin servidores y archivar en Glacier.
4. **Fase 4 (Semana 5-6):** Montaje de la Inteligencia Artificial (Capa Silver). Configurar librerías acústicas (Librosa, OpenSMILE, Whisper, spaCy) en un kernel `conda_pytorch_p310` de SageMaker Notebooks.
5. **Fase 5 (Semana 7):** Despliegue de la Transformación Final de IA (Capa Gold). Lambda en Python que reacciona limpiando unas 150 variables sobrantes a tan solo 44 válidas para los algoritmos predictivos.
6. **Fase 6 (Semana 8-9):** Entrenamiento de Algoritmos (Random Forest / SVM) sobre el fichero JSON Gold resultante, testing y compilación textual de la Memoria del Proyecto.
