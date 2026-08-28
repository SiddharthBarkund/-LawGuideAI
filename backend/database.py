import sqlite3
import json
import os
import uuid
from datetime import datetime

# Setup DB path relative to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "law_mitra.db")

def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    # Use check_same_thread=False since FastAPI handles async event loops across threads
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Documents Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                session_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                text TEXT NOT NULL,
                upload_time TEXT NOT NULL,
                fraud_warnings TEXT NOT NULL  -- JSON encoded array of warnings
            )
        """)
        
        # 2. Conversations Metadata Table (stores session info for UI sidebar history)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_name TEXT,
                user_language TEXT,
                preview TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        # 3. Chat Messages Table (stores actual conversation logs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,          -- 'user' or 'assistant' / 'system' (for summary)
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
    finally:
        conn.close()

# Initialize DB on import
init_db()

# ----------------------------------------------------------------------------------
# Document Store Helpers
# ----------------------------------------------------------------------------------
def save_document(session_id, filename, text, fraud_warnings):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        warnings_json = json.dumps(fraud_warnings)
        upload_time = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO documents (session_id, filename, text, upload_time, fraud_warnings)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                filename=excluded.filename,
                text=excluded.text,
                upload_time=excluded.upload_time,
                fraud_warnings=excluded.fraud_warnings
        """, (session_id, filename, text, upload_time, warnings_json))
        conn.commit()
    finally:
        conn.close()

def get_document(session_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            return {
                "session_id": row["session_id"],
                "filename": row["filename"],
                "text": row["text"],
                "upload_time": row["upload_time"],
                "fraud_warnings": json.loads(row["fraud_warnings"])
            }
        return None
    finally:
        conn.close()

def delete_document(session_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()

# ----------------------------------------------------------------------------------
# Chat History Helpers
# ----------------------------------------------------------------------------------
def save_conversation(session_id, user_name=None, user_language="english", preview=""):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO conversations (id, user_name, user_language, preview, timestamp)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                user_name=COALESCE(excluded.user_name, conversations.user_name),
                user_language=excluded.user_language,
                preview=excluded.preview,
                timestamp=excluded.timestamp
        """, (session_id, user_name, user_language, preview, timestamp))
        conn.commit()
    finally:
        conn.close()

def get_conversations_list():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversations ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            # Query first user query to construct preview if empty
            preview = r["preview"]
            if not preview:
                cursor.execute(
                    "SELECT content FROM chat_messages WHERE session_id = ? AND role = 'user' ORDER BY timestamp ASC LIMIT 1",
                    (r["id"],)
                )
                first_msg = cursor.fetchone()
                if first_msg:
                    msg_content = first_msg["content"]
                    preview = msg_content[:60] + "..." if len(msg_content) > 60 else msg_content
            
            result.append({
                "id": r["id"],
                "question": preview or "New Consultation",
                "timestamp": r["timestamp"],
                "preview": preview or "New Consultation",
                "language": r["user_language"],
                "user_name": r["user_name"]
            })
        return result
    finally:
        conn.close()

def delete_conversation(session_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM conversations WHERE id = ?", (session_id,))
        cursor.execute("DELETE FROM documents WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()

def save_chat_message(session_id, role, content, msg_id=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if not msg_id:
            msg_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Ensure conversation exists
        cursor.execute("SELECT id FROM conversations WHERE id = ?", (session_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO conversations (id, user_name, user_language, preview, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, None, "english", content[:60], timestamp))
            
        cursor.execute("""
            INSERT INTO chat_messages (id, session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (msg_id, session_id, role, content, timestamp))
        
        # Update preview in conversation
        if role == 'user':
            preview = content[:60] + "..." if len(content) > 60 else content
            cursor.execute(
                "UPDATE conversations SET preview = ?, timestamp = ? WHERE id = ?",
                (preview, timestamp, session_id)
            )
            
        conn.commit()
        return msg_id
    finally:
        conn.close()

def get_chat_history(session_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]
    finally:
        conn.close()

def clear_chat_history(session_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()
