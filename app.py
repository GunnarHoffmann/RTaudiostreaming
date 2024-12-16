import streamlit as st
import base64
import os
from google.cloud import speech

# Set page config for wider layout
st.set_page_config(layout="wide")

def transcribe_audio(audio_bytes, sample_rate=44100):  # Added sample_rate parameter
    """Transcribes audio using Google Cloud Speech-to-Text."""
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate,  # Use the provided sample rate
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

# JavaScript for recording (improved error handling and logging)
js_code = """
<script>
const startRecording = async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        console.log("getUserMedia success", stream);

        const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/wav' }); // Force WAV output

        const audioChunks = [];

        mediaRecorder.addEventListener("dataavailable", event => {
            console.log("dataavailable", event.data);
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        });

        mediaRecorder.addEventListener("stop", async () => {
            console.log("Recording stopped");
            try {
                const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
                const base64 = await blobToBase64(audioBlob);
                Streamlit.setComponentValue(base64);

                const audio = new Audio(URL.createObjectURL(audioBlob));
                audio.onloadedmetadata = function() {
                  console.log("Audio sample rate:", audio.sampleRate);
                  Streamlit.set({sample_rate_js: audio.sampleRate})
                };

            } catch (blobError) {
                console.error("Error creating Blob or converting to base64:", blobError);
            }
        });

        mediaRecorder.addEventListener("error", error => {
            console.error("MediaRecorder error:", error);
        });

        mediaRecorder.start();
        setTimeout(() => {
            console.log("Stopping recording after 5 seconds");
            mediaRecorder.stop();
        }, 5000);

    } catch (error) {
        console.error("Error accessing microphone:", error);
        if (error.name === "NotAllowedError") {
          alert("Microphone permission denied. Please allow access in your browser settings.");
        }
    }
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

audio_base64 = st.session_state.get("component_value", None)
sample_rate_js = st.session_state.get("sample_rate_js", None)

if audio_base64:
    try:
        audio_bytes = base64.b64decode(audio_base64.split(",")[1])
        st.write(f"Sample Rate from browser: {sample_rate_js}")
        transcript = transcribe_audio(audio_bytes, sample_rate_js) # Pass the sample rate to transcription

        if transcript:
            st.write("Transcription:")
            st.write(transcript)
        os.remove("google_credentials.json")
    except Exception as e:
        st.error(f"Error processing audio or transcription: {e}")
        try:
            os.remove("google_credentials.json")
        except FileNotFoundError:
            pass
elif audio_base64 is None:
    st.info("Click 'Record 5 Seconds' to start recording.")
