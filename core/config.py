# core/config.py
from pathlib import Path
from typing import Literal
import ast
import json
from pydantic import BaseModel, Field


def _load_yaml(text: str) -> dict:
    """Load the nested mapping/scalar subset used by the settings file."""
    result: dict = {}
    stack: list[tuple[int, dict]] = [(-1, result)]

    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        key, separator, raw_value = stripped.partition(":")
        if not separator:
            raise ValueError(f"Invalid settings YAML at line {line_number}")
        while indent <= stack[-1][0]:
            stack.pop()

        value = raw_value.strip()
        if not value:
            child: dict = {}
            stack[-1][1][key] = child
            stack.append((indent, child))
            continue

        if " #" in value and not value.startswith(("'", '"')):
            value = value.split(" #", 1)[0].rstrip()
        lowered = value.lower()
        if lowered in ("true", "false", "null", "~"):
            parsed = {"true": True, "false": False, "null": None, "~": None}[lowered]
        else:
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    parsed = value.strip("'") if value.startswith("'") and value.endswith("'") else value
        stack[-1][1][key] = parsed

    return result

class AppConfig(BaseModel):
    name: str = "JARVIS AI"
    version: str = "0.1.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

class DatabaseConfig(BaseModel):
    # path: str = "jarvis.db"
     url: str = "postgresql+psycopg2://postgres:admin@localhost:5432/jarvis_db"

class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b-instruct-q4_K_M"

class VoiceConfig(BaseModel):
    stt_model: str = "small"
    stt_device: str = "cpu"
    stt_compute_type: str = "int8"

class PathsConfig(BaseModel):
    logs_dir: str = "logs"
    vector_db_dir: str = "chroma_data"

class Settings(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)

    @classmethod
    def load(cls, path: str | Path = "config/settings.yaml") -> "Settings":
        path = Path(path)
        if not path.exists():
            return cls()  # fall back to defaults
        with open(path, "r", encoding="utf-8") as f:
            data = _load_yaml(f.read())
        return cls(**data)

_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.load()
    return _settings