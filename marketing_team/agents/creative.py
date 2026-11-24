"""Creative Studio: post writer, video scripts, graphic briefs. Output goes to the approval desk."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import config, db
from .base import Agent


class PostDraft(BaseModel):
    channel: str = Field(description="One of the requested channels")
    format: Literal["text", "carousel", "short_video", "long_video", "image"]
    hook: str = Field(description="First line / first 3 seconds. Must stop the scroll.")
    body: str = Field(description="Full caption or full video script with [VISUAL] cues")
    cta: str
    visual_brief: str = Field(description="Instructions for Canva / video tool: layout, b-roll, on-screen text")
    hashtags: list[str]


class PostBatch(BaseModel):
    posts: list[PostDraft]


class CreativeAgent(Agent):
    role = """
You are the Creative Studio (Post Writer, Video Maker, Graphic Designer, Editor).
You turn research into ready-to-publish posts written natively for each platform.
"""

    def draft_from_brief(self, brief_id: int | None = None, count: int | None = None) -> list[int]:
        count = count or config.POSTS_PER_DAY
        with db.connect("posts") as conn:
            row = conn.execute(
                "SELECT id, body FROM briefs WHERE id = ?" if brief_id else
                "SELECT id, body FROM briefs ORDER BY id DESC LIMIT 1",
                (brief_id,) if brief_id else (),
            ).fetchone()
            recent_hooks = [r["hook"] for r in conn.execute(
                "SELECT hook FROM posts ORDER BY id DESC LIMIT 20")]
        if not row:
            raise RuntimeError("no research brief yet - run `marketing research` first")

        prompt = f"""Research brief:
<brief>
{row['body']}
</brief>

Write {count} post(s) per channel for these channels: {', '.join(config.CHANNELS)}.
Use a different angle for each post. Match each platform's native format
(TikTok/Reels: script under 45s with [VISUAL] cues; LinkedIn: text post with line breaks;
YouTube: title + outline script; Instagram: carousel slide-by-slide or reel script).
Do not reuse these recent hooks:
{chr(10).join('- ' + h for h in recent_hooks) or '- (none yet)'}"""
        batch = self.llm.structured(self.system, prompt, PostBatch, effort="high")
        ids = []
        with db.connect("posts") as conn:
            for p in batch.posts:
                cur = conn.execute(
                    """INSERT INTO posts (created_at, channel, format, hook, body, cta,
                       visual_brief, hashtags, status) VALUES (?,?,?,?,?,?,?,?, 'pending_approval')""",
                    (db.now(), p.channel.lower(), p.format, p.hook, p.body, p.cta,
                     p.visual_brief, " ".join(p.hashtags[:3])),
                )
                ids.append(cur.lastrowid)
        return ids
