from __future__ import annotations

import argparse
import configparser
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx
from openai import OpenAI


DEFAULT_SYSTEM_PROMPT = (
    "You are a professional translator. Translate the user's text accurately and naturally. "
    "Return only the translated text. Preserve line breaks, formatting, and tone. "
    "Do not add explanations, quotation marks, notes, or extra text."
)


def main() -> int:
    args = parse_args()
    try:
        config = load_config(Path(args.config), args.profile)
        text = Path(args.text_file).read_text(encoding="utf-8")
        translated = translate_text(config, text, Path(args.log_file))
        result = {
            "ok": True,
            "text": translated,
            "source": f"LLM: {config['profile_name']}",
        }
        write_result(Path(args.result_file), result)
        return 0
    except Exception as exc:
        log_debug(Path(args.log_file), f"Python LLM translation failed. {exc}")
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
    parser.add_argument("--config", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--result-file", required=True)
    parser.add_argument("--log-file", required=True)
    return parser.parse_args()


def load_config(config_path: Path, requested_profile: str) -> dict[str, Any]:
    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")

    profile_name = normalize_profile_name(
        requested_profile
        or parser.get("General", "active_profile", fallback="default")
    )
    section_name = f"LLM.{profile_name}"
    legacy_section = "LLM"

    def read_option(name: str, default: str = "") -> str:
        if parser.has_option(section_name, name):
            return parser.get(section_name, name)
        if parser.has_option(legacy_section, name):
            return parser.get(legacy_section, name)
        return default

    enabled = normalize_bool(read_option("enabled", "false"))
    base_url = read_option("base_url", "").strip()
    api_key = read_option("api_key", "").strip()
    model = read_option("model", "").strip()
    timeout_ms = normalize_timeout(read_option("timeout_ms", "30000"))
    system_prompt = read_option("system_prompt", DEFAULT_SYSTEM_PROMPT).strip() or DEFAULT_SYSTEM_PROMPT

    if not enabled:
        raise RuntimeError(f"LLM profile '{profile_name}' is disabled.")
    if not base_url or not api_key or not model:
        raise RuntimeError(f"LLM profile '{profile_name}' is incomplete.")

    return {
        "profile_name": profile_name,
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "timeout_seconds": timeout_ms / 1000,
        "connect_timeout_seconds": min(timeout_ms / 1000, 10),
        "read_timeout_seconds": timeout_ms / 1000,
        "system_prompt": system_prompt,
    }


def translate_text(config: dict[str, Any], text: str, log_path: Path) -> str:
    source_lang, target_lang = detect_direction(text)
    client = OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout=httpx.Timeout(
            timeout=config["timeout_seconds"],
            connect=config["connect_timeout_seconds"],
            read=config["read_timeout_seconds"],
            write=min(config["timeout_seconds"], 30),
        ),
        max_retries=0,
    )

    log_debug(
        log_path,
        "Python LLM request started. "
        f"profile={config['profile_name']} "
        f"model={config['model']} "
        f"from={source_lang} to={target_lang} "
        f"timeout={config['timeout_seconds']}s",
    )

    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": config["system_prompt"]},
            {
                "role": "user",
                "content": f"Translate the following text from {source_lang} to {target_lang}.\n\n{text}",
            },
        ],
        temperature=0,
    )

    translated = extract_content(response)
    if not translated.strip():
        raise RuntimeError("Python translator returned empty content.")

    log_debug(log_path, "Python LLM translation succeeded.")
    return translated


def detect_direction(text: str) -> tuple[str, str]:
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh", "en"
    return "en", "zh"


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


def normalize_profile_name(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[\[\]\r\n]", "", value)
    return value or "default"


def normalize_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def normalize_timeout(value: str) -> int:
    value = value.strip()
    if not value.isdigit():
        return 30000
    timeout = int(value)
    return timeout if timeout >= 1000 else 30000


def write_result(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def log_debug(path: Path, message: str) -> None:
    timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{timestamp} {message}\n")


if __name__ == "__main__":
    sys.exit(main())
