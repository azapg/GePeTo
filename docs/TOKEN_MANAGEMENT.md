# Token Usage Telemetry and Management

GePeTo now includes comprehensive token usage tracking and management to monitor and control AI model usage costs.

## Features

### 🪙 Token Tracking
- **Per-call tracking**: Each DSPy LLM call is tracked separately with completion, prompt, and total tokens
- **Session-based tracking**: Multiple calls in a single interaction are grouped by session ID
- **User and guild tracking**: Token usage is tracked per Discord user and server
- **Historical data**: SQLite database stores all usage with timestamps for analysis

### 🚫 Token Limits
- **User limits**: Set maximum tokens per user over a configurable time window
- **Guild limits**: Set maximum tokens per Discord server
- **Automatic enforcement**: Requests are blocked when limits are exceeded
- **Bypass system**: Privileged users/guilds can have unlimited access

### 📊 Usage Monitoring
- **Discord commands**: Check usage with `/token-usage` and `/token-stats`
- **Real-time feedback**: Users see their current usage and remaining limits
- **Admin statistics**: Comprehensive usage analytics for administrators

## Configuration

### Token Limits (`models.json`)

Add token limit configuration to your `models.json`:

```json
{
  "default": "kimi-fast",
  "user_limit": 100000,
  "guild_limit": 500000,
  "time_window_days": 30,
  "models": [
    // ... your models
  ]
}
```

- `user_limit`: Maximum tokens per user in the time window (null = no limit)
- `guild_limit`: Maximum tokens per guild in the time window (null = no limit)  
- `time_window_days`: Time window for limits in days (default: 30)

### Token Bypasses (`token_bypasses.json`)

Create a `token_bypasses.json` file for unlimited access:

```json
{
  "users": [123456789012345678],
  "guilds": [987654321098765432]
}
```

## Discord Commands

### `/token-usage`
Check your personal and server token usage:
- Shows current usage vs limits
- Displays remaining tokens
- Shows usage breakdown by token type

### `/token-stats` (Admin only)
View comprehensive usage statistics:
- Overall usage across all users/guilds
- Top users and servers by usage
- Model usage breakdown
- Time-based analytics

## Implementation Details

### Token Extraction
The system safely extracts token usage from DSPy's `lm.history`:

```python
# Example of extracted data from a Groq Kimi call
usage = [
    {'completion_tokens': 117, 'prompt_tokens': 3721, 'total_tokens': 3838},
    {'completion_tokens': 63, 'prompt_tokens': 3856, 'total_tokens': 3919},
    {'completion_tokens': 39, 'prompt_tokens': 2725, 'total_tokens': 2764}
]
```

### Database Schema
Token usage is stored in SQLite with the following structure:
- `user_id`, `guild_id`, `channel_id`: Discord identifiers
- `session_id`, `call_index`: Track multiple calls per interaction
- `completion_tokens`, `prompt_tokens`, `total_tokens`: Token counts
- `model`, `timestamp`: Model used and when the call occurred

### Limit Enforcement
Before each request, the system:
1. Checks if user/guild has bypass permissions
2. Calculates current usage in the time window
3. Compares against configured limits
4. Blocks request if limits exceeded
5. Shows informative error message to user

## Benefits

- **Cost Control**: Prevents unlimited token usage and associated API costs
- **Usage Insights**: Detailed analytics on how tokens are being used
- **Fair Access**: Ensures equitable access across users and servers  
- **Privileged Access**: Allows unlimited access for trusted users/guilds
- **Transparency**: Users can see their usage and understand limits

## Backward Compatibility

The token tracking system is fully backward compatible:
- Existing data collection continues to work
- No changes required to existing configuration
- Token limits are optional (no limits by default)
- All existing functionality remains unchanged

## Example Usage

```python
from token_manager import get_token_manager

# Get token manager
token_manager = get_token_manager()

# Check if user can make request
can_process, info = token_manager.can_process_request(user_id, guild_id)

if not can_process:
    # Send limit exceeded message
    await message.channel.send("Token limit exceeded!")
    return

# After DSPy call, extract and record usage
usage_data = extract_token_usage_from_history(
    lm.history, user_id, guild_id, channel_id, session_id
)
token_manager.record_token_usage(usage_data)
```

This token management system provides comprehensive control over AI model usage while maintaining full transparency and user-friendly access to usage information.