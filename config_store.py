from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any


APP_NAME = "FlipText"
CONFIG_VERSION = 2
DEFAULT_SYSTEM_PROMPT = (
    "You are a professional translator. Translate the user's text accurately and naturally. "
    "Return only the translated text. Preserve line breaks, formatting, and tone. "
    "Do not add explanations, quotation marks, notes, or extra text."
)
DEFAULT_USER_PROMPT_TEMPLATE = "Translate the following text from {source_lang} to {target_lang}.\n\n{text}"
DEFAULT_SHOW_BINDINGS_SHORTCUT = "f1"
DEFAULT_EDGE_SHORTCUT = "f1+1"


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
        "prompt_library": [],
        "behavior_library": [
            {
                "id": "behavior-show-shortcuts",
                "name": "Show Shortcuts",
                "type": "show_shortcuts",
                "profile_id": "",
                "prompt_id": "",
            },
            {
                "id": "behavior-edge-translate",
                "name": "Edge Translate",
                "type": "edge_translate",
                "profile_id": "",
                "prompt_id": "",
            },
        ],
        "shortcut_bindings": [
            {"id": "binding-show-shortcuts", "shortcut": DEFAULT_SHOW_BINDINGS_SHORTCUT, "behavior_id": "behavior-show-shortcuts"},
            {"id": "binding-edge-translate", "shortcut": DEFAULT_EDGE_SHORTCUT, "behavior_id": "behavior-edge-translate"},
        ],
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
    _migrate_legacy_config(config)

    config["version"] = CONFIG_VERSION
    translation = config.setdefault("translation", {})
    translation["engine"] = normalize_engine(translation.get("engine", "edge"))
    translation.setdefault("active_provider_id", "")
    translation.setdefault("active_model_id", "")

    _normalize_providers(config)
    _normalize_prompts(config)
    _normalize_behaviors(config)
    _normalize_bindings(config)

    active = get_active_profile(config)
    if active is None:
        translation["active_provider_id"] = ""
        translation["active_model_id"] = ""
        first = get_first_enabled_profile(config)
        if first:
            translation["active_provider_id"] = first[0]["id"]
            translation["active_model_id"] = first[1]["id"]


def _migrate_legacy_config(config: dict[str, Any]) -> None:
    config.setdefault("providers", [])
    config.setdefault("translation", {})

    if "prompt_library" not in config:
        config["prompt_library"] = []
    if "behavior_library" not in config:
        config["behavior_library"] = []
    if "shortcut_bindings" not in config:
        config["shortcut_bindings"] = []

    legacy_presets = config.pop("prompt_presets", [])
    if legacy_presets:
        for preset in legacy_presets:
            prompt_id = make_id("prompt")
            behavior_id = make_id("behavior")
            config["prompt_library"].append(
                {
                    "id": prompt_id,
                    "name": preset.get("name", "").strip() or "Imported Prompt",
                    "system_prompt": str(preset.get("system_prompt", "")).strip(),
                    "user_prompt": "{text}",
                }
            )
            config["behavior_library"].append(
                {
                    "id": behavior_id,
                    "name": preset.get("name", "").strip() or "Imported Behavior",
                    "type": "llm_prompt",
                    "profile_id": "",
                    "prompt_id": prompt_id,
                }
            )
            shortcut = normalize_shortcut(preset.get("shortcut", ""))
            if shortcut:
                config["shortcut_bindings"].append(
                    {
                        "id": make_id("binding"),
                        "shortcut": shortcut,
                        "behavior_id": behavior_id,
                    }
                )


def _normalize_providers(config: dict[str, Any]) -> None:
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
            model["system_prompt"] = str(model.get("system_prompt", DEFAULT_SYSTEM_PROMPT)).strip() or DEFAULT_SYSTEM_PROMPT
            model["user_prompt_template"] = (
                str(model.get("user_prompt_template", DEFAULT_USER_PROMPT_TEMPLATE)).strip() or DEFAULT_USER_PROMPT_TEMPLATE
            )


def _normalize_prompts(config: dict[str, Any]) -> None:
    prompts = config.setdefault("prompt_library", [])
    for index, prompt in enumerate(prompts, start=1):
        prompt["id"] = prompt.get("id") or make_id("prompt")
        prompt["name"] = prompt.get("name", "").strip() or f"Prompt {index}"
        prompt["system_prompt"] = str(prompt.get("system_prompt", "")).strip()
        prompt["user_prompt"] = str(prompt.get("user_prompt", "{text}")).strip() or "{text}"


