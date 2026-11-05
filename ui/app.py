import sys
import httpx
import numpy as np
import sounddevice as sd
import webrtcvad
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
import os

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                               QLabel, QDialog)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont

from core.logger import get_logger

log = get_logger(__name__)

# --- 1. Load Whisper globally so it stays in memory ---
log.info("Initializing Whisper model... This might take a moment on startup.")
WHISPER_MODEL = WhisperModel("small", device="cpu", compute_type="int8")
log.info("Whisper model loaded successfully.")

# --- 2. Backend Communication Thread ---
class AIWorker(QThread):
    response_ready = Signal(str)
    
    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt

    def run(self):
        try:
            response = httpx.post(
                "http://127.0.0.1:8000/api/v1/chat", 
                json={"prompt": self.prompt},
                timeout=60.0
            )
            data = response.json()
            self.response_ready.emit(data.get("response", "Error: No response text."))
        except Exception as e:
            self.response_ready.emit(f"Connection Error: Make sure the FastAPI backend is running.\nDetails: {e}")

# --- 3. Audio Recording Thread ---
class AudioWorker(QThread):
    text_ready = Signal(str)
    status_update = Signal(str)
    
    def run(self):
        try:
            vad = webrtcvad.Vad(0)
            sample_rate = 16000
            frame_duration = 30
            frame_size = int(sample_rate * frame_duration / 1000)
            
            self.status_update.emit("Listening... Speak now!")
            
            audio_data = []
            silent_frames = 0
            started_talking = False
            initial_silence_frames = 0
            
            stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=frame_size)
            stream.start()
            
            while True:
                chunk, overflowed = stream.read(frame_size)
                chunk_bytes = chunk.tobytes()
                is_speech = vad.is_speech(chunk_bytes, sample_rate)
                
                if is_speech:
                    started_talking = True
                    silent_frames = 0
                    initial_silence_frames = 0
                    audio_data.append(chunk)
                else:
                    if not started_talking:
                        initial_silence_frames += 1
                        # 3 seconds of initial silence = 100 frames
                        if initial_silence_frames > 100:
                            self.status_update.emit("No speech detected. Cancelled.")
                            stream.stop()
                            stream.close()
                            self.text_ready.emit("")
                            return
                    else:
                        silent_frames += 1
                        audio_data.append(chunk)
                        # 1.5 seconds of silence after talking
                        if silent_frames > 50: 
                            break
                            
            stream.stop()
            stream.close()
            
            if not audio_data:
                self.text_ready.emit("")
                return
                
            self.status_update.emit("Transcribing...")
            final_audio = np.concatenate(audio_data, axis=0)
            write("temp_audio.wav", sample_rate, final_audio)
            
            segments, info = WHISPER_MODEL.transcribe("temp_audio.wav", beam_size=5)
            transcript = " ".join([segment.text for segment in segments])
            
            if os.path.exists("temp_audio.wav"):
                os.remove("temp_audio.wav")
                
            self.text_ready.emit(transcript.strip())
            
        except Exception as e:
            log.error(f"Audio error: {e}")
            self.text_ready.emit("")
