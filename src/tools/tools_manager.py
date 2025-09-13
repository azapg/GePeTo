from typing import Dict, Callable

TOOLS: Dict[str, Callable] = {}

def tool(func: Callable) -> Callable:
    """
    Decorator to register a function as a tool.
    
    Args:
        func: The function to register as a tool
        
    Returns:
        The original function, unchanged but registered
    """
    TOOLS[func.__name__] = func
    
    return func

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
        raise KeyError(f"Tool '{name}' not found. Available tools: {list(TOOLS.keys())}")
    return TOOLS[name]

def get_all_tools() -> Dict[str, Callable]:
    """
    Get all registered tools.
    
    Returns:
        Dictionary of all registered tools
    """
    return TOOLS.copy()

def list_tools() -> list:
    """
    Get a list of all registered tool names.
    
    Returns:
        List of tool names
    """
    return list(TOOLS.keys())
