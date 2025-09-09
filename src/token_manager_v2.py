"""
Token tracking and management system for GePeTo v2
Provides SQLite-based storage for user and guild token usage with complex limit hierarchies
"""

import sqlite3
import os
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
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
class ModelLimits:
    """Represents token limits for a specific model"""
    user_limit: Optional[int] = None
    guild_limit: Optional[int] = None
    guild_pool: Optional[int] = None
    member_limit: Optional[int] = None

@dataclass
class LimitsConfig:
    """Represents the complete limits configuration"""
    time_window_days: int = 30
    default_model_limits: Dict[str, ModelLimits] = None
    custom_user_limits: Dict[int, Dict] = None
    custom_guild_limits: Dict[int, Dict] = None

class TokenManagerV2:
    """Advanced token manager with guild pools and per-model limits"""
    
    def __init__(self, db_path: str = "data/token_usage.db", limits_path: str = "limits.json"):
        self.db_path = Path(db_path)
        self.limits_path = Path(limits_path)
        self._lock = threading.Lock()
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Token usage table (existing)
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
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    charge_source TEXT DEFAULT 'user' -- 'guild_pool', 'user_pool', 'unlimited'
                )
            """)
            
            # Guild token pools table (new)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guild_token_pools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    model TEXT NOT NULL,
                    total_pool INTEGER NOT NULL,
                    used_tokens INTEGER DEFAULT 0,
                    reset_date TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, model, reset_date)
                )
            """)
            
            # User token pools table (new)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_token_pools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    model TEXT NOT NULL,
                    used_tokens INTEGER DEFAULT 0,
                    reset_date TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, model, reset_date)
                )
            """)
            
            # Create indexes for efficient querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_model_timestamp 
                ON token_usage(user_id, model, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_guild_model_timestamp 
                ON token_usage(guild_id, model, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session 
                ON token_usage(session_id, call_index)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_guild_pools 
                ON guild_token_pools(guild_id, model, reset_date)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_pools 
                ON user_token_pools(user_id, model, reset_date)
            """)
            
            # Add charge_source column if it doesn't exist (migration)
            try:
                cursor.execute("ALTER TABLE token_usage ADD COLUMN charge_source TEXT DEFAULT 'user'")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
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
    
    def _load_limits_config(self) -> LimitsConfig:
        """Load limits configuration from JSON file"""
        if not self.limits_path.exists():
            # Return default config
            return LimitsConfig(
                default_model_limits={},
                custom_user_limits={},
                custom_guild_limits={}
            )
        
        try:
            with open(self.limits_path, 'r') as f:
                config = json.load(f)
                
            # Parse default limits
            default_limits = {}
            for model, limits in config.get('default_limits', {}).get('models', {}).items():
                default_limits[model] = ModelLimits(
                    user_limit=limits.get('user_limit'),
                    guild_limit=limits.get('guild_limit')
                )
            
            # Parse custom limits
            custom_user_limits = {}
            for user_id_str, user_config in config.get('custom_limits', {}).get('users', {}).items():
                custom_user_limits[int(user_id_str)] = user_config
                
            custom_guild_limits = {}
            for guild_id_str, guild_config in config.get('custom_limits', {}).get('guilds', {}).items():
                custom_guild_limits[int(guild_id_str)] = guild_config
            
            return LimitsConfig(
                time_window_days=config.get('default_limits', {}).get('time_window_days', 30),
                default_model_limits=default_limits,
                custom_user_limits=custom_user_limits,
                custom_guild_limits=custom_guild_limits
            )
        except (json.JSONDecodeError, IOError, ValueError):
            return LimitsConfig(
                default_model_limits={},
                custom_user_limits={},
                custom_guild_limits={}
            )
    
    def _get_reset_date(self, days: int) -> str:
        """Get the reset date for the current period"""
        return (datetime.now() + timedelta(days=days)).date().isoformat()
    
    def _get_cutoff_date(self, days: int) -> str:
        """Get the cutoff date for usage queries"""
        return (datetime.now() - timedelta(days=days)).isoformat()
    
    def _resolve_user_limit(self, user_id: int, model: str, config: LimitsConfig) -> Union[int, None]:
        """Resolve the effective limit for a user and model"""
        # Check custom user limits first
        if user_id in config.custom_user_limits:
            user_config = config.custom_user_limits[user_id]
            
            # Check model-specific limit
            if 'models' in user_config and model in user_config['models']:
                limit = user_config['models'][model]
                return None if limit == -1 else limit
            
            # Check fallback pool
            if 'fallback_pool' in user_config:
                limit = user_config['fallback_pool']
                return None if limit == -1 else limit
        
        # Fall back to default model limits
        if model in config.default_model_limits:
            return config.default_model_limits[model].user_limit
        
        return None
    
    def _resolve_guild_limits(self, guild_id: int, model: str, config: LimitsConfig) -> Dict[str, Any]:
        """Resolve guild limits and pool configuration"""
        result = {
            'has_pool': False,
            'pool_size': None,
            'member_limit': None,
            'role_limits': {},
            'member_bypasses': []
        }
        
        # Check custom guild limits
        if guild_id in config.custom_guild_limits:
            guild_config = config.custom_guild_limits[guild_id]
            
            # Check if guild has a token pool
            if 'token_pool' in guild_config:
                result['has_pool'] = True
                result['pool_size'] = guild_config['token_pool']
                result['member_limit'] = guild_config.get('member_limit')
                result['role_limits'] = guild_config.get('role_limits', {})
                result['member_bypasses'] = guild_config.get('member_bypasses', [])
            
            # Check model-specific pools
            elif 'models' in guild_config and model in guild_config['models']:
                model_config = guild_config['models'][model]
                if 'pool' in model_config:
                    result['has_pool'] = True
                    result['pool_size'] = model_config['pool']
                    result['member_limit'] = model_config.get('member_limit')
        
        return result
    
    def can_process_request(self, user_id: int, guild_id: Optional[int], model: str, estimated_tokens: int = 0, user_roles: List[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """Check if a request can be processed based on the new token hierarchy"""
        config = self._load_limits_config()
        
        # If no guild_id, check user limits only
        if guild_id is None:
            return self._check_user_only_limits(user_id, model, config, estimated_tokens)
        
        # Check guild pool first
        guild_limits = self._resolve_guild_limits(guild_id, model, config)
        
        if guild_limits['has_pool']:
            # Guild has a token pool - check if user can consume from it
            return self._check_guild_pool_limits(user_id, guild_id, model, config, guild_limits, estimated_tokens, user_roles)
        else:
            # No guild pool - fall back to user limits
            return self._check_user_only_limits(user_id, model, config, estimated_tokens)
    
    def _check_user_only_limits(self, user_id: int, model: str, config: LimitsConfig, estimated_tokens: int) -> Tuple[bool, Dict[str, Any]]:
        """Check user-only limits (for DMs or guilds without pools)"""
        user_limit = self._resolve_user_limit(user_id, model, config)
        
        # Unlimited user
        if user_limit is None:
            return True, {
                'user': {'unlimited': True, 'charge_source': 'unlimited'},
                'guild': {'no_pool': True},
                'can_process': True
            }
        
        # Check current usage
        usage = self._get_user_model_usage(user_id, model, config.time_window_days)
        remaining = user_limit - usage['total_tokens']
        
        can_process = remaining > estimated_tokens
        
        return can_process, {
            'user': {
                'limit': user_limit,
                'usage': usage,
                'remaining': remaining,
                'charge_source': 'user_pool'
            },
            'guild': {'no_pool': True},
            'can_process': can_process
        }
    
    def _check_guild_pool_limits(self, user_id: int, guild_id: int, model: str, config: LimitsConfig, guild_limits: Dict, estimated_tokens: int, user_roles: List[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """Check guild pool limits and member limits"""
        # Check if user bypasses guild limits
        if str(user_id) in guild_limits['member_bypasses']:
            return True, {
                'user': {'guild_bypass': True, 'charge_source': 'guild_pool'},
                'guild': {'has_pool': True, 'user_bypass': True},
                'can_process': True
            }
        
        # Get current guild pool usage
        pool_usage = self._get_guild_pool_usage(guild_id, model, config.time_window_days)
        pool_remaining = guild_limits['pool_size'] - pool_usage['total_tokens']
        
        # Check if guild pool has enough tokens
        if pool_remaining <= estimated_tokens:
            # Guild pool exhausted - fall back to user limits
            return self._check_user_fallback_limits(user_id, model, config, estimated_tokens, pool_usage)
        
        # Check member limits within guild pool
        member_limit = guild_limits['member_limit']
        
        # Check for role-based limits (higher priority than default member limit)
        if user_roles and guild_limits['role_limits']:
            for role_id in user_roles:
                if str(role_id) in guild_limits['role_limits']:
                    member_limit = guild_limits['role_limits'][str(role_id)]
                    break  # Use the first matching role limit found
        
        if member_limit:
            member_usage = self._get_user_guild_model_usage(user_id, guild_id, model, config.time_window_days)
            member_remaining = member_limit - member_usage['total_tokens']
            
            if member_remaining <= estimated_tokens:
                # Member limit exceeded - fall back to user limits
                return self._check_user_fallback_limits(user_id, model, config, estimated_tokens, pool_usage, member_usage)
        else:
            member_usage = None
        
        # Can use guild pool
        return True, {
            'user': {'charge_source': 'guild_pool'},
            'guild': {
                'has_pool': True,
                'pool_size': guild_limits['pool_size'],
                'pool_usage': pool_usage,
                'pool_remaining': pool_remaining,
                'member_limit': member_limit,
                'member_usage': member_usage
            },
            'can_process': True
        }
    
    def _check_user_fallback_limits(self, user_id: int, model: str, config: LimitsConfig, estimated_tokens: int, pool_usage: Dict = None, member_usage: Dict = None) -> Tuple[bool, Dict[str, Any]]:
        """Check user fallback limits when guild pool is exhausted"""
        user_limit = self._resolve_user_limit(user_id, model, config)
        
        # Unlimited user
        if user_limit is None:
            return True, {
                'user': {'unlimited': True, 'charge_source': 'user_fallback'},
                'guild': {'pool_exhausted': True, 'pool_usage': pool_usage},
                'can_process': True
            }
        
        # Check user usage
        usage = self._get_user_model_usage(user_id, model, config.time_window_days)
        remaining = user_limit - usage['total_tokens']
        
        can_process = remaining > estimated_tokens
        
        return can_process, {
            'user': {
                'limit': user_limit,
                'usage': usage,
                'remaining': remaining,
                'charge_source': 'user_fallback'
            },
            'guild': {
                'pool_exhausted': True,
                'pool_usage': pool_usage,
                'member_usage': member_usage
            },
            'can_process': can_process
        }
    
    def _get_user_model_usage(self, user_id: int, model: str, days: int) -> Dict[str, int]:
        """Get user usage for a specific model"""
        cutoff_date = self._get_cutoff_date(days)
        
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
    
    def _get_user_guild_model_usage(self, user_id: int, guild_id: int, model: str, days: int) -> Dict[str, int]:
        """Get user usage for a specific model within a specific guild"""
        cutoff_date = self._get_cutoff_date(days)
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    SUM(completion_tokens) as total_completion,
                    SUM(prompt_tokens) as total_prompt,
                    SUM(total_tokens) as total_tokens,
                    COUNT(*) as call_count
                FROM token_usage 
                WHERE user_id = ? AND guild_id = ? AND model = ? AND timestamp >= ?
            """, (user_id, guild_id, model, cutoff_date))
            
            result = cursor.fetchone()
            
            return {
                "completion_tokens": result["total_completion"] or 0,
                "prompt_tokens": result["total_prompt"] or 0,
                "total_tokens": result["total_tokens"] or 0,
                "call_count": result["call_count"] or 0,
                "timeframe_days": days
            }
    
    def _get_guild_pool_usage(self, guild_id: int, model: str, days: int) -> Dict[str, int]:
        """Get total guild pool usage for a specific model"""
        cutoff_date = self._get_cutoff_date(days)
        
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
                WHERE guild_id = ? AND model = ? AND timestamp >= ?
                AND charge_source IN ('guild_pool', 'unlimited')
            """, (guild_id, model, cutoff_date))
            
            result = cursor.fetchone()
            
            return {
                "completion_tokens": result["total_completion"] or 0,
                "prompt_tokens": result["total_prompt"] or 0,
                "total_tokens": result["total_tokens"] or 0,
                "call_count": result["call_count"] or 0,
                "unique_users": result["unique_users"] or 0,
                "timeframe_days": days
            }
    
    def record_token_usage(self, usage_data: List[TokenUsage], charge_source: str = 'user') -> bool:
        """Record token usage with charge source tracking"""
        with self._lock:
            try:
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    for usage in usage_data:
                        cursor.execute("""
                            INSERT INTO token_usage 
                            (user_id, guild_id, channel_id, session_id, call_index,
                             model, completion_tokens, prompt_tokens, total_tokens, timestamp, charge_source)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            usage.timestamp,
                            charge_source
                        ))
                    
                    conn.commit()
                    return True
                    
            except sqlite3.Error as e:
                print(f"Error recording token usage: {e}")
                return False

    def get_usage_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get overall usage statistics"""
        cutoff_date = self._get_cutoff_date(days)
        
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
            
            # Charge source breakdown
            cursor.execute("""
                SELECT 
                    charge_source,
                    SUM(total_tokens) as total_tokens,
                    COUNT(*) as call_count
                FROM token_usage 
                WHERE timestamp >= ?
                GROUP BY charge_source
                ORDER BY total_tokens DESC
            """, (cutoff_date,))
            
            charge_sources = [dict(row) for row in cursor.fetchall()]
            
            return {
                "timeframe_days": days,
                "overall": overall,
                "top_users": top_users,
                "top_guilds": top_guilds,
                "model_usage": model_usage,
                "charge_sources": charge_sources
            }

    # Legacy compatibility methods
    def check_user_limit(self, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """Legacy compatibility method"""
        # For backwards compatibility, just check if user can process a request
        # Use a default model if available
        config = self._load_limits_config()
        default_model = list(config.default_model_limits.keys())[0] if config.default_model_limits else 'default'
        
        can_process, info = self.can_process_request(user_id, None, default_model)
        return can_process, info.get('user', {})
    
    def check_guild_limit(self, guild_id: Optional[int]) -> Tuple[bool, Dict[str, Any]]:
        """Legacy compatibility method"""
        if guild_id is None:
            return True, {"dm": True, "reason": "DM channels have no guild limits"}
        
        # For backwards compatibility, just check if guild can process a request
        config = self._load_limits_config()
        default_model = list(config.default_model_limits.keys())[0] if config.default_model_limits else 'default'
        
        can_process, info = self.can_process_request(0, guild_id, default_model)  # Use dummy user_id
        return can_process, info.get('guild', {})


# Global instance
_token_manager_v2 = None

def get_token_manager() -> TokenManagerV2:
    """Get global token manager instance"""
    global _token_manager_v2
    if _token_manager_v2 is None:
        _token_manager_v2 = TokenManagerV2()
    return _token_manager_v2


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