from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any


APP_NAME = "FlipText"
CONFIG_VERSION = 1
DEFAULT_SYSTEM_PROMPT = (
    "You are a professional translator. Translate the user's text accurately and naturally. "
    "Return only the translated text. Preserve line breaks, formatting, and tone. "
    "Do not add explanations, quotation marks, notes, or extra text."
)


def get_user_config_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / ".config" / APP_NAME


def get_config_path() -> Path:
    return get_user_config_dir() / "config.json"


def default_config() -> dict[str, Any]:
    return {
        "version": CONFIG_VERSION,
        "translation": {
            "engine": "edge",
            "active_provider_id": "",
            "active_model_id": "",
        },
        "providers": [],
    }


def ensure_config(script_dir: Path | None = None) -> dict[str, Any]:
    config_path = get_config_path()
    if config_path.exists():
        return load_config(config_path)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = default_config()
    save_config(config)
    return config


def load_config(path: Path | None = None) -> dict[str, Any]:
    target = path or get_config_path()
    with target.open("r", encoding="utf-8") as fh:
        config = json.load(fh)
    normalize_config(config)
    return config


def save_config(config: dict[str, Any], path: Path | None = None) -> None:
    normalize_config(config)
    target = path or get_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_config(config: dict[str, Any]) -> None:
    config.setdefault("version", CONFIG_VERSION)
    translation = config.setdefault("translation", {})
    translation["engine"] = normalize_engine(translation.get("engine", "edge"))
    translation.setdefault("active_provider_id", "")
    translation.setdefault("active_model_id", "")

    providers = config.setdefault("providers", [])
    for provider in providers:
        provider["id"] = provider.get("id") or make_id("provider")
        provider["name"] = provider.get("name", "").strip() or "Untitled Provider"
        provider["base_url"] = provider.get("base_url", "").strip()
        provider["api_key"] = provider.get("api_key", "").strip()
        models = provider.setdefault("models", [])
        for model in models:
            model["id"] = model.get("id") or make_id("model")
            model["name"] = model.get("name", "").strip() or "Untitled Model"
            model["enabled"] = bool(model.get("enabled", True))
            model["timeout_ms"] = normalize_timeout(model.get("timeout_ms", 30000))
            model["system_prompt"] = (
                str(model.get("system_prompt", DEFAULT_SYSTEM_PROMPT)).strip() or DEFAULT_SYSTEM_PROMPT
            )

    active = get_active_profile(config)
    if active is None:
        translation["active_provider_id"] = ""
        translation["active_model_id"] = ""
        first = get_first_enabled_profile(config)
        if first:
            translation["active_provider_id"] = first[0]["id"]
            translation["active_model_id"] = first[1]["id"]


def normalize_engine(value: str) -> str:
    return "llm" if str(value).strip().lower() == "llm" else "edge"


def normalize_timeout(value: Any) -> int:
    text = str(value).strip()
    if not text.isdigit():
        return 30000
    timeout = int(text)
    return timeout if timeout >= 1000 else 30000


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def iter_profiles(config: dict[str, Any]) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    translation = config["translation"]
    active_provider_id = translation.get("active_provider_id", "")
    active_model_id = translation.get("active_model_id", "")

    for provider in config.get("providers", []):
        for model in provider.get("models", []):
            profile_id = build_profile_id(provider["id"], model["id"])
            profiles.append(
                {
                    "id": profile_id,
                    "provider_id": provider["id"],
                    "model_id": model["id"],
                    "provider_name": provider["name"],
                    "model_name": model["name"],
                    "label": f"{provider['name']} / {model['name']}",
                    "enabled": bool(model.get("enabled", True)),
                    "timeout_ms": model["timeout_ms"],
                    "is_active": provider["id"] == active_provider_id and model["id"] == active_model_id,
                }
            )
    return profiles


def build_profile_id(provider_id: str, model_id: str) -> str:
    return f"{provider_id}::{model_id}"


def split_profile_id(profile_id: str) -> tuple[str, str]:
    provider_id, _, model_id = profile_id.partition("::")
    return provider_id, model_id


def get_active_profile(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    translation = config.get("translation", {})
    provider_id = translation.get("active_provider_id", "")
    model_id = translation.get("active_model_id", "")
    if not provider_id or not model_id:
        return None
    return find_profile(config, provider_id, model_id)


def get_first_enabled_profile(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for provider in config.get("providers", []):
        for model in provider.get("models", []):
            if model.get("enabled", True):
                return provider, model
    return None


def find_profile(
    config: dict[str, Any], provider_id: str, model_id: str
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for provider in config.get("providers", []):
        if provider["id"] != provider_id:
            continue
        for model in provider.get("models", []):
            if model["id"] == model_id:
                return provider, model
    return None


def resolve_profile(config: dict[str, Any], profile_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    if profile_id:
        provider_id, model_id = split_profile_id(profile_id)
        found = find_profile(config, provider_id, model_id)
        if found is not None:
            return found
        raise RuntimeError(f"Profile '{profile_id}' was not found.")

    active = get_active_profile(config)
    if active is not None:
        return active

    raise RuntimeError("No active LLM profile is configured.")


def set_engine(config: dict[str, Any], engine: str) -> None:
    config["translation"]["engine"] = normalize_engine(engine)


def set_active_profile(config: dict[str, Any], profile_id: str) -> None:
    provider_id, model_id = split_profile_id(profile_id)
    found = find_profile(config, provider_id, model_id)
    if found is None:
        raise RuntimeError(f"Profile '{profile_id}' was not found.")
    config["translation"]["active_provider_id"] = provider_id
    config["translation"]["active_model_id"] = model_id
