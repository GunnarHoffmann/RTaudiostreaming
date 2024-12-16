import streamlit as st
import io
import os
from google.cloud import speech

def transcribe_streaming(audio_stream):
    """Streams audio from the microphone and transcribes it using Google Cloud Speech-to-Text."""

    client = speech.SpeechClient()

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
        model = "default" # or "latest_long" for better accuracy but higher latency
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

# Access credentials from secrets.toml
credentials_json = st.secrets["google_cloud"]["credentials"]

# Set the environment variable using the content from secrets.toml
with open("google_credentials.json", "w") as f:
    f.write(credentials_json)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"

audio_bytes = st.audio(sample_rate=16000, format="audio/wav")

if audio_bytes:
    try:
        audio_stream = io.BytesIO(audio_bytes)

        transcription_generator = transcribe_streaming(iter(lambda: audio_stream.read(4096), b''))

        st.write("Transcription:")
        transcription_placeholder = st.empty()

        for transcript in transcription_generator:
            transcription_placeholder.write(transcript)

        # Clean up the temporary credentials file (important!)
        os.remove("google_credentials.json")

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.write("Please ensure your microphone is working and the audio format is correct (raw PCM, 16kHz).")