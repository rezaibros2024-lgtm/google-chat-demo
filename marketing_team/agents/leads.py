"""Leads & Booking: lead catcher, lead scorer, follow-up drafts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import db
from .base import Agent


class LeadScore(BaseModel):
    score: int = Field(description="0-100 fit x intent")
    tier: Literal["hot", "warm", "cold", "not_a_fit"]
    reason: str
    next_action: str
    draft_email: str = Field(description="Personal follow-up email: subject line on first line, then body")


class LeadsAgent(Agent):
    role = """
You are Leads & Booking (Lead Catcher, Lead Scorer, Call Booker, Reminder).
Score each lead on fit (matches the ideal customer) and intent (urgency, budget, buying words).
Write short, personal follow-ups that reference what the lead actually said and push
toward the main call to action in the offer file.
"""

    @staticmethod
    def add(name: str, email: str = "", company: str = "", source: str = "", message: str = "") -> int:
        with db.connect("leads") as conn:
            cur = conn.execute(
                "INSERT INTO leads (created_at, name, email, company, source, message) VALUES (?,?,?,?,?,?)",
                (db.now(), name, email, company, source, message),
            )
            return cur.lastrowid

    def score_new(self) -> list[tuple[int, str, int]]:
        with db.connect("leads") as conn:
            rows = conn.execute("SELECT * FROM leads WHERE status = 'new' ORDER BY id").fetchall()
        out = []
        for row in rows:
            lead = {k: row[k] for k in ("name", "email", "company", "source", "message")}
            s = self.llm.structured(self.system, f"Score this lead:\n{lead}", LeadScore, effort="low")
            with db.connect("leads") as conn:
                conn.execute(
                    """UPDATE leads SET score=?, tier=?, reason=?, next_action=?, draft_email=?,
                       status='scored' WHERE id=?""",
                    (max(0, min(100, s.score)), s.tier, s.reason, s.next_action, s.draft_email, row["id"]),
                )
            out.append((row["id"], s.tier, s.score))
        return out