# --- 3. Audio Recording Thread ---
# --- 3. Audio Recording Thread ---
class AudioWorker(QThread):
    text_ready = Signal(str)
    status_update = Signal(str)
    error_ready = Signal(str)
    
    def run(self):
        try:
            vad = webrtcvad.Vad(0) # 0 = least aggressive (listens to everything)
            sample_rate = 16000
            frame_duration = 30
            frame_size = int(sample_rate * frame_duration / 1000)
            
            self.status_update.emit("Listening... Speak now!")
            
            audio_data = []
            silent_frames = 0
            started_talking = False
            initial_silence_frames = 0
            
            # Changed to 6 (DirectSound) to avoid MME driver issues
            mic_index = 6 
            
            device_info = sd.query_devices(mic_index)
            log.info(f"Listening to Microphone: {device_info['name']}")
            
            stream = sd.InputStream(
                samplerate=sample_rate, 
                channels=1, 
                dtype='int16', 
                blocksize=frame_size,
                device=mic_index
            )
            stream.start()
            
            while True:
                chunk, overflowed = stream.read(frame_size)
                chunk_bytes = chunk.tobytes()
                
                # Calculate volume (max amplitude in this chunk)
                volume = np.max(np.abs(chunk))
                
                # --- DEBUG PRINTS ---
                # If you speak and this stays at 0, Python is blocked from the mic!
                if volume > 5: 
                    print(f"Mic Volume detected: {volume}") 
                # --------------------

                is_speech = vad.is_speech(chunk_bytes, sample_rate)
                
                if is_speech:
                    started_talking = True
                    silent_frames = 0
                    initial_silence_frames = 0
                    audio_data.append(chunk)
                else:
                    if not started_talking:
                        initial_silence_frames += 1
                        if initial_silence_frames > 100: # 3 seconds of silence
                            self.status_update.emit("No speech detected. Cancelled.")
                            stream.stop()
                            stream.close()
                            self.text_ready.emit("")
                            return
                    else:
                        silent_frames += 1
                        audio_data.append(chunk)
                        if silent_frames > 50: # 1.5 seconds of silence
                            break
                            
            stream.stop()
            stream.close()
            
            if not audio_data:
                self.text_ready.emit("")
                return
                
            self.status_update.emit("Transcribing...")
            final_audio = np.concatenate(audio_data, axis=0)
            write("temp_audio.wav", sample_rate, final_audio)
            
            segments, info = WHISPER_MODEL.transcribe("temp_audio.wav", beam_size=5)
            transcript = " ".join([segment.text for segment in segments])
            
            if os.path.exists("temp_audio.wav"):
                os.remove("temp_audio.wav")
                
            self.text_ready.emit(transcript.strip())
            
        except Exception as e:
            log.error(f"Audio error: {e}")
            self.text_ready.emit("")
    text_ready = Signal(str)
    status_update = Signal(str)
    
    def run(self):
        try:
            # Lowered VAD aggressiveness from 2 to 1 so it picks up quieter mics
            vad = webrtcvad.Vad(1) 
            sample_rate = 16000
            frame_duration = 30
            frame_size = int(sample_rate * frame_duration / 1000)
            
            self.status_update.emit("Listening... Speak now!")
            
            audio_data = []
            silent_frames = 0
            started_talking = False
            initial_silence_frames = 0
            
            # ---> CHANGE THIS NUMBER if your mic is not device 1 <---
            mic_index = 1 
            
            # Print the active mic to terminal so we know it's working
            device_info = sd.query_devices(mic_index)
            log.info(f"Listening to Microphone: {device_info['name']}")
            
            stream = sd.InputStream(
                samplerate=sample_rate, 
                channels=1, 
                dtype='int16', 
                blocksize=frame_size,
                device=mic_index # Force Python to use this mic
            )
            stream.start()
            
            while True:
                chunk, overflowed = stream.read(frame_size)
                chunk_bytes = chunk.tobytes()
                is_speech = vad.is_speech(chunk_bytes, sample_rate)
                
                if is_speech:
                    started_talking = True
                    silent_frames = 0
                    initial_silence_frames = 0
                    audio_data.append(chunk)
                else:
                    if not started_talking:
                        initial_silence_frames += 1
                        # 3 seconds of initial silence = 100 frames
                        if initial_silence_frames > 100:
                            self.status_update.emit("No speech detected. Cancelled.")
                            stream.stop()
                            stream.close()
                            self.text_ready.emit("")
                            return
                    else:
                        silent_frames += 1
                        audio_data.append(chunk)
                        # 1.5 seconds of silence after talking
                        if silent_frames > 50: 
                            break
                            
            stream.stop()
            stream.close()
            
            if not audio_data:
                self.text_ready.emit("")
                return
                
            self.status_update.emit("Transcribing...")
            final_audio = np.concatenate(audio_data, axis=0)
            write("temp_audio.wav", sample_rate, final_audio)
            
            segments, info = WHISPER_MODEL.transcribe("temp_audio.wav", beam_size=5)
            transcript = " ".join([segment.text for segment in segments])
            
            if os.path.exists("temp_audio.wav"):
                os.remove("temp_audio.wav")
                
            self.text_ready.emit(transcript.strip())
            
        except Exception as e:
            log.exception("Audio recording or transcription failed")
            self.error_ready.emit(str(e))
