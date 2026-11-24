"""Research & Content team: trend spotting, audience research, keyword finding."""

from __future__ import annotations

from .. import db
from .base import Agent


class ResearchAgent(Agent):
    role = """
You are the Research lead (Trend Spotter, Audience Researcher, Keyword Finder).
Use web search to find what the target audience is talking about right now.
Cite the sources you used as plain URLs.
"""

    def daily_brief(self, focus: str = "") -> int:
        recent = self._recent_learnings()
        prompt = f"""Write today's content research brief.

{f'Focus requested by the owner: {focus}' if focus else ''}
{f'What our analytics say has worked recently:{chr(10)}{recent}' if recent else ''}

Search the web for the last 7-14 days of conversation relevant to our audience and offer.
Return markdown with these sections:
## Trends (3-5 bullets, each with why it matters to OUR audience and a source URL)
## Questions people are asking (5 bullets, in the audience's own words)
## Keywords / search phrases (5-10)
## 3 post angles we should make today (one line each)
Keep it under 500 words."""
        body = self.llm.research(self.system, prompt)
        with db.connect("posts") as conn:
            cur = conn.execute(
                "INSERT INTO briefs (created_at, topic, body) VALUES (?, ?, ?)",
                (db.now(), focus or "daily", body),
            )
            return cur.lastrowid

    @staticmethod
    def _recent_learnings() -> str:
        with db.connect("posts") as conn:
            row = conn.execute("SELECT body FROM learnings ORDER BY id DESC LIMIT 1").fetchone()
        return row["body"] if row else ""
