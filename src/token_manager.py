"""
Simplified token tracking and management system for GePeTo
Provides SQLite-based storage for per-user per-model token usage with configurable limits
"""

import sqlite3
import os
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from contextlib import contextmanager

@dataclass
class TokenUsage:
    """Represents token usage for a single call"""
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int
    timestamp: str
    model: str
    user_id: int
    guild_id: Optional[int]
    channel_id: int
    session_id: str
    call_index: int  # Index of this call within the session

class TokenManager:
    """Simplified token manager - per-user per-model limits only"""
    
    def __init__(self, db_path: str = "data/token_usage.db"):
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        
        # Default limits per model (can be customized per user)
        self.default_limits = {
            "time_window_days": 30,
            "default_limit": 100000,  # 100k tokens per user per model per month
        }
        
        # User-specific limits stored in memory (could be moved to DB later)
        self.user_limits = {}  # {user_id: {model: limit_or_-1_for_unlimited}}
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Token usage table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER,
                    channel_id INTEGER NOT NULL,
                    session_id TEXT NOT NULL,
                    call_index INTEGER NOT NULL,
                    model TEXT NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User limits table for persistent storage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_limits (
                    user_id INTEGER NOT NULL,
                    model TEXT NOT NULL,
                    token_limit INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, model)
                )
            """)
            
            # Create indexes for efficient querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_model_timestamp 
                ON token_usage(user_id, model, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session 
                ON token_usage(session_id, call_index)
            """)
            
            conn.commit()
            
        # Load user limits from database
        self._load_user_limits()
    
    @contextmanager
    def _get_db_connection(self):
        """Get a database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        finally:
            if conn:
                conn.close()
    
    def _load_user_limits(self):
        """Load user limits from database into memory"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, model, token_limit FROM user_limits")
            
            self.user_limits = {}
            for row in cursor.fetchall():
                user_id = row["user_id"]
                model = row["model"]
                limit = row["token_limit"]
                
                if user_id not in self.user_limits:
                    self.user_limits[user_id] = {}
                self.user_limits[user_id][model] = limit
    
    def set_user_limit(self, user_id: int, model: str, limit: int):
        """Set token limit for a user for a specific model (-1 for unlimited)"""
        with self._lock:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO user_limits (user_id, model, token_limit, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, model, limit))
                conn.commit()
            
            # Update in-memory cache
            if user_id not in self.user_limits:
                self.user_limits[user_id] = {}
            self.user_limits[user_id][model] = limit
    
    def get_user_limit(self, user_id: int, model: str) -> int:
        """Get token limit for a user for a specific model"""
        if user_id in self.user_limits and model in self.user_limits[user_id]:
            return self.user_limits[user_id][model]
        return self.default_limits["default_limit"]
    
    def set_user_limit_all_models(self, user_id: int, limit: int):
        """Set the same limit for a user across all models"""
        # Get all unique models from usage history
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT model FROM token_usage")
            models = [row["model"] for row in cursor.fetchall()]
        
        # Also include any models the user already has limits for
        if user_id in self.user_limits:
            models.extend(self.user_limits[user_id].keys())
        
        # Remove duplicates and set limit for each model
        models = list(set(models))
        for model in models:
            self.set_user_limit(user_id, model, limit)
    
    def reset_user_usage(self, user_id: int):
        """Reset (delete) all usage for a user"""
        with self._lock:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM token_usage WHERE user_id = ?", (user_id,))
                conn.commit()
    
    def record_token_usage(self, usage_data: List[TokenUsage]) -> bool:
        """Record token usage for a session"""
        with self._lock:
            try:
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    for usage in usage_data:
                        cursor.execute("""
                            INSERT INTO token_usage 
                            (user_id, guild_id, channel_id, session_id, call_index,
                             model, completion_tokens, prompt_tokens, total_tokens, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            usage.user_id,
                            usage.guild_id,
                            usage.channel_id,
                            usage.session_id,
                            usage.call_index,
                            usage.model,
                            usage.completion_tokens,
                            usage.prompt_tokens,
                            usage.total_tokens,
                            usage.timestamp
                        ))
                    
                    conn.commit()
                    return True
                    
            except sqlite3.Error as e:
                print(f"Error recording token usage: {e}")
                return False
    
    def get_user_usage(self, user_id: int, model: str, days: Optional[int] = None) -> Dict[str, int]:
        """Get token usage for a user for a specific model within specified timeframe"""
        if days is None:
            days = self.default_limits["time_window_days"]
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    SUM(completion_tokens) as total_completion,
                    SUM(prompt_tokens) as total_prompt,
                    SUM(total_tokens) as total_tokens,
                    COUNT(*) as call_count
                FROM token_usage 
                WHERE user_id = ? AND model = ? AND timestamp >= ?
            """, (user_id, model, cutoff_date))
            
            result = cursor.fetchone()
            
            return {
                "completion_tokens": result["total_completion"] or 0,
                "prompt_tokens": result["total_prompt"] or 0,
                "total_tokens": result["total_tokens"] or 0,
                "call_count": result["call_count"] or 0,
                "timeframe_days": days
            }
    
    def can_process_request(self, user_id: int, guild_id: Optional[int], model: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if a request can be processed based on user token limits for the specific model"""
        user_limit = self.get_user_limit(user_id, model)
        
        # Unlimited access
        if user_limit == -1:
            return True, {
                "user": {
                    "unlimited": True,
                    "limit": -1,
                    "model": model
                }
            }
        
        # Get usage for this user and model
        usage = self.get_user_usage(user_id, model)
        
        within_limit = usage["total_tokens"] < user_limit
        remaining = max(0, user_limit - usage["total_tokens"])
        
        return within_limit, {
            "user": {
                "unlimited": False,
                "limit": user_limit,
                "usage": usage,
                "remaining": remaining,
                "model": model,
                "timeframe_days": self.default_limits["time_window_days"]
            }
        }
    
    def get_session_usage(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all token usage for a specific session"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM token_usage 
                WHERE session_id = ? 
                ORDER BY call_index
            """, (session_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_usage_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get overall usage statistics"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Overall stats
            cursor.execute("""
                SELECT 
                    SUM(completion_tokens) as total_completion,
                    SUM(prompt_tokens) as total_prompt,
                    SUM(total_tokens) as total_tokens,
                    COUNT(*) as total_calls,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT guild_id) as unique_guilds,
                    COUNT(DISTINCT session_id) as unique_sessions
                FROM token_usage 
                WHERE timestamp >= ?
            """, (cutoff_date,))
            
            overall = dict(cursor.fetchone())
            
            # Top users
            cursor.execute("""
                SELECT 
                    user_id,
                    SUM(total_tokens) as total_tokens,
                    COUNT(*) as call_count
                FROM token_usage 
                WHERE timestamp >= ?
                GROUP BY user_id
                ORDER BY total_tokens DESC
                LIMIT 10
            """, (cutoff_date,))
            
            top_users = [dict(row) for row in cursor.fetchall()]
            
            # Top guilds
            cursor.execute("""
                SELECT 
                    guild_id,
                    SUM(total_tokens) as total_tokens,
                    COUNT(*) as call_count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM token_usage 
                WHERE timestamp >= ? AND guild_id IS NOT NULL
                GROUP BY guild_id
                ORDER BY total_tokens DESC
                LIMIT 10
            """, (cutoff_date,))
            
            top_guilds = [dict(row) for row in cursor.fetchall()]
            
            # Model usage
            cursor.execute("""
                SELECT 
                    model,
                    SUM(total_tokens) as total_tokens,
                    COUNT(*) as call_count,
                    AVG(total_tokens) as avg_tokens_per_call
                FROM token_usage 
                WHERE timestamp >= ?
                GROUP BY model
                ORDER BY total_tokens DESC
            """, (cutoff_date,))
            
            model_usage = [dict(row) for row in cursor.fetchall()]
            
            return {
                "timeframe_days": days,
                "overall": overall,
                "top_users": top_users,
                "top_guilds": top_guilds,
                "model_usage": model_usage
            }


# Global instance
_token_manager = None

def get_token_manager() -> TokenManager:
    """Get global token manager instance"""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager


def extract_token_usage_from_history(
    lm_history: List[Dict[str, Any]], 
    user_id: int,
    guild_id: Optional[int],
    channel_id: int,
    session_id: str
) -> List[TokenUsage]:
    """Extract token usage from DSPy lm.history"""
    usage_data = []
    
    for call_index, call in enumerate(lm_history):
        if 'usage' not in call or not call['usage']:
            continue
            
        usage_info = call['usage']
        
        # Extract safe token counts as specified in the issue
        completion_tokens = usage_info.get('completion_tokens', 0)
        prompt_tokens = usage_info.get('prompt_tokens', 0)
        total_tokens = usage_info.get('total_tokens', 0)
        
        # Get timestamp and model
        timestamp = call.get('timestamp', datetime.now().isoformat())
        model = call.get('model', 'unknown')
        
        usage_data.append(TokenUsage(
            completion_tokens=completion_tokens,
            prompt_tokens=prompt_tokens,
            total_tokens=total_tokens,
            timestamp=timestamp,
            model=model,
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            session_id=session_id,
            call_index=call_index
        ))
    
    return usage_data