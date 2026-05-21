from __future__ import annotations

import sys
from collections.abc import Callable


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: FlipTextHelper.exe <settings|config|translate> [...]", file=sys.stderr)
        return 2

    command = sys.argv[1].strip().lower()
    args = sys.argv[2:]

    if command == "settings":
        if args:
            print("Usage: FlipTextHelper.exe settings", file=sys.stderr)
            return 2
        from settings_app import SettingsApp

        SettingsApp().run()
        return 0

    if command == "config":
        import config_cli

        return _run_module_main(config_cli.main, "config_cli.py", args)

    if command == "translate":
        import llm_translate

        return _run_module_main(llm_translate.main, "llm_translate.py", args)

    print(f"Unknown command: {command}", file=sys.stderr)
    return 2


def _run_module_main(main_func: Callable[[], int], program_name: str, args: list[str]) -> int:
    original_argv = sys.argv
    sys.argv = [program_name, *args]
    try:
        return main_func()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    raise SystemExit(main())
