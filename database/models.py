from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import declarative_base, sessionmaker
from core.config import get_settings
from core.logger import get_logger

log = get_logger(__name__)
settings = get_settings()

# 1. Create Engine and Session
engine = create_engine(settings.database.url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Define Models based on your PDF Chapter 9
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String) # 'user', 'assistant', 'system', 'tool'
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String, nullable=False)
    payload = Column(Text)
    status = Column(String)
    timestamp = Column(TIMESTAMP, server_default=func.now())

# 3. Create tables
def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        log.info("PostgreSQL database initialized successfully.")
    except Exception as e:
        log.error(f"Failed to connect to PostgreSQL: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()