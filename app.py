import streamlit as st
import base64
import io
import os
from google.cloud import speech

# Set page config for wider layout
st.set_page_config(layout="wide")

def transcribe_audio(audio_bytes):
    """Transcribes audio using Google Cloud Speech-to-Text."""
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=44100,  # Important: Match recording sample rate
        language_code="en-US",
    )
    try:
        response = client.recognize(config=config, audio=audio)
        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript + " "
        return transcript.strip()
    except Exception as e:
        st.error(f"Transcription error: {e}")
        return None

st.title("WebRTC Audio Recorder with Streamlit and Google Cloud Speech-to-Text")

# Access credentials from secrets.toml and set environment variable
try:
    credentials_json = st.secrets["google_cloud"]["credentials"]
    with open("google_credentials.json", "w") as f:
        f.write(credentials_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
except KeyError:
    st.error("Google Cloud credentials not found in secrets.toml. Please configure.")
    st.stop()

# JavaScript for recording
js_code = """
<script>
const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    const mediaRecorder = new MediaRecorder(stream);
    const audioChunks = [];

    mediaRecorder.addEventListener("dataavailable", event => {
        audioChunks.push(event.data);
    });

    mediaRecorder.addEventListener("stop", async () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/wav" }); // Important: use wav
        const base64 = await blobToBase64(audioBlob);
        Streamlit.setComponentValue(base64);
    });

    mediaRecorder.start();
    setTimeout(() => mediaRecorder.stop(), 5000); // Stop after 5 seconds (adjust as needed)
};

const blobToBase64 = blob => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = reject;
    reader.onload = () => resolve(reader.result);
    reader.readAsDataURL(blob);
});

const btn = document.createElement('button');
btn.innerHTML = 'Record 5 Seconds';
btn.onclick = startRecording;
document.body.appendChild(btn);
</script>
"""

st.components.v1.html(js_code)

# Get the audio data from the frontend
audio_base64 = st.session_state.get("component_value", None)

if audio_base64:
    try:
        audio_bytes = base64.b64decode(audio_base64.split(",")[1]) # Split to remove data url part
        transcript = transcribe_audio(audio_bytes)

        if transcript:
            st.write("Transcription:")
            st.write(transcript)

        os.remove("google_credentials.json") #Cleanup
    except Exception as e:
        st.error(f"Error processing audio or transcription: {e}")
        try:
            os.remove("google_credentials.json") #Cleanup
        except FileNotFoundError:
            pass
elif audio_base64 is None:
    st.info("Click 'Record 5 Seconds' to start recording.")
