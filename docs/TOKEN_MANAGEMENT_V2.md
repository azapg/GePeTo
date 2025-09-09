# Advanced Token Management System

This document describes the comprehensive token management system that provides cost control and usage analytics for GePeTo.

## Overview

The token management system implements a hierarchical approach to token limits:

1. **Guild Token Pools** - Servers get token pools that members consume from first
2. **User Fallback Pools** - Personal limits when guild pools are exhausted or unavailable  
3. **Per-Model Limits** - Different limits for different AI models based on their costs
4. **Role-Based Limits** - Different limits within guilds based on Discord roles
5. **Unlimited Access** - Special users/guilds can have unlimited tokens

## Configuration

### limits.json Structure

Create a `limits.json` file based on `limits.sample.json`:

```json
{
  "default_limits": {
    "time_window_days": 30,
    "models": {
      "model-name": {
        "user_limit": 100000,
        "guild_limit": 500000
      }
    }
  },
  "custom_limits": {
    "users": {
      "user_id": {
        "models": {
          "model-name": -1,  // -1 = unlimited
          "other-model": 200000
        },
        "fallback_pool": -1
      }
    },
    "guilds": {
      "guild_id": {
        "token_pool": 10000000,
        "member_limit": 100000,
        "role_limits": {
          "role_id": 500000,
          "vip_role_id": 1000000
        },
        "member_bypasses": ["user_id"],
        "models": {
          "model-name": {
            "pool": 5000000,
            "member_limit": 50000
          }
        }
      }
    }
  }
}
```

## How Token Consumption Works

### 1. Guild Context (User in a Server)

When a user interacts in a server:

1. **Check Guild Pool**: If the guild has a token pool, try to consume from it
2. **Check Member Limits**: Verify the user hasn't exceeded their guild member limit
3. **Check Role Limits**: If user has special roles, use role-specific limits
4. **Fallback to User**: If guild pool exhausted, fall back to user's personal limits

### 2. DM Context (Direct Messages)

When a user interacts in DMs:

1. **Use User Limits**: Directly consume from user's personal token pool
2. **Check Model Limits**: Apply per-model limits based on current AI model
3. **Unlimited Check**: Verify if user has unlimited access

### 3. Charge Source Tracking

The system tracks where tokens are charged:

- `guild_pool` - Consumed from guild's token pool
- `user_pool` - Consumed from user's personal limits (DM or no guild pool)
- `user_fallback` - Consumed from user's limits after guild pool exhausted
- `unlimited` - User/guild has unlimited access (still tracked for analytics)

## Per-Model Limits

Different AI models have different costs, so limits are model-specific:

```json
{
  "default_limits": {
    "models": {
      "local-model": {
        "user_limit": 1000000,  // Cheap/free local model
        "guild_limit": 5000000
      },
      "gpt-4": {
        "user_limit": 50000,    // Expensive model
        "guild_limit": 250000
      }
    }
  }
}
```

## Role-Based Limits

Guilds can set different limits based on Discord roles:

```json
{
  "guilds": {
    "guild_id": {
      "member_limit": 100000,      // Default for all members
      "role_limits": {
        "premium_role_id": 500000,  // Premium members get more
        "vip_role_id": 1000000      // VIP members get even more
      }
    }
  }
}
```

The system uses the **first matching role** found, so order roles by priority in your Discord server.

## Guild Token Pool Management

### Setting Up Guild Pools

1. Add guild to `limits.json`:
```json
{
  "guilds": {
    "YOUR_GUILD_ID": {
      "token_pool": 10000000,     // 10M tokens for the guild
      "member_limit": 100000,     // Each member can use up to 100k
      "member_bypasses": ["admin_user_id"]  // Special users with no limits
    }
  }
}
```

2. Members automatically consume from the guild pool when using the bot in that server

3. When guild pool is exhausted, members fall back to their personal limits

### Member Management

- **member_limit**: Maximum tokens each member can use from guild pool
- **role_limits**: Different limits for different Discord roles
- **member_bypasses**: Users who ignore member limits (still consume from pool)

## Database Schema

### Token Usage Table

Tracks all token consumption with charge source:

```sql
CREATE TABLE token_usage (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    guild_id INTEGER,
    model TEXT NOT NULL,
    total_tokens INTEGER NOT NULL,
    charge_source TEXT,  -- 'guild_pool', 'user_pool', etc.
    timestamp TEXT NOT NULL
);
```

### Analytics Queries

The system provides detailed analytics:

- **Per-model usage**: Track which models are most expensive
- **Charge source breakdown**: See how much comes from guild vs user pools
- **Top users/guilds**: Identify highest usage
- **Cost projections**: Estimate monthly costs based on usage patterns

## Discord Commands

### `/token-usage`

Shows current usage for the active model:

- Personal usage and limits
- Guild pool status (if applicable)
- Charge source information
- Remaining tokens

### `/token-stats` (Admin Only)

Shows comprehensive analytics:

- Overall usage statistics
- Top users and guilds
- Per-model breakdown
- Charge source analysis

## Migration from Old System

The new system is backward compatible:

1. Old token_manager.py methods still work
2. Database automatically migrates to add new columns
3. Existing usage data is preserved
4. New features activate when limits.json is created

## Best Practices

### For Guild Administrators

1. **Start Conservative**: Begin with smaller token pools and adjust based on usage
2. **Monitor Analytics**: Use `/token-stats` to track usage patterns
3. **Role-Based Limits**: Give higher limits to trusted/premium members
4. **Model Selection**: Use cheaper models for general chat, expensive ones for specific tasks

### For Bot Administrators

1. **Per-Model Pricing**: Set limits based on actual API costs
2. **Analytics Review**: Regularly review usage to identify cost trends
3. **Limit Adjustments**: Adjust limits based on budget and usage patterns
4. **Unlimited Access**: Grant sparingly to trusted users only

## Troubleshooting

### User Can't Use Bot

1. Check if user has exceeded their personal limits
2. Check if guild pool is exhausted
3. Verify limits.json configuration
4. Check for typos in user/guild IDs

### Guild Pool Not Working

1. Verify guild ID is correct in limits.json
2. Check JSON syntax is valid
3. Restart bot after configuration changes
4. Verify guild has remaining tokens

### High Token Usage

1. Use `/token-stats` to identify top users
2. Check which models are consuming most tokens
3. Review charge source breakdown
4. Consider lowering limits for expensive models

## Configuration Examples

### Small Community Server
```json
{
  "guilds": {
    "guild_id": {
      "token_pool": 1000000,
      "member_limit": 10000
    }
  }
}
```

### Large Server with Roles
```json
{
  "guilds": {
    "guild_id": {
      "token_pool": 50000000,
      "member_limit": 50000,
      "role_limits": {
        "premium_role": 200000,
        "staff_role": 500000
      },
      "member_bypasses": ["admin_id"]
    }
  }
}
```

### Per-Model Configuration
```json
{
  "default_limits": {
    "models": {
      "llama-local": {"user_limit": 2000000, "guild_limit": 10000000},
      "gpt-4": {"user_limit": 25000, "guild_limit": 100000},
      "claude-3": {"user_limit": 75000, "guild_limit": 300000}
    }
  }
}
```

This system provides complete control over token usage while maintaining user-friendly access and detailed analytics for cost management.