def _normalize_behaviors(config: dict[str, Any]) -> None:
    behaviors = config.setdefault("behavior_library", [])
    known_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []

    required = {
        "behavior-show-shortcuts": {
            "id": "behavior-show-shortcuts",
            "name": "Show Shortcuts",
            "type": "show_shortcuts",
            "profile_id": "",
            "prompt_id": "",
        },
        "behavior-edge-translate": {
            "id": "behavior-edge-translate",
            "name": "Edge Translate",
            "type": "edge_translate",
            "profile_id": "",
            "prompt_id": "",
        },
    }

    for behavior in behaviors:
        behavior_id = behavior.get("id") or make_id("behavior")
        if behavior_id in known_ids:
            behavior_id = make_id("behavior")
        known_ids.add(behavior_id)
        behavior_type = normalize_behavior_type(behavior.get("type", "llm_prompt"))
        normalized.append(
            {
                "id": behavior_id,
                "name": behavior.get("name", "").strip() or f"Behavior {len(normalized) + 1}",
                "type": behavior_type,
                "profile_id": str(behavior.get("profile_id", "")).strip(),
                "prompt_id": str(behavior.get("prompt_id", "")).strip(),
            }
        )

    existing = {item["id"] for item in normalized}
    for behavior_id, payload in required.items():
        if behavior_id not in existing:
            normalized.insert(0, dict(payload))

    config["behavior_library"] = normalized


def _normalize_bindings(config: dict[str, Any]) -> None:
    bindings = config.setdefault("shortcut_bindings", [])
    behavior_ids = {behavior["id"] for behavior in config.get("behavior_library", [])}
    used_shortcuts: set[str] = set()
    normalized: list[dict[str, Any]] = []

    for binding in bindings:
        shortcut = normalize_shortcut(binding.get("shortcut", ""))
        behavior_id = str(binding.get("behavior_id", "")).strip()
        if not shortcut or behavior_id not in behavior_ids or shortcut in used_shortcuts:
            continue
        used_shortcuts.add(shortcut)
        normalized.append(
            {
                "id": binding.get("id") or make_id("binding"),
                "shortcut": shortcut,
                "behavior_id": behavior_id,
            }
        )

    _ensure_binding(normalized, used_shortcuts, DEFAULT_SHOW_BINDINGS_SHORTCUT, "behavior-show-shortcuts")
    _ensure_binding(normalized, used_shortcuts, DEFAULT_EDGE_SHORTCUT, "behavior-edge-translate")
    config["shortcut_bindings"] = normalized


def _ensure_binding(bindings: list[dict[str, Any]], used_shortcuts: set[str], shortcut: str, behavior_id: str) -> None:
    if any(binding["behavior_id"] == behavior_id for binding in bindings):
        return
    if shortcut in used_shortcuts:
        return
    bindings.append({"id": make_id("binding"), "shortcut": shortcut, "behavior_id": behavior_id})
    used_shortcuts.add(shortcut)


def normalize_engine(value: str) -> str:
    return "llm" if str(value).strip().lower() == "llm" else "edge"


def normalize_timeout(value: Any) -> int:
    text = str(value).strip()
    if not text.isdigit():
        return 30000
    timeout = int(text)
    return timeout if timeout >= 1000 else 30000


def normalize_shortcut(value: Any) -> str:
    text = str(value or "").strip().lower().replace(" ", "")
    if not text:
        return ""
    parts = [part for part in text.split("+") if part]
    if not parts or len(parts) > 2:
        return ""
    return "+".join(parts)


def normalize_behavior_type(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"edge_translate", "show_shortcuts"}:
        return text
    return "llm_prompt"


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


def iter_prompts(config: dict[str, Any]) -> list[dict[str, Any]]:
    prompts: list[dict[str, Any]] = []
    for prompt in config.get("prompt_library", []):
        prompts.append(
            {
                "id": prompt["id"],
                "name": prompt["name"],
                "system_prompt": prompt["system_prompt"],
                "user_prompt": prompt["user_prompt"],
                "label": prompt["name"],
            }
        )
    return prompts


