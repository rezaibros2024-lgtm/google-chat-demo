"""The Analytics Loop: reads all three databases and feeds learnings back to Research/Creative."""

from __future__ import annotations

from pydantic import BaseModel

from .. import db
from .base import Agent


class Analysis(BaseModel):
    what_worked: list[str]
    what_flopped: list[str]
    double_down_on: list[str]
    stop_doing: list[str]
    summary: str


class AnalyticsAgent(Agent):
    role = """
You are the Analytics Loop (Post Analyst, Revenue Tracker, Loop Feeder).
Find patterns that connect content to leads and revenue. Be concrete and blunt.
If there is too little data to conclude anything, say so.
"""

    def run(self) -> str:
        with db.connect("posts") as conn:
            posts = [dict(r) for r in conn.execute(
                """SELECT channel, format, hook, views, likes, comments, shares, published_at
                   FROM posts WHERE status='published' ORDER BY id DESC LIMIT 60""")]
        with db.connect("leads") as conn:
            leads = [dict(r) for r in conn.execute(
                "SELECT source, tier, status, created_at FROM leads ORDER BY id DESC LIMIT 200")]
        with db.connect("sales") as conn:
            sales = [dict(r) for r in conn.execute(
                "SELECT amount, currency, product, source, created_at FROM sales ORDER BY id DESC LIMIT 200")]
        a = self.llm.structured(
            self.system,
            f"Posts:\n{posts}\n\nLeads:\n{leads}\n\nSales:\n{sales}\n\n"
            "Analyse performance and tell the content team what to change next week.",
            Analysis,
            effort="high",
        )
        body = (
            f"{a.summary}\n\nDouble down on:\n" + "\n".join(f"- {x}" for x in a.double_down_on)
            + "\n\nStop doing:\n" + "\n".join(f"- {x}" for x in a.stop_doing)
        )
        with db.connect("posts") as conn:
            conn.execute("INSERT INTO learnings (created_at, body) VALUES (?, ?)", (db.now(), body))
        return body
