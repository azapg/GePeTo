import discord

def _snapshot_text(text: str, limit: int) -> str:
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit] + "..."

def _format_message_context(msg: discord.Message, verbosity: int) -> str:
    try:
        author = f"{msg.author}" + (f" ({msg.author.id})" if verbosity >= 3 else "")
        if msg.guild:
            guild = f"{msg.guild.name}" + (f" ({msg.guild.id})" if verbosity >= 3 else "")
            channel_name = getattr(msg.channel, "name", str(msg.channel))
            channel = f"#{channel_name}" + (f" ({msg.channel.id})" if verbosity >= 3 else "")
            location = f"{guild}/{channel}"
        else:
            location = "DM"
        snippet_len = 50 if verbosity == 1 else 90 if verbosity == 2 else 180
        snippet = _snapshot_text(getattr(msg, "content", ""), snippet_len)
        extras = f", attachments={len(msg.attachments)}" if verbosity >= 2 and getattr(msg, "attachments", None) else ""
        return f'from {author} in {location}: "{snippet}"{extras}'
    except Exception:
        return "context unavailable"