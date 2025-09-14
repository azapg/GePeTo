"""
Memory validation utilities for the bot startup.
Provides cross-platform memory checking to prevent silent failures.
"""
from typing import Tuple
import os
import psutil


def _read_cgroup_memory_limit() -> int | None:
    """
    Return cgroup memory limit in bytes if present and sensible, otherwise None.
    Checks both cgroup v1 and v2 locations.
    """
    cgroup_v1 = "/sys/fs/cgroup/memory/memory.limit_in_bytes"
    cgroup_v2 = "/sys/fs/cgroup/memory.max"
    try:
        if os.path.exists(cgroup_v1):
            with open(cgroup_v1, "r") as f:
                limit = int(f.read().strip())
                if limit < (1 << 60):
                    return limit
        if os.path.exists(cgroup_v2):
            with open(cgroup_v2, "r") as f:
                raw = f.read().strip()
                if raw.isdigit():
                    limit = int(raw)
                    if limit < (1 << 60):
                        return limit
    except (OSError, Exception):
        pass
    return None


def get_system_memory_info() -> Tuple[int, int]:
    """
    Get total and available system memory in MB.

    Returns:
        Tuple of (total_memory_mb, available_memory_mb)
    """
    mem = psutil.virtual_memory()
    total_bytes = mem.total
    available_bytes = mem.available

    # If running in a constrained container, respect the cgroup memory limit.
    cgroup_limit = _read_cgroup_memory_limit()
    if cgroup_limit is not None and cgroup_limit < total_bytes:
        used_bytes = total_bytes - available_bytes
        total_bytes = cgroup_limit
        available_bytes = max(0, total_bytes - used_bytes)

    return total_bytes // (1024 * 1024), available_bytes // (1024 * 1024)


def estimate_minimum_memory_requirement() -> int:
    """
    Estimate minimum memory requirement for the bot in MB.

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

    if total_mb == 0:
        if show_warnings:
            print("Warning: Could not determine system memory. Proceeding with caution.")
        return True

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

    return True


def check_memory_before_import(module_name: str) -> None:
    """
    Check memory before importing potentially heavy modules.

    Args:
        module_name: Name of the module being imported for error context
    """
    total_mb, available_mb = get_system_memory_info()
    min_required = estimate_minimum_memory_requirement()

    if available_mb < min_required:
        print(f"Warning: Low memory ({available_mb} MB available) while importing {module_name}")
        print("This may cause import failures or slow performance.")