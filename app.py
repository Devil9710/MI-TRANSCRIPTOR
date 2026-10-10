import streamlit as st
import tempfile
import os
import time
from google import genai

st.set_page_config(page_title="Transcriptor de Audio", layout="centered")

st.title("🎙️ Mi Transcriptor de Audio a Texto")
st.write("Sube cualquier archivo de audio para obtener la transcripción exacta.")

# Si ya la escribiste en esta sesión, la recuerda
if "api_key_guardada" not in st.session_state:
    st.session_state.api_key_guardada = ""

# Intentar leer desde secrets o desde la sesión activa
api_key = st.secrets.get("GEMINI_API_KEY", "") or st.session_state.api_key_guardada

if not api_key:
    input_key = st.text_input("Pega aquí tu Gemini API Key:", type="password")
    if input_key:
        st.session_state.api_key_guardada = input_key
        api_key = input_key
        st.rerun()

if api_key:
    # Opción discreta en la barra lateral por si alguna vez quieres cambiarla
    if st.sidebar.button("Cambiar API Key"):
        st.session_state.api_key_guardada = ""
        st.rerun()

    client = genai.Client(api_key=api_key)
    
    # Modelos activos en tu cuenta
    try:
        modelos_disponibles = [
            m.name.replace("models/", "") 
            for m in client.models.list() 
            if "generateContent" in m.supported_actions
        ]
    except Exception:
        modelos_disponibles = ["gemini-3.8-flash"]

    modelo_elegido = st.sidebar.selectbox("Modelos activos en tu cuenta:", modelos_disponibles)

    archivo = st.file_uploader("Elige tu archivo de audio", type=["mp3", "wav", "m4a", "aac"])

    if archivo is not None:
        st.audio(archivo)
        
        if st.button("Comenzar Transcripción"):
            with st.spinner("Subiendo audio y procesando..."):
                extension = f".{archivo.name.split('.')[-1]}"
                with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temporal:
                    temporal.write(archivo.read())
                    ruta_temporal = temporal.name

                audio_subido = None
                try:
                    audio_subido = client.files.upload(file=ruta_temporal)
                    
                    while audio_subido.state.name == "PROCESSING":
                        time.sleep(3)
                        audio_subido = client.files.get(name=audio_subido.name)

                    if audio_subido.state.name == "FAILED":
                        raise Exception("El servidor no pudo procesar este archivo de audio.")

                    orden = (
                        "Transcribe íntegramente todo el contenido de este archivo de audio. "
                        "Hazlo de manera literal y completa, palabra por palabra, en su idioma original. "
                        "No resumas, no omitas oraciones ni diálogos."
                    )

                    st.info("Transcribiendo en vivo...")
                    area_texto = st.empty()
                    texto_completo = ""

                    for chunk in client.models.generate_content_stream(
                        model=modelo_elegido,
                        contents=[orden, audio_subido]
                    ):
                        if chunk.text:
                            texto_completo += chunk.text
                            area_texto.text_area("Texto transcrito:", texto_completo, height=400)

                    if texto_completo.strip():
                        st.success("¡Transcripción terminada con éxito!")
                        st.download_button(
                            label="Descargar transcripción (.txt)",
                            data=texto_completo,
                            file_name=f"transcripcion_{archivo.name}.txt",
                            mime="text/plain"
                        )
                    else:
                        st.warning("No se recibió respuesta de texto del modelo.")

                except Exception as error:
                    st.error(f"Ocurrió un error: {error}")
                finally:
                    if audio_subido is not None:
                        try:
                            client.files.delete(name=audio_subido.name)
                        except:
                            pass
                    if os.path.exists(ruta_temporal):
                        os.remove(ruta_temporal)
