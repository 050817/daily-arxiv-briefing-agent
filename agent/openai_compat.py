from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from agent.io_utils import load_json, resolve_path


LOCAL_SETTINGS_PATH = resolve_path("web_app/local_settings.json")


def load_openai_compatible_settings(settings_path: str | Path | None = None) -> dict[str, str]:
    path = resolve_path(settings_path or LOCAL_SETTINGS_PATH)
    if not path.exists():
        return {}

    try:
        payload = load_json(path)
    except (OSError, ValueError):
        return {}

    return {
        "api_url": str(payload.get("api_url", "")).strip(),
        "model": str(payload.get("model", "")).strip(),
        "api_key": str(payload.get("api_key", "")).strip(),
    }


def resolve_openai_compatible_config(
    *,
    configured_base_url: str = "",
    configured_model: str = "",
    configured_api_key: str = "",
    default_base_url: str = "https://api.openai.com/v1",
    default_model: str = "gpt-4.1-mini",
) -> dict[str, str]:
    settings = load_openai_compatible_settings()
    api_url = (
        str(configured_base_url).strip()
        or settings.get("api_url", "")
        or os.environ.get("OPENAI_BASE_URL", "").strip()
        or default_base_url
    )
    return {
        "api_url": normalize_openai_compatible_base_url(api_url),
        "model": (
            str(configured_model).strip()
            or settings.get("model", "")
            or os.environ.get("OPENAI_MODEL", "").strip()
            or default_model
        ),
        "api_key": (
            str(configured_api_key).strip()
            or settings.get("api_key", "")
            or os.environ.get("OPENAI_API_KEY", "").strip()
        ),
    }


def has_openai_compatible_api_key(configured_api_key: str = "") -> bool:
    return bool(resolve_openai_compatible_config(configured_api_key=configured_api_key).get("api_key"))


def normalize_openai_compatible_base_url(api_url: str) -> str:
    value = str(api_url or "").strip().rstrip("/")
    if not value:
        return value

    parsed = urlsplit(value)
    if parsed.scheme and parsed.netloc and parsed.path in {"", "/"}:
        return urlunsplit((parsed.scheme, parsed.netloc, "/v1", "", ""))
    return value