# --- 4. Visual Overlay ---
class RecorderOverlay(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 120)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        self.label = QLabel("Listening...")
        self.label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.label.setStyleSheet("color: #00d2ff;")
        self.label.setAlignment(Qt.AlignCenter)
        
        self.mic_icon = QLabel("🎤")
        self.mic_icon.setFont(QFont("Segoe UI", 30))
        self.mic_icon.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.mic_icon)
        layout.addWidget(self.label)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                border: 2px solid #00d2ff;
                border-radius: 15px;
            }
        """)

    def update_status(self, text):
        self.label.setText(text)
        if "Cancelled" in text:
            self.mic_icon.setText("❌")
        elif "Transcribing" in text:
            self.mic_icon.setText("⏳")

# --- 5. Main Window ---
class JarvisWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS AI - Desktop")
        self.resize(800, 600)
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        title = QLabel("J.A.R.V.I.S.")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #00d2ff; margin-bottom: 10px;")
        layout.addWidget(title)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border-radius: 15px;
                padding: 10px 15px;
                font-size: 16px;
            }
            QPushButton:hover { background-color: #555; }
            QPushButton:disabled { background-color: #2b2b2b; color: #666; }
        """)
        self.mic_btn.clicked.connect(self.record_audio)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your command or click the mic...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 15px;
                padding: 10px;
                font-size: 14px;
                color: white;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d2ff;
                color: black;
                border-radius: 15px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #00a8cc; }
            QPushButton:disabled { background-color: #555; color: #888; }
        """)
        self.send_btn.clicked.connect(self.send_message)

        input_layout.addWidget(self.mic_btn)
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

        self.append_message("JARVIS", "Systems online. How can I assist you today, Sir?")

    def append_message(self, sender, message):
        if sender == "You":
            self.chat_display.append(f"<b style='color: #00d2ff;'>You:</b> <span style='color: #ddd;'>{message}</span><br>")
        else:
            self.chat_display.append(f"<b style='color: #ff0055;'>JARVIS:</b> <span style='color: #ddd;'>{message}</span><br>")

    def record_audio(self):
        self.mic_btn.setEnabled(False)
        self.mic_btn.setText("🔴")
        
        self.overlay = RecorderOverlay(self)
        self.overlay.show()
        
        self.audio_worker = AudioWorker()
        self.audio_worker.status_update.connect(self.overlay.update_status)
        self.audio_worker.text_ready.connect(self.on_audio_transcribed)
        self.audio_worker.error_ready.connect(self.on_audio_error)
        self.audio_worker.start()

    def on_audio_error(self, error):
        QTimer.singleShot(500, self.overlay.close)
        self.mic_btn.setEnabled(True)
        self.mic_btn.setText("🎤")
        self.append_message("System", f"Audio error: {error}")

    def on_audio_transcribed(self, text):
        QTimer.singleShot(500, self.overlay.close)
        
        self.mic_btn.setEnabled(True)
        self.mic_btn.setText("🎤")
        
        if text:
            self.input_field.setText(text)
            self.send_message()
        else:
            self.append_message("System", "Recording cancelled or no speech detected.")

    def send_message(self):
        prompt = self.input_field.text().strip()
        if not prompt:
            return

        self.input_field.clear()
        self.append_message("You", prompt)
        self.send_btn.setEnabled(False)
        self.send_btn.setText("...")

        self.worker = AIWorker(prompt)
        self.worker.response_ready.connect(self.on_response_received)
        self.worker.start()

    def on_response_received(self, response_text):
        self.append_message("JARVIS", response_text)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")

    # This prevents the QThread destroyed error when closing the app
    def closeEvent(self, event):
        if hasattr(self, 'audio_worker') and self.audio_worker.isRunning():
            self.audio_worker.terminate()
            self.audio_worker.wait()
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JarvisWindow()
    window.show()
    sys.exit(app.exec())