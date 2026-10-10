import streamlit as st
import tempfile
import os
from google import genai

st.set_page_config(page_title="Transcriptor de Audio", layout="centered")

st.title("🎙️ Mi Transcriptor de Audio a Texto")
st.write("Sube cualquier archivo de audio (MP3, WAV, M4A) para obtener la transcripción exacta.")

# Configurar API Key
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    api_key = st.text_input("Pega aquí tu Gemini API Key:", type="password")

if api_key:
    client = genai.Client(api_key=api_key)
    
    archivo = st.file_uploader("Elige tu archivo de audio", type=["mp3", "wav", "m4a", "aac"])

    if archivo is not None:
        st.audio(archivo)
        
        if st.button("Comenzar Transcripción"):
            with st.spinner("Transcribiendo en la nube... Esto puede tomar unos instantes dependiendo de la duración."):
                extension = f".{archivo.name.split('.')[-1]}"
                with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temporal:
                    temporal.write(archivo.read())
                    ruta_temporal = temporal.name

                try:
                    # Subir archivo al procesador
                    audio_subido = client.files.upload(file=ruta_temporal)
                    
                    # Llamar al modelo
                    orden = (
                        "Transcribe todo el contenido de este archivo de audio de forma estrictamente "
                        "literal, palabra por palabra, en su idioma original. No resumas, no omitas "
                        "frases, no corrijas errores gramaticales del hablante ni omitas muletillas."
                    )
                    
                    respuesta = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[orden, audio_subido]
                    )
                    
                    st.success("¡Transcripción terminada con éxito!")
                    st.text_area("Texto transcrito:", respuesta.text, height=350)
                    
                    st.download_button(
                        label="Descargar transcripción (.txt)",
                        data=respuesta.text,
                        file_name=f"transcripcion_{archivo.name}.txt",
                        mime="text/plain"
                    )
                    
                    client.files.delete(name=audio_subido.name)
                    
                except Exception as error:
                    st.error(f"Ocurrió un error: {error}")
                finally:
                    if os.path.exists(ruta_temporal):
                        os.remove(ruta_temporal)
else:
    st.info("Ingresa tu API Key para habilitar la transcripción.")
