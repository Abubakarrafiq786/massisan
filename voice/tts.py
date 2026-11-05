import os
import subprocess
from pathlib import Path

import sounddevice as sd
from scipy.io.wavfile import read
from core.logger import get_logger
from voice.language import detect_text_language

log = get_logger(__name__)

class TextToSpeech:
    def __init__(
        self,
        model_path="models/en_US-lessac-medium.onnx",
        urdu_model_path="models/ur_PK-fasih-medium.onnx",
    ):
        project_root = Path(__file__).resolve().parents[1]
        self.model_paths = {
            "en": Path(model_path) if Path(model_path).is_absolute() else project_root / model_path,
            "ur": Path(urdu_model_path)
            if Path(urdu_model_path).is_absolute()
            else project_root / urdu_model_path,
        }
        log.info("TTS Engine initialized.")

    def speak(self, text: str, language: str | None = None):
        if not text:
            return

        language = language or detect_text_language(text) or "en"
        model_path = self.model_paths.get(language, self.model_paths["en"])
        if not model_path.is_file():
            if language == "ur":
                raise FileNotFoundError(
                    f"Urdu Piper voice model is missing: {model_path}. "
                    "Download model.onnx and config.json from "
                    "https://huggingface.co/Keshavji/piper-ur_PK-fasih-medium "
                    "and save them as models/ur_PK-fasih-medium.onnx and "
                    "models/ur_PK-fasih-medium.onnx.json."
                )
            raise FileNotFoundError(f"Piper voice model is missing: {model_path}")

        log.info("Speaking response in %s", language)
        output_file = Path(__file__).resolve().parents[1] / "output.wav"
        command = [
            "piper",
            "--model", str(model_path),
            "--output_file", str(output_file),
        ]

        try:
            piper_env = os.environ.copy()
            piper_env["PYTHONUTF8"] = "1"
            subprocess.run(
                command,
                input=text.encode("utf-8"),
                check=True,
                capture_output=True,
                env=piper_env,
            )
            sample_rate, data = read(str(output_file))
            sd.play(data, sample_rate)
            sd.wait()
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Piper could not synthesize speech: {detail}") from exc
        finally:
            if output_file.exists():
                output_file.unlink()