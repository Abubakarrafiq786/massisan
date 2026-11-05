from core.config import Settings, get_settings

def test_default_settings():
    s = Settings()
    assert s.app.name == "JARVIS AI"
    assert s.ollama.model.startswith("qwen2.5")

def test_load_from_yaml():
    s = Settings.load("config/settings.yaml")
    assert s.database.url.startswith("postgresql")

def test_get_settings_singleton():
    assert get_settings() is get_settings()