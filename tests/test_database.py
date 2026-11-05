import pytest
from sqlalchemy import inspect, text
from database.models import init_db, engine, SessionLocal, User, Conversation, Message

# Run this once before any tests to make sure tables exist
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    init_db()

def test_tables_created():
    """Verify that SQLAlchemy created all 4 tables in Postgres."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    expected_tables = {"users", "conversations", "messages", "audit_logs"}
    assert expected_tables <= set(tables)

def test_insert_and_query_data():
    """Verify we can insert data and read it back using SQLAlchemy."""
    db = SessionLocal()
    try:
        # Clean up any leftover test data from previous runs
        db.execute(text("TRUNCATE users, conversations, messages RESTART IDENTITY CASCADE;"))
        db.commit()

        # 1. Insert a user
        new_user = User(username="test_alice")
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # 2. Insert a conversation linked to the user
        new_conv = Conversation(user_id=new_user.id, title="Test Chat")
        db.add(new_conv)
        db.commit()
        db.refresh(new_conv)

        # 3. Verify the data was saved
        assert new_user.id is not None
        assert new_conv.id is not None
        
        # 4. Query it back
        fetched_conv = db.query(Conversation).filter_by(id=new_conv.id).first()
        assert fetched_conv.title == "Test Chat"
        assert fetched_conv.user_id == new_user.id

    finally:
        db.close()