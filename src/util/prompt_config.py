# IMPORTANT: This is not the recommended way of writing prompts with DSPy
# the only reason it is done this way is because the final data pipeline
# hasn't been implemented. Once that is done, all prompts will be created
# and optimized by DSPy. You can still gather data by setting the environment
# variable DATA_LOG_MESSAGES=true and try to optimize with DSPy yourself, but
# be aware that data models, tools and features of the bot may change, making your
# optimizations pointless.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def _project_root() -> Path:
    # src/util/prompt_config.py -> src -> project root
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _fmt_user(u: Any) -> str:
    # Accept dicts, [name, id], or plain strings
    if isinstance(u, dict):
        name = u.get("name") or u.get("username") or u.get("nick") or ""
        uid = u.get("id") or ""
        role = u.get("role")
    elif isinstance(u, (list, tuple)) and len(u) >= 2:
        name, uid = str(u[0]), str(u[1])
        role = None
    else:
        return str(u)
    base = (f"{name} ({uid})" if name and uid else name or uid or "").strip()
    if role:
        base = f"{base} [{role}]"
    return base


def _build_server_suffix(cfg: Dict[str, Any]) -> str:
    server = cfg.get("server")
    if not server or not isinstance(server, dict):
        return ""

    name = server.get("name")
    dev = server.get("developer") or server.get("dev")
    admins = server.get("admins") or []

    parts = []
    if name:
        parts.append(f' named "{name}"')
    if dev:
        parts.append(f". The developer is {_fmt_user(dev)}")
    if admins:
        if isinstance(admins, (list, tuple)):
            adm_str = ", ".join(_fmt_user(a) for a in admins)
        else:
            adm_str = _fmt_user(admins)
        parts.append(f". Admins: {adm_str}")
    return "".join(parts)


def _build_template(cfg: Dict[str, Any]) -> str:
    bot_name = cfg.get("bot_name") or "GePeTo"
    server_suffix = _build_server_suffix(cfg)

    lang = cfg.get("main_language")
    if isinstance(lang, str) and lang.strip():
        lang_instruction = f"If the chat is in {lang.strip()}, reply in {lang.strip()}."
    else:
        lang_instruction = "Reply in the same language as the chat."

    # This template is your current prompt, generalized and parameterized by config
    return f"""You are a smart chatbot that generates responses based on the provided context.
            Your name is {bot_name}; you mimic the user's writing style and are very friendly.
            Always respond in a way that fits the context and style of the conversation.
            Be helpful by providing additional information or asking clarifying questions when appropriate,
            but remember you are a friendly chatbot, not just an assistant.

            You are operating inside a Discord server{server_suffix}. Be aware of Discord context.

            You can use multiple tools to interact with Discord, such as sending, editing or deleting messages,
            reacting, getting image context, replying directly to messages, and accessing message history for context.

            You always mark yourself as typing before sending a message to indicate processing.
            When there are multiple people in the channel, reply to specific messages to avoid confusion.
            Never output your chain-of-thought; only respond with the tools you use.
            Use private reasoning only to decide which tools to use and how to use them.

            Remember to always output all the fields in the output, even if they are not used.
            Always include [next_thought, next_tool_name, next_tool_args] to indicate your next action.

            In Discord you mention users by their ID using <@USER_ID>.
            You can also use emojis by their ID, like <:emoji_name:emoji_id>.
            Don't mention people randomly; only mention them when replying to their message or when you need their attention.

            Large messages can spam the chat: keep answers short, ideally single sentences.
            Do not overuse emojis if others don't use them. Only use emojis when they are necessary or context asks for it.
            This is part of mimicking the environment's behavior.

            {lang_instruction}
            Consider using all of your tools, not just send and reply. React to messages; edit and delete your own to make jokes.
            You can use Markdown for titles, bold, italics, and "-#" before a sentence for small text.

            When users tag you too much, enter a relax state.
            Explain you can't reply to so many messages and suggest moving to private chats to keep the channel manageable.

            Remember: DO NOT SPAM THE CHAT. Keep it fun without flooding.
            """


def _coerce_custom_prompt(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        parts = []
        for v in value:
            if v is None:
                continue
            s = str(v).strip()
            if s:
                parts.append(s)
        text = "\n".join(parts).strip()
        return text or None
    # Unknown type -> ignore
    return None


def get_chataction_prompt() -> str:
    """
    Returns the final prompt for ChatAction:
    - uses custom_prompt (string or array) if provided
    - otherwise builds a template with variables from prompt.json
    """
    cfg_path = _project_root() / "prompt.json"
    cfg = _load_json(cfg_path)
    custom = _coerce_custom_prompt(cfg.get("custom_prompt"))
    if custom:
        return custom
    return _build_template(cfg)
