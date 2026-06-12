from __future__ import annotations

from textwrap import wrap


def wrap_labeled_line(timestamp: str, label: str, text: str, width: int = 58) -> list[str]:
    cleaned = " ".join(text.split())
    prefix = f"{timestamp}: {label}: "
    wrapped = wrap(cleaned, width=max(12, width - len(prefix))) or [""]
    lines = [f"{prefix}{wrapped[0]}"]
    lines.extend(f"{' ' * len(prefix)}{line}" for line in wrapped[1:])
    return lines