def iter_behaviors(config: dict[str, Any]) -> list[dict[str, Any]]:
    profiles = {profile["id"]: profile for profile in iter_profiles(config)}
    prompts = {prompt["id"]: prompt for prompt in iter_prompts(config)}
    items: list[dict[str, Any]] = []
    for behavior in config.get("behavior_library", []):
        profile = profiles.get(behavior["profile_id"])
        prompt = prompts.get(behavior["prompt_id"])
        items.append(
            {
                "id": behavior["id"],
                "name": behavior["name"],
                "type": behavior["type"],
                "profile_id": behavior["profile_id"],
                "prompt_id": behavior["prompt_id"],
                "profile_label": profile["label"] if profile else "",
                "prompt_label": prompt["label"] if prompt else "",
                "label": build_behavior_label(behavior, profile, prompt),
            }
        )
    return items


def build_behavior_label(behavior: dict[str, Any], profile: dict[str, Any] | None, prompt: dict[str, Any] | None) -> str:
    if behavior["type"] == "edge_translate":
        return f"{behavior['name']} [Edge]"
    if behavior["type"] == "show_shortcuts":
        return f"{behavior['name']} [Mappings]"
    profile_label = profile["label"] if profile else "No model"
    prompt_label = prompt["label"] if prompt else "No prompt"
    return f"{behavior['name']} [{profile_label}] + [{prompt_label}]"


def iter_bindings(config: dict[str, Any]) -> list[dict[str, Any]]:
    behaviors = {behavior["id"]: behavior for behavior in iter_behaviors(config)}
    items: list[dict[str, Any]] = []
    for binding in config.get("shortcut_bindings", []):
        behavior = behaviors.get(binding["behavior_id"])
        if behavior is None:
            continue
        items.append(
            {
                "id": binding["id"],
                "shortcut": binding["shortcut"],
                "behavior_id": binding["behavior_id"],
                "behavior_name": behavior["name"],
                "behavior_type": behavior["type"],
                "behavior_label": behavior["label"],
                "label": f"{format_shortcut_label(binding['shortcut'])} -> {behavior['label']}",
            }
        )
    return items


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


def find_profile(config: dict[str, Any], provider_id: str, model_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for provider in config.get("providers", []):
        if provider["id"] != provider_id:
            continue
        for model in provider.get("models", []):
            if model["id"] == model_id:
                return provider, model
    return None


def build_profile_id(provider_id: str, model_id: str) -> str:
    return f"{provider_id}::{model_id}"


def split_profile_id(profile_id: str) -> tuple[str, str]:
    provider_id, _, model_id = profile_id.partition("::")
    return provider_id, model_id


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


def find_prompt(config: dict[str, Any], prompt_id: str) -> dict[str, Any] | None:
    for prompt in config.get("prompt_library", []):
        if prompt["id"] == prompt_id:
            return prompt
    return None


def resolve_prompt(config: dict[str, Any], prompt_id: str) -> dict[str, Any]:
    prompt = find_prompt(config, prompt_id)
    if prompt is None:
        raise RuntimeError(f"Prompt '{prompt_id}' was not found.")
    return prompt


def find_behavior(config: dict[str, Any], behavior_id: str) -> dict[str, Any] | None:
    for behavior in config.get("behavior_library", []):
        if behavior["id"] == behavior_id:
            return behavior
    return None


def resolve_behavior(config: dict[str, Any], behavior_id: str) -> dict[str, Any]:
    behavior = find_behavior(config, behavior_id)
    if behavior is None:
        raise RuntimeError(f"Behavior '{behavior_id}' was not found.")
    return behavior


def set_engine(config: dict[str, Any], engine: str) -> None:
    config["translation"]["engine"] = normalize_engine(engine)


def set_active_profile(config: dict[str, Any], profile_id: str) -> None:
    provider_id, model_id = split_profile_id(profile_id)
    found = find_profile(config, provider_id, model_id)
    if found is None:
        raise RuntimeError(f"Profile '{profile_id}' was not found.")
    config["translation"]["active_provider_id"] = provider_id
    config["translation"]["active_model_id"] = model_id


def format_shortcut_label(shortcut: str) -> str:
    return "+".join(part.upper() for part in shortcut.split("+") if part)
