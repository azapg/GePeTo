import functools
from typing import Dict, Callable, Optional, List

import discord

TOOLS: Dict[str, Callable] = {}


class ToolContext:
    """Immutable context for a single request"""

    def __init__(self, initiator: discord.Message, permissions_checker: Callable,
                 confirmation_sender: Callable):
        self._initiator = initiator
        self._permissions_checker = permissions_checker
        self._confirmation_sender = confirmation_sender

    @property
    def initiator(self) -> discord.Message:
        return self._initiator

    async def check_permissions(self, permissions: List[str]) -> bool:
        return await self._permissions_checker(self._initiator, permissions)

    async def request_confirmation(self, action: str) -> bool:
        return await self._confirmation_sender(self._initiator, action)


class ProtectedTool:
    """A tool that requires permission checks and/or user confirmation before execution."""

    def __init__(self, original_func: Callable, permissions: Optional[List[str]] = None,
                 needs_confirmation: bool = False):
        self.original_func = original_func
        self.permissions = permissions
        self.needs_confirmation = needs_confirmation
        self.__name__ = original_func.__name__
        self.__doc__ = original_func.__doc__

    async def __call__(self, context: ToolContext, *args, **kwargs):
        """Execute tool with context-based protection"""
        if self.permissions:
            if not await context.check_permissions(self.permissions):
                raise PermissionError(f"User lacks permissions: {self.permissions}")

        if self.needs_confirmation:
            # TODO: This description could be improved. Maybe the function could have a custom description?
            #   you could possible prompt inject the bot to use another guild_id, and most users won't probably
            #   notice it. The tool itself could decide how to describe the args of its call, and show the actual
            #   guild, for a create_channel tool for example.
            action_name = self.original_func.__name__
            parts = [f"🛠️ {action_name}"]
            if args:
                parts.append("• Positional args:")
                parts.extend([f"   {i+1}. {a!r}" for i, a in enumerate(args)])
            if kwargs:
                parts.append("• Parameters:")
                parts.extend([f"   - {k}: {v!r}" for k, v in kwargs.items()])
            action_desc = "\n".join(parts)
            confirmed = await context.request_confirmation(action_desc)
            if not confirmed:
                raise ValueError("Operation cancelled by user")

        return await self.original_func(*args, **kwargs)


def tool(_func: Optional[Callable] = None, *, permissions: Optional[List[str]] = None,
         needs_confirmation: bool = False):
    """
    Decorator to register a function as a tool.
    
    Args:
        _func: The function to register (automatically passed when used as a decorator)
        permissions: Permissions to check before executing the tool
        needs_confirmation: Whether the tool needs user confirmation before execution
    Returns:
        The original function, unchanged but registered

    Can be used as:
        - @tool
        - @tool(permissions=[...], needs_confirmation=True)
    """

    def _register(func: Callable) -> Callable:
        if permissions or needs_confirmation:
            protected_tool = ProtectedTool(func, permissions, needs_confirmation)
            TOOLS[func.__name__] = protected_tool
        else:
            TOOLS[func.__name__] = func
        return func

    if callable(_func):
        return _register(_func)
    return _register


def get_tool(name: str) -> Callable:
    """
    Get a specific tool by name.
    
    Args:
        name: The name of the tool to retrieve
        
    Returns:
        The tool function
        
    Raises:
        KeyError: If the tool is not found
    """
    if name not in TOOLS:
        raise KeyError(f"Tool '{name}' not found.")
    return TOOLS[name]


def get_all_tools() -> Dict[str, Callable]:
    """
    Get all registered tools.
    
    Returns:
        Dictionary of all registered tools
    """
    return TOOLS


def list_tools() -> list:
    """
    Get a list of all registered tool names.
    
    Returns:
        List of tool names
    """
    return list(TOOLS.keys())


def tools_with_context(context: ToolContext) -> list[Callable]:
    """
    Get all tools wrapped to accept a ToolContext as the first argument.

    Args:
        context: The ToolContext to bind to each tool
    Returns:
        List of tool functions registered for agentic use.
    """
    tools = {}
    for name, func in TOOLS.items():
        if isinstance(func, ProtectedTool):
            @functools.wraps(func)
            async def wrapped_tool(*args, _func=func, **kwargs):
                return await _func(context, *args, **kwargs)

            tools[name] = wrapped_tool
        else:
            tools[name] = func
    return list(tools.values())
