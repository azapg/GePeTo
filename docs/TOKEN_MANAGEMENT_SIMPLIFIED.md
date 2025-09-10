# Simplified Token Management System

This document describes the new simplified token management system for GePeTo.

## Overview

The token management system has been completely simplified to focus on **per-user per-model limits** only. No more complex guild pools, role-based limits, or charge source tracking.

## How It Works

1. **Per-User Per-Model Limits**: Each user has a token limit for each AI model
2. **Default Limits**: 100,000 tokens per user per model per 30 days
3. **Unlimited Access**: Set limit to `-1` for unlimited tokens (still tracked)
4. **Simple Tracking**: Usage is tracked and displayed correctly in `/token-usage`

## Admin Commands

| Command | Description |
|---------|-------------|
| `/token-set-limit user limit` | Set token limit for a user on current model |
| `/token-set-limit-all limit` | Set limit for all server members on current model |
| `/token-reset-usage user` | Reset all token usage for a user |
| `/token-set-unlimited user` | Give unlimited tokens on all models |
| `/token-usage` | Check your token usage (available to all users) |
| `/token-stats` | View overall statistics (admin only) |

## Examples

```bash
# Give a user 50,000 tokens for the current model
/token-set-limit user:@john limit:50000

# Give unlimited access to a trusted user
/token-set-unlimited user:@admin

# Set all server members to 200,000 tokens for current model
/token-set-limit-all limit:200000

# Reset a user's usage (like giving them 0 tokens used)
/token-reset-usage user:@spammer
```

## Database Schema

- **token_usage**: Tracks all token usage with user_id, model, tokens, timestamp
- **user_limits**: Stores per-user per-model limits (-1 = unlimited)

## Benefits

- ✅ **Simple**: Easy to understand and manage
- ✅ **Working**: Usage tracking and display actually works
- ✅ **Flexible**: Per-model limits allow different costs for different models
- ✅ **Scalable**: Admin commands for bulk management
- ✅ **Clean**: No complex configuration files or hierarchies