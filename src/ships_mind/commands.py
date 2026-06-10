from __future__ import annotations


def is_clear_command(value: str) -> bool:
    return value.strip().lower() in {"clear", "/clear"}
