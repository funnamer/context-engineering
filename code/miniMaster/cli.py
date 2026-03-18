from __future__ import annotations

import argparse
from pathlib import Path

from app import build_app
from config import AppConfig


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", type=str, help="Run once and exit.")
    parser.add_argument("--project-dir", type=str, help="Override project dir.")
    parser.add_argument("--api-base", type=str, help="Override API base.")
    parser.add_argument("--api-key", type=str, help="Override API key.")
    parser.add_argument("--model", type=str, help="Override model name.")
    args = parser.parse_args()

    config = AppConfig.from_env()

    if args.project_dir:
        config.project_dir = Path(args.project_dir).expanduser().resolve()
    if args.api_base:
        config.api_base = args.api_base
    if args.api_key is not None:
        config.api_key = args.api_key
    if args.model:
        config.model_name = args.model

    app = build_app(config)

    print("mini-claude-code")
    print("loaded_skills:", ", ".join(app.loaded_skills) if app.loaded_skills else "(none)")
    if app.warnings:
        print("warnings:")
        for w in app.warnings:
            print(" -", w)

    if args.once:
        print(app.loop.run_turn(args.once))
        return

    print("Type exit to quit.")
    print("Use /skill-name to explicitly activate a skill.")
    while True:
        try:
            text = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            break

        try:
            result = app.loop.run_turn(text)
            print(result)
        except Exception as exc:  # noqa: BLE001
            print("[error]", exc)


if __name__ == "__main__":
    main()