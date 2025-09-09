"""
Token tracking and management system for GePeTo
Provides SQLite-based storage for user and guild token usage with configurable limits
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

@dataclass 
class TokenLimits:
    """Represents token limits configuration"""
    user_limit: Optional[int] = None
    guild_limit: Optional[int] = None
    time_window_days: int = 30  # Default to monthly limits

class TokenManager:
    """Manages token usage tracking and limits enforcement"""
    
    def __init__(self, db_path: str = "data/token_usage.db", bypasses_path: str = "token_bypasses.json"):
        self.db_path = Path(db_path)
        self.bypasses_path = Path(bypasses_path)
        self._lock = threading.Lock()
        
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
            
            # Create indexes for efficient querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_timestamp 
                ON token_usage(user_id, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_guild_timestamp 
                ON token_usage(guild_id, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session 
                ON token_usage(session_id, call_index)
            """)
            
            conn.commit()
    
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
    
    def _load_bypasses(self) -> Dict[str, Any]:
        """Load token limit bypasses from JSON file"""
        if not self.bypasses_path.exists():
            return {"users": [], "guilds": []}
        
        try:
            with open(self.bypasses_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"users": [], "guilds": []}
    
    def _load_token_limits(self) -> TokenLimits:
        """Load token limits from models.json"""
        models_path = Path(__file__).parent.parent / "models.json"
        
        if not models_path.exists():
            return TokenLimits()  # No limits if file doesn't exist
        
        try:
            with open(models_path, 'r') as f:
                config = json.load(f)
                
            # Look for limits in the config
            user_limit = config.get('user_limit')
            guild_limit = config.get('guild_limit')
            time_window_days = config.get('time_window_days', 30)
            
            return TokenLimits(
                user_limit=user_limit,
                guild_limit=guild_limit,
                time_window_days=time_window_days
            )
        except (json.JSONDecodeError, IOError):
            return TokenLimits()
    
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
    
    def get_user_usage(self, user_id: int, days: Optional[int] = None) -> Dict[str, int]:
        """Get token usage for a user within specified timeframe"""
        limits = self._load_token_limits()
        if days is None:
            days = limits.time_window_days
        
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
                WHERE user_id = ? AND timestamp >= ?
            """, (user_id, cutoff_date))
            
            result = cursor.fetchone()
            
            return {
                "completion_tokens": result["total_completion"] or 0,
                "prompt_tokens": result["total_prompt"] or 0,
                "total_tokens": result["total_tokens"] or 0,
                "call_count": result["call_count"] or 0,
                "timeframe_days": days
            }
    
    def get_guild_usage(self, guild_id: int, days: Optional[int] = None) -> Dict[str, int]:
        """Get token usage for a guild within specified timeframe"""
        limits = self._load_token_limits()
        if days is None:
            days = limits.time_window_days
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    SUM(completion_tokens) as total_completion,
                    SUM(prompt_tokens) as total_prompt,
                    SUM(total_tokens) as total_tokens,
                    COUNT(*) as call_count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM token_usage 
                WHERE guild_id = ? AND timestamp >= ?
            """, (guild_id, cutoff_date))
            
            result = cursor.fetchone()
            
            return {
                "completion_tokens": result["total_completion"] or 0,
                "prompt_tokens": result["total_prompt"] or 0,
                "total_tokens": result["total_tokens"] or 0,
                "call_count": result["call_count"] or 0,
                "unique_users": result["unique_users"] or 0,
                "timeframe_days": days
            }
    
    def check_user_limit(self, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """Check if user has exceeded token limits"""
        limits = self._load_token_limits()
        bypasses = self._load_bypasses()
        
        # Check if user has bypass
        if user_id in bypasses.get("users", []):
            return True, {"bypass": True, "reason": "User has unlimited access"}
        
        # No limits configured
        if limits.user_limit is None:
            return True, {"no_limits": True}
        
        usage = self.get_user_usage(user_id, limits.time_window_days)
        
        within_limit = usage["total_tokens"] < limits.user_limit
        
        return within_limit, {
            "limit": limits.user_limit,
            "usage": usage,
            "remaining": max(0, limits.user_limit - usage["total_tokens"]),
            "timeframe_days": limits.time_window_days
        }
    
    def check_guild_limit(self, guild_id: Optional[int]) -> Tuple[bool, Dict[str, Any]]:
        """Check if guild has exceeded token limits"""
        if guild_id is None:
            return True, {"dm": True, "reason": "DM channels have no guild limits"}
        
        limits = self._load_token_limits()
        bypasses = self._load_bypasses()
        
        # Check if guild has bypass
        if guild_id in bypasses.get("guilds", []):
            return True, {"bypass": True, "reason": "Guild has unlimited access"}
        
        # No limits configured
        if limits.guild_limit is None:
            return True, {"no_limits": True}
        
        usage = self.get_guild_usage(guild_id, limits.time_window_days)
        
        within_limit = usage["total_tokens"] < limits.guild_limit
        
        return within_limit, {
            "limit": limits.guild_limit,
            "usage": usage,
            "remaining": max(0, limits.guild_limit - usage["total_tokens"]),
            "timeframe_days": limits.time_window_days
        }
    
    def can_process_request(self, user_id: int, guild_id: Optional[int]) -> Tuple[bool, Dict[str, Any]]:
        """Check if a request can be processed based on token limits"""
        user_ok, user_info = self.check_user_limit(user_id)
        guild_ok, guild_info = self.check_guild_limit(guild_id)
        
        can_process = user_ok and guild_ok
        
        return can_process, {
            "user": user_info,
            "guild": guild_info,
            "can_process": can_process
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