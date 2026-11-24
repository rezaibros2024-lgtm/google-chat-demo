"""Loads the knowledge base: the markdown files every agent reads before working."""

from __future__ import annotations

from . import config

ORDER = ["offer", "audience", "voice", "channels", "rules", "compliance"]


def load() -> str:
    parts = []
    files = sorted(config.KNOWLEDGE_DIR.glob("*.md"), key=lambda p: (
        ORDER.index(p.stem) if p.stem in ORDER else len(ORDER), p.stem))
    for path in files:
        text = path.read_text(encoding="utf-8").strip()
        if text:
            parts.append(f'<knowledge file="{path.name}">\n{text}\n</knowledge>')
    return "\n\n".join(parts)


def unfilled() -> list[str]:
    """Knowledge files still containing the TODO placeholder."""
    return [p.name for p in sorted(config.KNOWLEDGE_DIR.glob("*.md"))
            if "TODO" in p.read_text(encoding="utf-8")]
