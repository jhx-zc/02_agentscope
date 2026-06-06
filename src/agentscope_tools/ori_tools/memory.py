"""JSON-backed user preference memory tools."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentscope_tools.ori_tools.scanner import WORKSPACE_ROOT

MEMORY_DIR = WORKSPACE_ROOT / ".agentscope_memory"
USER_PREFERENCES_PATH = MEMORY_DIR / "user_preferences.json"


def _now_iso() -> str:
    """Return a stable UTC timestamp for memory metadata."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def _empty_store() -> dict[str, Any]:
    """Create the base JSON document used for user preference memory."""
    return {
        "version": 1,
        "kind": "user_preferences",
        "updated_at": None,
        "preferences": {},
    }


def _validate_key(key: str) -> str:
    """Normalize and validate a memory key."""
    normalized = key.strip()
    if not normalized:
        raise ValueError("key must not be empty")
    return normalized


def _validate_label(value: str, field_name: str) -> str:
    """Normalize and validate a short label-like value."""
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _load_store() -> dict[str, Any]:
    """Load the JSON store, returning an empty document when it does not exist."""
    if not USER_PREFERENCES_PATH.exists():
        return _empty_store()

    try:
        store = json.loads(USER_PREFERENCES_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"memory file contains invalid JSON: {USER_PREFERENCES_PATH}"
        ) from exc

    if not isinstance(store, dict):
        raise ValueError("memory file must contain a JSON object")

    preferences = store.setdefault("preferences", {})
    if not isinstance(preferences, dict):
        raise ValueError("memory file field 'preferences' must be a JSON object")

    store.setdefault("version", 1)
    store.setdefault("kind", "user_preferences")
    store.setdefault("updated_at", None)
    return store


