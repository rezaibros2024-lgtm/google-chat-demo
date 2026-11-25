"""Quiet-night offers: SMS/WhatsApp messages to opted-in customers to fill slow nights."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .. import config, db
from .base import Agent

OPT_OUT = "Reply STOP to opt out"


class OfferMessage(BaseModel):
    night: str
    deal_name: str = Field(description="An existing deal from the offer file, unchanged")
    sms: str = Field(description="Under 160 characters including the opt-out line")
    whatsapp: str = Field(description="Slightly longer friendly version, may use 1-2 emojis")


class OfferPlan(BaseModel):
    messages: list[OfferMessage]


class OffersAgent(Agent):
    role = """
You are the Offers agent. You write short SMS and WhatsApp messages that fill the shop's
quiet nights. Use ONLY deals and prices that already exist in the offer file - never invent
a discount. Each message names the shop, the night, one deal, and how to order
(juniorspizzakebab.com.au or call). Every message ends with the opt-out line you are given.
"""

    def plan_week(self) -> list[int]:
        nights = ", ".join(config.QUIET_NIGHTS)
        plan = self.llm.structured(
            self.system,
            f"Write one message for each quiet night: {nights}. "
            f"Use a different deal each night. End every message with: '{OPT_OUT}'.",
            OfferPlan,
        )
        ids = []
        with db.connect("posts") as conn:
            for m in plan.messages:
                sms = m.sms if OPT_OUT in m.sms else f"{m.sms.rstrip()} {OPT_OUT}"
                wa = m.whatsapp if OPT_OUT in m.whatsapp else f"{m.whatsapp.rstrip()}\n{OPT_OUT}"
                cur = conn.execute(
                    """INSERT INTO posts (created_at, channel, format, hook, body, cta, status)
                       VALUES (?,?,?,?,?,?, 'pending_approval')""",
                    (db.now(), "sms", "text", f"{m.night}: {m.deal_name}", sms, wa),
                )
                ids.append(cur.lastrowid)
        return ids
