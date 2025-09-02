# tts.py  —— Use TTS to synthesize audible speech
import tempfile
from TTS.api import TTS

def synthesize_speech(text: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        path = tmp.name
    
    # Use TTS to generate speech
    tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
    tts.tts_to_file(text=text, file_path=path)
    return path