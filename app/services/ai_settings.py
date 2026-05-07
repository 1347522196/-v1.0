from __future__ import annotations

from typing import Any


DEFAULT_MODEL = "deepseek-v4-flash"

_runtime_settings: dict[str, str] = {
    "api_key": "",
    "model": DEFAULT_MODEL,
}


def load_ai_settings() -> dict[str, Any]:
    api_key = _runtime_settings["api_key"].strip()
    model = _runtime_settings["model"].strip() or DEFAULT_MODEL
    return {
        "api_key": api_key,
        "model": model,
        "has_api_key": bool(api_key),
        "masked_api_key": mask_api_key(api_key),
        "source": "session" if api_key else "none",
    }


def save_ai_settings(*, api_key: str, model: str) -> dict[str, Any]:
    cleaned_key = api_key.strip()
    if cleaned_key:
        _runtime_settings["api_key"] = cleaned_key
    _runtime_settings["model"] = model.strip() or DEFAULT_MODEL
    return load_ai_settings()


def clear_ai_settings() -> dict[str, Any]:
    _runtime_settings["api_key"] = ""
    _runtime_settings["model"] = DEFAULT_MODEL
    return load_ai_settings()


def mask_api_key(api_key: str) -> str:
    value = api_key.strip()
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"
