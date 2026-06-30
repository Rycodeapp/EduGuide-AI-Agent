import sqlite3
import datetime
import logging

logger = logging.getLogger(__name__)

def init_db():
    conn = sqlite3.connect('feedback.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_prompt TEXT,
            bot_response TEXT,
            rating TEXT
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized.")

def save_feedback(user_prompt, bot_response, rating):
    try:
        conn = sqlite3.connect('feedback.db')
        c = conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        c.execute('''
            INSERT INTO feedback (timestamp, user_prompt, bot_response, rating)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, user_prompt, bot_response, rating))
        conn.commit()
        conn.close()
        logger.info("Feedback saved.")
    except Exception as e:
        logger.error(f"Lỗi lưu feedback: {e}")

def get_feedback_data():
    """Trả về list các dòng feedback dưới dạng dict"""
    try:
        conn = sqlite3.connect('feedback.db')
        c = conn.cursor()
        c.execute('SELECT timestamp, user_prompt, bot_response, rating FROM feedback ORDER BY timestamp DESC')
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Lỗi lấy feedback: {e}")
        return []