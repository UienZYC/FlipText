from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
from pathlib import Path
from typing import Any

import httpx
from openai import OpenAI

from config_store import DEFAULT_USER_PROMPT_TEMPLATE, ensure_config, resolve_profile, resolve_prompt_preset


def main() -> int:
    args = parse_args()
    try:
        script_dir = Path(__file__).resolve().parent
        config = ensure_config(script_dir)
        provider, model = resolve_profile(config, args.profile_id or None)
        text = Path(args.text_file).read_text(encoding="utf-8")
        preset = resolve_prompt_preset(config, args.preset_id) if args.preset_id else None
        translated = translate_text(provider, model, text, Path(args.log_file), preset)
        result = {
            "ok": True,
            "text": translated,
            "source": build_source_label(provider, model, preset),
        }
        write_result(Path(args.result_file), result)
        return 0
    except Exception as exc:
        log_exception(Path(args.log_file), "Python LLM translation failed.", exc)
        write_result(
            Path(args.result_file),
            {
                "ok": False,
                "error": str(exc),
                "text": "",
                "source": "",
            },
        )
        return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-id", default="")
    parser.add_argument("--preset-id", default="")
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--result-file", required=True)
    parser.add_argument("--log-file", required=True)
    return parser.parse_args()


def translate_text(
    provider: dict[str, Any], model: dict[str, Any], text: str, log_path: Path, preset: dict[str, Any] | None = None
) -> str:
    if not model.get("enabled", True):
        raise RuntimeError(f"Model '{model['name']}' is disabled.")
    if not provider.get("base_url", "").strip() or not provider.get("api_key", "").strip() or not model.get("name", "").strip():
        raise RuntimeError(f"Provider '{provider['name']}' is incomplete.")

    timeout_seconds = model["timeout_ms"] / 1000
    client = OpenAI(
        api_key=provider["api_key"],
        base_url=provider["base_url"],
        timeout=httpx.Timeout(
            timeout=timeout_seconds,
            connect=min(timeout_seconds, 10),
            read=timeout_seconds,
            write=min(timeout_seconds, 30),
        ),
        max_retries=0,
    )

    log_debug(
        log_path,
        "Python LLM request started. "
        f"provider={provider['name']} "
        f"model={model['name']} "
        f"timeout={timeout_seconds}s",
    )

    system_prompt, user_prompt, meta = compose_messages(model, text, preset)
    log_debug(log_path, meta)
    log_prompt_composition(log_path, system_prompt, user_prompt)

    response = client.chat.completions.create(
        model=model["name"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )

    translated = extract_content(response)
    if not translated.strip():
        raise RuntimeError("Python translator returned empty content.")

    log_debug(log_path, "Python LLM translation succeeded.")
    return translated


def build_source_label(provider: dict[str, Any], model: dict[str, Any], preset: dict[str, Any] | None) -> str:
    if preset is not None:
        return f"LLM Prompt: {preset['name']} ({provider['name']} / {model['name']})"
    return f"LLM: {provider['name']} / {model['name']}"


def detect_direction(text: str) -> tuple[str, str]:
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh", "en"
    return "en", "zh"


def compose_messages(model: dict[str, Any], text: str, preset: dict[str, Any] | None) -> tuple[str, str, str]:
    if preset is not None:
        system_prompt = str(preset.get("system_prompt", "")).strip()
        if not system_prompt:
            raise RuntimeError(f"Prompt preset '{preset['name']}' has an empty system prompt.")
        return system_prompt, text, f"Prompt preset selected. preset={preset['name']} shortcut={preset['shortcut']}"

    source_lang, target_lang = detect_direction(text)
    system_prompt = str(model.get("system_prompt", "")).strip()
    user_prompt = compose_user_prompt(model, text, source_lang, target_lang)
    return system_prompt, user_prompt, f"Translation direction detected. from={source_lang} to={target_lang}"


def extract_content(response: Any) -> str:
    content = response.choices[0].message.content
    if isinstance(content, str):
        return content

    parts: list[str] = []
    if isinstance(content, list):
        for part in content:
            text = getattr(part, "text", "")
            if text:
                parts.append(text)
    return "\n".join(parts)


def compose_user_prompt(model: dict[str, Any], text: str, source_lang: str, target_lang: str) -> str:
    template = str(model.get("user_prompt_template", DEFAULT_USER_PROMPT_TEMPLATE)).strip()
    if not template:
        template = DEFAULT_USER_PROMPT_TEMPLATE
    try:
        return template.format(source_lang=source_lang, target_lang=target_lang, text=text)
    except KeyError as exc:
        name = exc.args[0]
        raise RuntimeError(
            "User prompt template contains an unsupported placeholder: "
            f"{{{name}}}. Supported placeholders are {{source_lang}}, {{target_lang}}, and {{text}}."
        ) from exc


def log_prompt_composition(path: Path, system_prompt: str, user_prompt: str) -> None:
    log_debug(path, "Prompt composition:")
    log_multiline(path, "  [system] ", system_prompt)
    log_multiline(path, "  [user] ", user_prompt)


def write_result(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def log_debug(path: Path, message: str) -> None:
    timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{timestamp} {message}\n")


def log_multiline(path: Path, prefix: str, text: str) -> None:
    lines = text.splitlines() or [""]
    for index, line in enumerate(lines, start=1):
        log_debug(path, f"{prefix}{index:02d}: {line}")


def log_exception(path: Path, message: str, exc: BaseException) -> None:
    details = format_exception_details(exc)
    log_debug(path, f"{message} {exc}")
    for line in details.splitlines():
        log_debug(path, f"  {line}")


def format_exception_details(exc: BaseException) -> str:
    parts = traceback.format_exception(type(exc), exc, exc.__traceback__)
    cause = exc.__cause__
    context = exc.__context__ if exc.__cause__ is None else None

    while cause is not None:
        parts.append("\nCaused by:\n")
        parts.extend(traceback.format_exception(type(cause), cause, cause.__traceback__))
        cause = cause.__cause__

    while context is not None:
        parts.append("\nDuring handling of the above exception, another exception occurred:\n")
        parts.extend(traceback.format_exception(type(context), context, context.__traceback__))
        context = context.__context__

    return "".join(parts).rstrip()


if __name__ == "__main__":
    sys.exit(main())
