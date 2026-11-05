from core.config import get_settings
from core.logger import get_logger
from database.models import init_db, get_connection

log = get_logger("smoke")
s = get_settings()
log.info(f"App: {s.app.name} v{s.app.version}")

init_db()
conn = get_connection()
tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
log.info(f"Tables: {[t['name'] for t in tables]}")
conn.close()
log.info("Smoke test OK ✅")