def _save_store(store: dict[str, Any]) -> None:
    """Persist the JSON store with a simple atomic replace."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = USER_PREFERENCES_PATH.with_suffix(".json.tmp")
    temp_path.write_text(
        json.dumps(store, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(USER_PREFERENCES_PATH)


def _memory_outline_entry(memory: dict[str, Any], include_preview: bool) -> dict[str, Any]:
    """Build a lightweight index entry without loading full memory content."""
    entry = {
        "key": memory.get("key"),
        "category": memory.get("category"),
        "source": memory.get("source"),
        "created_at": memory.get("created_at"),
        "updated_at": memory.get("updated_at"),
    }
    if include_preview:
        value = str(memory.get("value", ""))
        entry["preview"] = value[:80]
        entry["truncated"] = len(value) > 80
    return entry


def hard_user_memories() -> list[dict[str, Any]]:
    store = _load_store()
    hard_memories = []
    for memory in store["preferences"].values():
        if memory.get('hard', False):
            hard_memories.append(memory)
    return hard_memories


def user_memory_outline(
    category: str | None = None,
    include_preview: bool = False,
) -> dict[str, Any]:
    """Return a lightweight outline of user preference memory.

    Use this before loading memory values. The outline supports progressive
    import: an agent can inspect available categories and keys first, then call
    ``user_memory_get_preference`` only for the specific keys it needs.

    Args:
        category: Optional category filter. When omitted, all categories are
            included.
        include_preview: Whether to include a short 80-character value preview.
            Defaults to ``False`` so full preference values stay unloaded.

    Returns:
        A dictionary containing category counts and lightweight memory index
        entries. Full ``value`` fields are intentionally not returned.
    """
    store = _load_store()
    normalized_category = category.strip() if category else None
    if normalized_category == "":
        raise ValueError("category must not be empty when provided")

    categories: dict[str, dict[str, Any]] = {}
    for memory in store["preferences"].values():
        memory_category = memory.get("category", "general")
        if normalized_category is not None and memory_category != normalized_category:
            continue

        category_outline = categories.setdefault(
            memory_category,
            {
                "category": memory_category,
                "count": 0,
                "keys": [],
                "memories": [],
            },
        )
        category_outline["count"] += 1
        category_outline["keys"].append(memory.get("key"))
        category_outline["memories"].append(
            _memory_outline_entry(memory, include_preview=include_preview)
        )

    for category_outline in categories.values():
        category_outline["keys"].sort()
        category_outline["memories"].sort(key=lambda item: item.get("key", ""))

    sorted_categories = [
        categories[name]
        for name in sorted(categories)
    ]

    return {
        "kind": store.get("kind"),
        "updated_at": store.get("updated_at"),
        "category": normalized_category,
        "total_count": sum(item["count"] for item in sorted_categories),
        "categories": sorted_categories,
        "tip": "Call user_memory_get_preference with a specific key to load a full memory value.",
    }


def user_memory_save_preference(
    key: str,
    value: str,
    category: str = "general",
    source: str = "user",
    hard: bool = False,
) -> dict[str, Any]:
    """Save or update one explicitly requested user preference memory.

    Call this tool only when the user clearly asks the agent to remember,
    save, record, or use a preference in the future. Do not infer preferences
    silently from ordinary conversation. Examples of valid triggers include:
    "remember that I prefer Chinese replies", "save this as my coding style",
    "以后默认用中文回答", and "记住我的项目偏好". If the user said that you must 
    remenber this, its means that this preference is a hard preference.

    Args:
        key: Stable preference key, for example ``language`` or
            ``code_comment_style``.
        value: Preference content to remember.
        category: Preference category used for filtering. Defaults to
            ``general``.
        source: Where this memory came from. Defaults to ``user``.
        hard: Dose preference is a hard rule.

    Returns:
        A dictionary containing the saved memory record, whether it replaced an
        existing record, and the JSON file path.
    """
    normalized_key = _validate_key(key)
    normalized_category = _validate_label(category, "category")
    normalized_source = _validate_label(source, "source")
    timestamp = _now_iso()

    store = _load_store()
    preferences = store["preferences"]
    existed = normalized_key in preferences

    record = {
        "key": normalized_key,
        "value": value,
        "category": normalized_category,
        "source": normalized_source,
        "created_at": preferences.get(normalized_key, {}).get("created_at", timestamp),
        "updated_at": timestamp,
        "hard": hard,
    }
    preferences[normalized_key] = record
    store["updated_at"] = timestamp
    _save_store(store)

    return {
        "saved": True,
        "replaced": existed,
        "memory": record,
    }


def user_memory_get_preference(key: str) -> dict[str, Any]:
    """Get one user preference memory by key.

    Args:
        key: Stable preference key to read.

    Returns:
        A dictionary containing ``found`` and, when present, the memory record.
    """
    normalized_key = _validate_key(key)
    store = _load_store()
    memory = store["preferences"].get(normalized_key)

    return {
        "key": normalized_key,
        "found": memory is not None,
        "memory": memory,
    }


def user_memory_list_preferences(category: str | None = None) -> dict[str, Any]:
    """List user preference memories from the JSON file.

    Args:
        category: Optional category filter. When omitted, all preferences are
            returned.

    Returns:
        A dictionary containing the JSON file path, total count, and sorted
        memory records.
    """
    store = _load_store()
    normalized_category = category.strip() if category else None
    if normalized_category == "":
        raise ValueError("category must not be empty when provided")

    memories = list(store["preferences"].values())
    if normalized_category is not None:
        memories = [
            memory
            for memory in memories
            if memory.get("category") == normalized_category
        ]

    memories.sort(key=lambda memory: memory.get("key", ""))

    return {
        "category": normalized_category,
        "count": len(memories),
        "memories": memories,
    }


def user_memory_delete_preference(key: str) -> dict[str, Any]:
    """Delete one user preference memory by key.

    Args:
        key: Stable preference key to delete.

    Returns:
        A dictionary containing whether a memory was deleted and the deleted
        record when it existed.
    """
    normalized_key = _validate_key(key)
    timestamp = _now_iso()
    store = _load_store()
    deleted = store["preferences"].pop(normalized_key, None)

    if deleted is not None:
        store["updated_at"] = timestamp
        _save_store(store)

    return {
        "key": normalized_key,
        "deleted": deleted is not None,
        "memory": deleted,
    }


def user_memory_clear_preferences(confirm: bool = False) -> dict[str, Any]:
    """Clear all user preference memories from the JSON file.

    Args:
        confirm: Must be ``True`` to prevent accidental memory deletion.

    Returns:
        A dictionary containing how many preference memories were removed.

    Raises:
        ValueError: If ``confirm`` is not ``True``.
    """
    if not confirm:
        raise ValueError("confirm must be true to clear user preference memory")

    store = _load_store()
    removed_count = len(store["preferences"])
    timestamp = _now_iso()
    store["preferences"] = {}
    store["updated_at"] = timestamp
    _save_store(store)

    return {
        "cleared": True,
        "removed_count": removed_count,
    }
