"""Email & Nurture: weekly newsletter built from this week's best content."""

from __future__ import annotations

from pydantic import BaseModel

from .. import config, db
from .base import Agent


class Newsletter(BaseModel):
    subject_lines: list[str]
    preview_text: str
    body_markdown: str


class EmailAgent(Agent):
    role = """
You are Email & Nurture (Newsletter, Sequences, Lead Magnet, Segmenter, Win-Back).
Write emails that sound like one person writing to one reader. One idea, one CTA.
"""

    def weekly_newsletter(self) -> str:
        with db.connect("posts") as conn:
            posts = conn.execute(
                """SELECT channel, hook, body, views, likes, comments FROM posts
                   WHERE status='published' AND published_at >= datetime('now','-7 days')
                   ORDER BY (likes + comments*3 + shares*5) DESC LIMIT 5"""
            ).fetchall()
        source = "\n\n".join(f"[{p['channel']}] {p['hook']}\n{p['body']}" for p in posts) or "(no posts this week)"
        nl = self.llm.structured(
            self.system,
            f"Turn this week's best content into a newsletter. Give 3 subject lines.\n<content>\n{source}\n</content>",
            Newsletter,
        )
        out_dir = config.DATA_DIR / "drafts"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"newsletter-{db.now()[:10]}.md"
        path.write_text(
            "Subject options:\n" + "\n".join(f"- {s}" for s in nl.subject_lines)
            + f"\n\nPreview: {nl.preview_text}\n\n---\n\n{nl.body_markdown}\n",
            encoding="utf-8",
        )
        return str(path)
