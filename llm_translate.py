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

from config_store import ensure_config, resolve_profile, resolve_prompt


def main() -> int:
    args = parse_args()
    try:
        config = ensure_config(Path(__file__).resolve().parent)
        provider, model = resolve_profile(config, args.profile_id or None)
        prompt = resolve_prompt(config, args.prompt_id)
        text = Path(args.text_file).read_text(encoding="utf-8")
        output = run_prompt(provider, model, prompt, text, Path(args.log_file))
        write_result(
            Path(args.result_file),
            {
                "ok": True,
                "text": output,
                "source": f"LLM: {provider['name']} / {model['name']} + {prompt['name']}",
            },
        )
        return 0
    except Exception as exc:
        log_exception(Path(args.log_file), "Python LLM behavior failed.", exc)
        write_result(Path(args.result_file), {"ok": False, "error": str(exc), "text": "", "source": ""})
        return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--prompt-id", required=True)
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--result-file", required=True)
    parser.add_argument("--log-file", required=True)
    return parser.parse_args()


def run_prompt(provider: dict[str, Any], model: dict[str, Any], prompt: dict[str, Any], text: str, log_path: Path) -> str:
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

    source_lang, target_lang = detect_direction(text)
    system_prompt = str(prompt.get("system_prompt", "")).strip()
    if not system_prompt:
        raise RuntimeError(f"Prompt '{prompt['name']}' has an empty system prompt.")
    user_prompt = compose_user_prompt(prompt, text, source_lang, target_lang)

    log_debug(
        log_path,
        "Python LLM behavior started. "
        f"provider={provider['name']} "
        f"model={model['name']} "
        f"prompt={prompt['name']} "
        f"from={source_lang} to={target_lang} "
        f"timeout={timeout_seconds}s",
    )
    log_prompt_composition(log_path, system_prompt, user_prompt)

    response = client.chat.completions.create(
        model=model["name"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )

    content = extract_content(response)
    if not content.strip():
        raise RuntimeError("Python LLM behavior returned empty content.")

    log_debug(log_path, "Python LLM behavior succeeded.")
    return content


def detect_direction(text: str) -> tuple[str, str]:
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh", "en"
    return "en", "zh"


def compose_user_prompt(prompt: dict[str, Any], text: str, source_lang: str, target_lang: str) -> str:
    template = str(prompt.get("user_prompt", "")).strip() or "{text}"
    try:
        return template.format(source_lang=source_lang, target_lang=target_lang, text=text)
    except KeyError as exc:
        name = exc.args[0]
        raise RuntimeError(
            "User prompt contains an unsupported placeholder: "
            f"{{{name}}}. Supported placeholders are {{source_lang}}, {{target_lang}}, and {{text}}."
        ) from exc


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


def log_prompt_composition(path: Path, system_prompt: str, user_prompt: str) -> None:
    log_debug(path, "Prompt composition:")
    log_multiline(path, "  [system] ", system_prompt)
    log_multiline(path, "  [user] ", user_prompt)


def log_multiline(path: Path, prefix: str, text: str) -> None:
    for index, line in enumerate(text.splitlines() or [""], start=1):
        log_debug(path, f"{prefix}{index:02d}: {line}")


def log_exception(path: Path, message: str, exc: BaseException) -> None:
    details = traceback.format_exception(type(exc), exc, exc.__traceback__)
    log_debug(path, f"{message} {exc}")
    for line in "".join(details).splitlines():
        log_debug(path, f"  {line}")


if __name__ == "__main__":
    sys.exit(main())
