import streamlit as st
import io
import os
from google.cloud import speech

# Set page config for wider layout
st.set_page_config(layout="wide")

def transcribe_streaming(audio_stream):
    """Streams audio from the microphone and transcribes it using Google Cloud Speech-to-Text."""

    client = speech.SpeechClient()

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",  # Change language as needed
        model="default",  # or "latest_long" for better accuracy but higher latency
    )
    streaming_config = speech.StreamingRecognitionConfig(config=config, interim_results=True)

    def generator(audio_chunks):
        for chunk in audio_chunks:
            yield speech.StreamingRecognizeRequest(audio_content=chunk)

    requests = generator(audio_stream)

    responses = client.streaming_recognize(config=streaming_config, requests=requests)

    transcript = ""
    for response in responses:
        if not response.results:
            continue

        result = response.results[0]
        if not result.alternatives:
            continue

        transcript_chunk = result.alternatives[0].transcript
        if result.is_final:
            transcript += transcript_chunk + " "
            yield transcript
            transcript = ""
        else:
            yield transcript + transcript_chunk + " (Interim)"


st.title("Real-time Speech to Text with Streamlit and Google Cloud")

# Access credentials from secrets.toml and set environment variable
try:
    credentials_json = st.secrets["google_cloud"]["credentials"]
    with open("google_credentials.json", "w") as f:
        f.write(credentials_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
except KeyError:
    st.error("Google Cloud credentials not found in secrets.toml. Please configure.")
    st.stop() # Stop execution if credentials are not found

# Audio recording
audio_bytes = st.audio(sample_rate=16000, format="audio/wav")

if audio_bytes:
    try:
        audio_stream = io.BytesIO(audio_bytes)
        transcription_generator = transcribe_streaming(iter(lambda: audio_stream.read(4096), b''))

        st.subheader("Transcription:") # Use a subheader
        transcription_placeholder = st.empty()  # Placeholder for dynamic updates

        for transcript in transcription_generator:
            transcription_placeholder.write(transcript)

        # Clean up the temporary credentials file
        os.remove("google_credentials.json")

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.write("Please ensure your microphone is working and the audio format is correct (raw PCM, 16kHz). Check Google Cloud configuration.")
        try:
            os.remove("google_credentials.json") #Try to remove it even if there is another error
        except FileNotFoundError:
            pass

elif audio_bytes is None:
    st.info("Please start recording audio.")
