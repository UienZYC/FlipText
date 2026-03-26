from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx
from openai import OpenAI

from config_store import ensure_config, resolve_profile


def main() -> int:
    args = parse_args()
    try:
        script_dir = Path(__file__).resolve().parent
        config = ensure_config(script_dir)
        provider, model = resolve_profile(config, args.profile_id or None)
        text = Path(args.text_file).read_text(encoding="utf-8")
        translated = translate_text(provider, model, text, Path(args.log_file))
        result = {
            "ok": True,
            "text": translated,
            "source": f"LLM: {provider['name']} / {model['name']}",
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
    parser.add_argument("--profile-id", default="")
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--result-file", required=True)
    parser.add_argument("--log-file", required=True)
    return parser.parse_args()


def translate_text(provider: dict[str, Any], model: dict[str, Any], text: str, log_path: Path) -> str:
    if not model.get("enabled", True):
        raise RuntimeError(f"Model '{model['name']}' is disabled.")
    if not provider.get("base_url", "").strip() or not provider.get("api_key", "").strip() or not model.get("name", "").strip():
        raise RuntimeError(f"Provider '{provider['name']}' is incomplete.")

    timeout_seconds = model["timeout_ms"] / 1000
    source_lang, target_lang = detect_direction(text)
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
        f"from={source_lang} to={target_lang} "
        f"timeout={timeout_seconds}s",
    )

    response = client.chat.completions.create(
        model=model["name"],
        messages=[
            {"role": "system", "content": model["system_prompt"]},
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


def write_result(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def log_debug(path: Path, message: str) -> None:
    timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{timestamp} {message}\n")


if __name__ == "__main__":
    sys.exit(main())
