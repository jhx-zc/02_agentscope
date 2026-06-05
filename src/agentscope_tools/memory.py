"""Backward-compatible re-export for JSON-backed memory tools."""

from agentscope_tools.ori_tools.memory import (  # noqa: F401
    MEMORY_DIR,
    USER_PREFERENCES_PATH,
    user_memory_clear_preferences,
    user_memory_delete_preference,
    user_memory_get_preference,
    user_memory_list_preferences,
    user_memory_outline,
    user_memory_save_preference,
)
