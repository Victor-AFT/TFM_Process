import streamlit as st
import boto3
import uuid
from datetime import datetime
import io

# Configuración básica
st.set_page_config(
    page_title="TFM - Ingesta de Audio (Detección Demencia)",
    page_icon="🎙️",
    layout="centered"
)

# Constantes
INGESTA_BUCKET = "tfm-dementia-bronze"  # Usamos el bucket bronze, pero en la carpeta raw/

def upload_to_s3(file_buffer, bucket, key):
    """Sube un archivo a S3."""
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_fileobj(
            file_buffer,
            bucket,
            key,
            ExtraArgs={'ContentType': 'audio/wav'}
        )
        return True
    except Exception as e:
        st.error(f"❌ Error subiendo a S3: {e}")
        return False

# Interfaz de Usuario
st.title("🎙️ Plataforma de Ingesta de Voz")
st.markdown("""
Esta aplicación permite a los usuarios subir muestras de voz (`.wav`). 
Los archivos se enviarán al **Landing Zone (S3 Ingesta)**, desde donde se procesarán automáticamente
y se archivarán de forma segura en **AWS Glacier**.
""")

st.divider()

# Formulario de subida/grabación
with st.form("upload_form"):
    st.subheader("Capturar Muestra de Audio")
    
    # Campo para seleccionar categoría (Etiquetado manual para entrenamiento)
    categoria = st.selectbox(
        "Diagnóstico Clínico (Categoría):",
        options=["nodementia", "dementia"],
        format_func=lambda x: "Desarrollo Típico (No Demencia)" if x == "nodementia" else "Paciente con Demencia"
    )
    
    # Identificador del paciente (opcional, si está vacío se autogenera)
    paciente_id = st.text_input("ID del Paciente (Opcional)", placeholder="Ej: PAC-001")
    
    tab1, tab2 = st.tabs(["🎙️ Grabar Audio", "📁 Subir Archivo"])
    
    with tab1:
        st.info("Presiona el micrófono para empezar a grabar tu muestra.")
        recorded_audio = st.audio_input("Graba la muestra del paciente")
    
    with tab2:
        uploaded_file = st.file_uploader("O selecciona un archivo (.wav)", type=["wav"])
    
    # Botón de envío
    submit_button = st.form_submit_button(label="Enviar a AWS", use_container_width=True)

# Lógica de procesamiento
if submit_button:
    # Usamos el grabado si existe, sino el subido
    audio_data = recorded_audio if recorded_audio else uploaded_file
    
    if audio_data is None:
        st.warning("⚠️ Por favor, graba un audio o selecciona un archivo para subir.")
    else:
        with st.spinner("Enviando y encriptando en AWS..."):
            
            # Generar nombre único para el archivo
            if not paciente_id:
                paciente_id = f"anon-{str(uuid.uuid4())[:8]}"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_ext = "wav" # audio_input siempre devuelve WAV
            
            # Formato: raw/categoria/paciente_id_timestamp.wav -> ej: raw/dementia/PAC-001_20260302_120000.wav
            s3_key = f"raw/{categoria}/{paciente_id}_{timestamp}.{file_ext}"
            
            # Subir usando el buffer de Streamlit
            success = upload_to_s3(audio_data, INGESTA_BUCKET, s3_key)
            
            if success:
                st.success("✅ ¡Audio subido correctamente a S3 Ingesta!")
                st.info(f"📁 **Ruta de destino:** `s3://{INGESTA_BUCKET}/{s3_key}`")
                st.markdown("> *El audio será procesado inmediatamente en Bronze y luego archivado en Glacier para cold storage.*")

# Instrucciones laterales
with st.sidebar:
    st.header("⚙️ Estado del Sistema")
    st.info("🟢 S3 Connectivity: Activa (Requiere AWS Credentials locales)")
    st.markdown("""
    ### Arquitectura del Flujo:
    1. **Web App**: Sube el `.wav` original.
    2. **S3 Ingesta**: Recibe el archivo Raw.
    3. **Glacier rule**: Archivado a los 0 días.
    4. **Lambda Transform**: Normaliza el audio y lo pasa a Bronze.
    """)
