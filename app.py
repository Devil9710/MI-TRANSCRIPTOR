import streamlit as st
import tempfile
import os
import time
from google import genai

st.set_page_config(page_title="Transcriptor de Audio", layout="centered")

st.title("🎙️ Mi Transcriptor de Audio a Texto")
st.write("Sube cualquier archivo de audio (MP3, WAV, M4A) para obtener la transcripción exacta.")

modelo = st.sidebar.selectbox(
    "Modelo de IA:",
    ["gemini-3.8-flash", "gemini-3.5-transcribe"]
)

api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    api_key = st.text_input("Pega aquí tu Gemini API Key:", type="password")

if api_key:
    client = genai.Client(api_key=api_key)
    archivo = st.file_uploader("Elige tu archivo de audio", type=["mp3", "wav", "m4a", "aac"])

    if archivo is not None:
        st.audio(archivo)
        
        if st.button("Comenzar Transcripción"):
            with st.spinner("Procesando y transcribiendo en la nube... Esto puede tomar unos instantes."):
                extension = f".{archivo.name.split('.')[-1]}"
                with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temporal:
                    temporal.write(archivo.read())
                    ruta_temporal = temporal.name

                audio_subido = None
                try:
                    # 1. Subir archivo
                    audio_subido = client.files.upload(file=ruta_temporal)
                    
                    # 2. Esperar hasta que el archivo esté procesado en Google
                    with st.spinner("Verificando procesamiento del archivo en la nube..."):
                        while audio_subido.state.name == "PROCESSING":
                            time.sleep(3)
                            audio_subido = client.files.get(name=audio_subido.name)

                        if audio_subido.state.name == "FAILED":
                            raise Exception("El servidor no pudo procesar el archivo de audio subido.")

                    orden = (
                        "Transcribe todo el contenido de este archivo de audio de forma estrictamente "
                        "literal, palabra por palabra, en su idioma original. No resumas, no omitas "
                        "frases, no corrijas errores gramaticales del hablante ni omitas muletillas."
                    )

                    # 3. Solicitud con reintento para evitar errores 503
                    respuesta = None
                    for intento in range(3):
                        try:
                            respuesta = client.models.generate_content(
                                model=modelo,
                                contents=[orden, audio_subido]
                            )
                            break
                        except Exception as e:
                            if "503" in str(e) and intento < 2:
                                time.sleep(6)
                                continue
                            raise e

                    texto_resultado = respuesta.text if (respuesta and respuesta.text) else ""

                    if texto_resultado.strip():
                        st.success("¡Transcripción terminada con éxito!")
                        st.text_area("Texto transcrito:", texto_resultado, height=350)

                        st.download_button(
                            label="Descargar transcripción (.txt)",
                            data=texto_resultado,
                            file_name=f"transcripcion_{archivo.name}.txt",
                            mime="text/plain"
                        )
                    else:
                        st.warning("El modelo completó la solicitud pero no devolvió texto. Prueba cambiando el modelo en la barra lateral.")

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
else:
    st.info("Ingresa tu API Key para habilitar la transcripción.")
