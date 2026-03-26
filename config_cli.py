from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Any

from config_store import (
    ensure_config,
    iter_behaviors,
    iter_bindings,
    iter_profiles,
    iter_prompts,
    resolve_profile,
    save_config,
    set_active_profile,
    set_engine,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary_parser = subparsers.add_parser("summary")
    summary_parser.add_argument("--result-file")

    set_engine_parser = subparsers.add_parser("set-engine")
    set_engine_parser.add_argument("--engine", required=True)

    set_profile_parser = subparsers.add_parser("set-active-profile")
    set_profile_parser.add_argument("--profile-id", required=True)

    args = parser.parse_args()

    try:
        config = ensure_config(Path(__file__).resolve().parent)

        if args.command == "summary":
            text = encode_summary(build_summary(config))
            if args.result_file:
                Path(args.result_file).write_text(text, encoding="utf-8")
            else:
                print(text)
            return 0

        if args.command == "set-engine":
            set_engine(config, args.engine)
            save_config(config)
            return 0

        if args.command == "set-active-profile":
            set_active_profile(config, args.profile_id)
            save_config(config)
            return 0

        return 1
    except Exception as exc:
        if getattr(args, "result_file", None):
            result_path = Path(args.result_file)
            error_log_path = result_path.with_suffix(result_path.suffix + ".error.log")
            error_log_path.write_text(traceback.format_exc(), encoding="utf-8")
            result_path.write_text(
                "ok=0\n"
                f"error={escape_value(str(exc))}\n"
                f"error_file={escape_value(str(error_log_path))}\n",
                encoding="utf-8",
            )
        else:
            traceback.print_exc(file=sys.stderr)
        return 1


def build_summary(config: dict[str, Any]) -> dict[str, Any]:
    profiles = iter_profiles(config)
    active_profile_id = ""
    active_profile_label = ""
    active_timeout_ms = 30000
    if profiles:
        try:
            active_provider, active_model = resolve_profile(config)
            active_profile_id = f"{active_provider['id']}::{active_model['id']}"
            active_profile_label = f"{active_provider['name']} / {active_model['name']}"
            active_timeout_ms = active_model["timeout_ms"]
        except RuntimeError:
            pass

    return {
        "engine": config["translation"]["engine"],
        "active_profile_id": active_profile_id,
        "active_profile_label": active_profile_label,
        "active_timeout_ms": active_timeout_ms,
        "profiles": profiles,
        "prompts": iter_prompts(config),
        "behaviors": iter_behaviors(config),
        "bindings": iter_bindings(config),
    }


def encode_summary(summary: dict[str, Any]) -> str:
    lines = [
        "ok=1",
        f"engine={escape_value(summary['engine'])}",
        f"active_profile_id={escape_value(summary['active_profile_id'])}",
        f"active_profile_label={escape_value(summary['active_profile_label'])}",
        f"active_timeout_ms={summary['active_timeout_ms']}",
    ]

    for profile in summary["profiles"]:
        lines.append(
            "profile=" + "|".join(
                [
                    escape_value(profile["id"]),
                    escape_value(profile["label"]),
                    "1" if profile["enabled"] else "0",
                    str(profile["timeout_ms"]),
                ]
            )
        )

    for prompt in summary["prompts"]:
        lines.append(
            "prompt=" + "|".join(
                [
                    escape_value(prompt["id"]),
                    escape_value(prompt["name"]),
                ]
            )
        )

    for behavior in summary["behaviors"]:
        lines.append(
            "behavior=" + "|".join(
                [
                    escape_value(behavior["id"]),
                    escape_value(behavior["name"]),
                    escape_value(behavior["type"]),
                    escape_value(behavior["profile_id"]),
                    escape_value(behavior["prompt_id"]),
                    escape_value(behavior["label"]),
                ]
            )
        )

    for binding in summary["bindings"]:
        lines.append(
            "binding=" + "|".join(
                [
                    escape_value(binding["id"]),
                    escape_value(binding["shortcut"]),
                    escape_value(binding["behavior_id"]),
                    escape_value(binding["behavior_name"]),
                    escape_value(binding["behavior_type"]),
                    escape_value(binding["behavior_label"]),
                ]
            )
        )

    return "\n".join(lines) + "\n"


def escape_value(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "")
        .replace("|", "\\p")
        .replace("=", "\\e")
    )


if __name__ == "__main__":
    sys.exit(main())
