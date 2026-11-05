import logging
from core.logger import get_logger

def test_logger_creates_handlers(tmp_path, monkeypatch):
    # force fresh config pointing logs to tmp
    from core import config, logger as logger_mod
    cfg = config.Settings()
    cfg.paths.logs_dir = str(tmp_path)
    monkeypatch.setattr(config, "_settings", cfg)
    monkeypatch.setattr(logger_mod, "_settings", cfg, raising=False)

    lg = get_logger("test_logger_unique")
    lg.info("hello")
    assert (tmp_path / "jarvis.log").exists()