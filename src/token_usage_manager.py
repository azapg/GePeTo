from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Optional
from datetime import datetime, timedelta, timezone


@dataclass
class UsageEntry:
    user_id: int
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    timestamp: str


@dataclass
class UserLimit:
    user_id: int
    model: str
    monthly_limit: int
    used_tokens: int


class TokenUsageManager:
    def __init__(self, db_path: str = "data/token_usage.db"):
        self.db_path = Path(db_path)
        self._initialize_db()

    def _initialize_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS usage
                           (
                               id                INTEGER PRIMARY KEY AUTOINCREMENT,
                               user_id           INTEGER,
                               model             TEXT,
                               prompt_tokens     INTEGER,
                               completion_tokens INTEGER,
                               total_tokens      INTEGER,
                               timestamp         TEXT
                           )
                           ''')

            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS limits
                           (
                               user_id       INTEGER,
                               model         TEXT,
                               monthly_limit INTEGER,
                               used_tokens   INTEGER,
                               PRIMARY KEY (user_id, model)
                           )
                           ''')

            conn.commit()

    def log_usage(self, user_id: int, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int,
                  timestamp: Optional[str] = None):
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO usage (user_id, model, prompt_tokens, completion_tokens, total_tokens, timestamp)
                           VALUES (?, ?, ?, ?, ?, ?)
                           ''', (user_id, model, prompt_tokens, completion_tokens, total_tokens, timestamp))
            conn.commit()

    def get_usage(self, user_id: int, model: str, days: int = 30) -> list[UsageEntry]:
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = '''
                    SELECT user_id, model, prompt_tokens, completion_tokens, total_tokens, timestamp
                    FROM usage
                    WHERE user_id = ?
                      AND model = ?
                      AND timestamp >= ? \
                    '''
            cursor.execute(query, (user_id, model, cutoff_date))
            rows = cursor.fetchall()

        return [UsageEntry(*row) for row in rows]

    def get_user_monthly_usage(self, user_id: int, model: str) -> int:
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT SUM(total_tokens)
                           FROM usage
                           WHERE user_id = ?
                             AND model = ?
                             AND timestamp >= ?
                           ''', (user_id, model, cutoff_date))
            result = cursor.fetchone()

        return result[0] if result[0] is not None else 0

    def set_user_limit(self, user_id: int, model: str, monthly_limit: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO limits (user_id, model, monthly_limit, used_tokens)
                           VALUES (?, ?, ?, 0)
                           ON CONFLICT(user_id, model) DO UPDATE SET monthly_limit = excluded.monthly_limit
                           ''', (user_id, model, monthly_limit))
            conn.commit()

    def get_user_limit(self, user_id: int, model: str) -> Optional[UserLimit]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT user_id, model, monthly_limit, used_tokens
                           FROM limits
                           WHERE user_id = ?
                             AND model = ?
                           ''', (user_id, model))
            row = cursor.fetchone()

        if row:
            return UserLimit(*row)
        return None


manager = TokenUsageManager()
