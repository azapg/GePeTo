"""
Memory validation utilities for GePeTo bot startup.
Provides cross-platform memory checking to prevent silent failures.
"""
import os
from typing import Tuple


def get_system_memory_info() -> Tuple[int, int]:
    """
    Get total and available system memory in MB.
    
    Returns:
        Tuple of (total_memory_mb, available_memory_mb)
    """
    try:
        # Try psutil first if available
        import psutil
        memory = psutil.virtual_memory()
        return memory.total // (1024 * 1024), memory.available // (1024 * 1024)
    except ImportError:
        pass
    
    try:
        # Fallback to Linux /proc/meminfo
        with open('/proc/meminfo', 'r') as f:
            meminfo = {}
            for line in f:
                if ':' in line:
                    key, value = line.split(':', 1)
                    # Extract numeric value (remove 'kB' unit)
                    meminfo[key.strip()] = int(value.strip().split()[0])
        
        total_mb = meminfo.get('MemTotal', 0) // 1024
        available_mb = meminfo.get('MemAvailable', meminfo.get('MemFree', 0)) // 1024
        return total_mb, available_mb
    except (FileNotFoundError, ValueError, KeyError):
        pass
    
    try:
        # Fallback to os.sysconf (Unix systems)
        page_size = os.sysconf('SC_PAGESIZE')
        total_pages = os.sysconf('SC_PHYS_PAGES')
        avail_pages = os.sysconf('SC_AVPHYS_PAGES')
        total_mb = (page_size * total_pages) // (1024 * 1024)
        available_mb = (page_size * avail_pages) // (1024 * 1024)
        return total_mb, available_mb
    except (OSError, ValueError):
        pass
    
    # If all methods fail, return unknown values
    return 0, 0


def estimate_minimum_memory_requirement() -> int:
    """
    Estimate minimum memory requirement for GePeTo bot in MB.
    
    Returns:
        Estimated minimum memory requirement in MB
    """
    # Conservative estimate based on dependencies:
    # - Python interpreter: ~20-50 MB
    # - Discord.py: ~50-100 MB  
    # - DSPy (ML framework): ~200-500 MB
    # - MLflow: ~50-100 MB
    # - Model inference: ~100-1000 MB (depending on model)
    # - OS overhead and buffers: ~200 MB
    return 512  # 512 MB minimum, which is quite conservative


def estimate_recommended_memory() -> int:
    """
    Estimate recommended memory for optimal performance in MB.
    
    Returns:
        Recommended memory in MB
    """
    # For smooth operation with larger models and multiple concurrent operations
    return 2048  # 2 GB recommended


def validate_memory_requirements(show_warnings: bool = True) -> bool:
    """
    Validate if system has sufficient memory to run GePeTo bot.
    
    Args:
        show_warnings: Whether to print warning messages
        
    Returns:
        True if memory is sufficient, False if critically low
    """
    total_mb, available_mb = get_system_memory_info()
    
    if total_mb == 0:  # Could not determine memory
        if show_warnings:
            print("Warning: Could not determine system memory. Proceeding with caution.")
        return True  # Assume OK if we can't check
    
    min_required = estimate_minimum_memory_requirement()
    recommended = estimate_recommended_memory()
    
    if available_mb < min_required:
        if show_warnings:
            print(f"ERROR: Insufficient memory to run GePeTo bot!")
            print(f"Available: {available_mb} MB, Minimum required: {min_required} MB")
            print(f"Total system memory: {total_mb} MB")
            print()
            print("Recommendations:")
            print("- Close other applications to free up memory")
            print("- Consider upgrading your system memory")
            print(f"- Ensure at least {recommended} MB RAM for optimal performance")
            if total_mb < recommended:
                print("- Your system may struggle with larger AI models")
            print()
        return False
    
    if available_mb < recommended:
        if show_warnings:
            print(f"Warning: Memory is below recommended levels")
            print(f"Available: {available_mb} MB, Recommended: {recommended} MB")
            print(f"Total system memory: {total_mb} MB")
            print("The bot may run slowly or fail with larger models.")
            print()
        # Continue despite warning
        
    return True


def check_memory_before_import(module_name: str) -> None:
    """
    Check memory before importing potentially heavy modules.
    
    Args:
        module_name: Name of the module being imported for error context
    """
    total_mb, available_mb = get_system_memory_info()
    min_required = estimate_minimum_memory_requirement()
    
    if available_mb > 0 and available_mb < min_required:
        print(f"Warning: Low memory ({available_mb} MB available) while importing {module_name}")
        print("This may cause import failures or slow performance.")