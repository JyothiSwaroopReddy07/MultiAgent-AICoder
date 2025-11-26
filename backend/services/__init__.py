"""
Services module for AI Code Generator
"""

from .execution_service import (
    execute_application,
    stop_application,
    get_running_applications,
    cleanup_all_applications
)

__all__ = [
    "execute_application",
    "stop_application", 
    "get_running_applications",
    "cleanup_all_applications"
]

