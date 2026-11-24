"""Distribution & Community: publishes approved posts, triages comments/DMs, escalates."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from .. import db
from ..publishers import get_publisher
from .base import Agent


class InboxTriage(BaseModel):
    intent: Literal["question", "buying_signal", "praise", "complaint", "spam", "wants_human", "other"]
    needs_human: bool
    reason: str
    draft_reply: str


class DistributionAgent(Agent):
    role = """
You are Distribution & Community (Scheduler, Poster, Comment & DM Agent, Escalation).
You reply to comments and DMs in the owner's voice. You escalate to the human when:
someone asks for a person, is angry or complaining, mentions refunds/legal/press,
shows strong buying intent, or when you are not sure.
"""

    def publish_approved(self) -> list[tuple[int, str]]:
        publisher = get_publisher()
        results = []
        with db.connect("posts") as conn:
            rows = conn.execute("SELECT * FROM posts WHERE status = 'approved' ORDER BY id").fetchall()
            for row in rows:
                external_id = publisher.publish(dict(row))
                conn.execute(
                    "UPDATE posts SET status='published', published_at=?, external_id=? WHERE id=?",
                    (db.now(), external_id, row["id"]),
                )
                results.append((row["id"], external_id))
        return results

    def triage(self, channel: str, author: str, text: str) -> int:
        result = self.llm.structured(
            self.system,
            f"New {channel} message from {author}:\n<message>\n{text}\n</message>\n"
            "Classify it and draft a reply (empty reply for spam).",
            InboxTriage,
            effort="low",
        )
        with db.connect("posts") as conn:
            cur = conn.execute(
                """INSERT INTO inbox (created_at, channel, author, text, intent, draft_reply,
                   needs_human, status) VALUES (?,?,?,?,?,?,?,?)""",
                (db.now(), channel, author, text, result.intent, result.draft_reply,
                 int(result.needs_human), "escalated" if result.needs_human else "drafted"),
            )
            return cur.lastrowid
