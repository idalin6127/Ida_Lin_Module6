import whisper
import tempfile
import os

asr_model = whisper.load_model("small")

def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_file.flush()
        temp_path = tmp_file.name
    try:
        result = asr_model.transcribe(temp_path)
        return result["text"].strip()
    finally:
        os.remove(temp_path)
