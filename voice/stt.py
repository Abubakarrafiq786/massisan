import sounddevice as sd
import numpy as np
import webrtcvad
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
import os
from core.logger import get_logger

log = get_logger(__name__)

class SpeechRecognizer:
    def __init__(self, model_size="small", device="cpu", compute_type="int8"):
        log.info(f"Loading Whisper model '{model_size}' on {device}...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.vad = webrtcvad.Vad(2) # 0 to 3. 3 is most aggressive at filtering out silence.
        log.info("Whisper and VAD models loaded successfully.")

    def record_and_transcribe(self, filename="temp_audio.wav", language: str | None = None) -> str:
        sample_rate = 16000
        frame_duration = 30 # 30ms chunks is standard for WebRTC VAD
        frame_size = int(sample_rate * frame_duration / 1000) # 480 samples
        
        log.info("Listening... Speak now!")
        
        audio_data = []
        silent_frames = 0
        started_talking = False
        
        # Start the stream
        stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=frame_size)
        stream.start()
        
        try:
            while True:
                # Read a 30ms chunk of audio
                chunk, _ = stream.read(frame_size)
                chunk_bytes = chunk.tobytes()
                
                # Check if this chunk has voice
                is_speech = self.vad.is_speech(chunk_bytes, sample_rate)
                
                if is_speech:
                    started_talking = True
                    silent_frames = 0
                    audio_data.append(chunk)
                elif started_talking:
                    # We allow a 1-second pause (about 33 frames) before assuming you are done
                    silent_frames += 1
                    audio_data.append(chunk) 
                    if silent_frames > 33: 
                        log.info("Silence detected. Stopping recording.")
                        break
        finally:
            stream.stop()
            stream.close()

        if not audio_data:
            return ""

        # Save the recorded chunks to a file
        final_audio = np.concatenate(audio_data, axis=0)
        write(filename, sample_rate, final_audio)
        
        log.info("Transcribing...")
        segments, _ = self.model.transcribe(filename, beam_size=5, language=language)
        transcript = " ".join([segment.text for segment in segments])
        
        if os.path.exists(filename):
            os.remove(filename)
            
        return transcript.strip()