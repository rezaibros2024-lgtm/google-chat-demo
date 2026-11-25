"""Reviews: drafts replies to Google reviews. Unhappy reviews are flagged for the owner."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .. import db
from .base import Agent


class ReviewReply(BaseModel):
    reply: str = Field(description="Public reply, 2-4 sentences, signed '— the Juniors team'")
    needs_owner: bool = Field(description="True for 1-3 stars, food safety, allergies, refunds, or anything serious")
    reason: str


class ReviewsAgent(Agent):
    role = """
You are the Reviews agent. You draft public replies to Google reviews in the owner's voice.
Thank people by first name and mention what they ordered when they say it. Never argue,
never blame the customer, never offer refunds or free food in public, and never reveal
private details. For unhappy reviews: apologise briefly and invite them to call the shop
so the owner can make it right.
"""

    def draft(self, author: str, stars: int, text: str) -> int:
        stars = max(1, min(5, stars))
        r = self.llm.structured(
            self.system,
            f"Google review from {author}, {stars}★:\n<review>\n{text or '(no text)'}\n</review>",
            ReviewReply,
            effort="low",
        )
        needs_owner = r.needs_owner or stars <= 3
        with db.connect("posts") as conn:
            cur = conn.execute(
                """INSERT INTO inbox (created_at, channel, author, text, intent, draft_reply,
                   needs_human, status) VALUES (?,?,?,?,?,?,?,?)""",
                (db.now(), "google_review", author, f"{stars}★ {text}", "review", r.reply,
                 int(needs_owner), "escalated" if needs_owner else "drafted"),
            )
            return cur.lastrowid
