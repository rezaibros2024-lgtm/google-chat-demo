"""Where approved posts go.

dry-run  - writes the post to data/outbox/ so you can copy-paste or upload it yourself.
webhook  - POSTs the post as JSON to MKT_WEBHOOK_URL. Point that at a Zapier / Make / n8n
           scenario (or Buffer / Metricool via those tools) that fans out to TikTok,
           Instagram, YouTube and LinkedIn. This avoids waiting months for each
           platform's own API approval.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Protocol

from .. import config


class Publisher(Protocol):
    def publish(self, post: dict) -> str: ...


class DryRunPublisher:
    def publish(self, post: dict) -> str:
        out = config.DATA_DIR / "outbox"
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"post-{post['id']}-{post['channel']}.md"
        path.write_text(
            f"# {post['channel']} ({post['format']})\n\n{post['hook']}\n\n{post['body']}\n\n"
            f"{post['cta']}\n\n{post['hashtags']}\n\n---\nVisual brief: {post['visual_brief']}\n",
            encoding="utf-8",
        )
        return f"outbox:{path.name}"


class WebhookPublisher:
    def __init__(self, url: str):
        if not url.startswith("https://"):
            raise ValueError("MKT_WEBHOOK_URL must be an https:// URL")
        self.url = url

    def publish(self, post: dict) -> str:
        payload = {k: post[k] for k in ("id", "channel", "format", "hook", "body", "cta",
                                        "hashtags", "visual_brief")}
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode(), method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status >= 300:
                raise RuntimeError(f"webhook returned {resp.status}")
        return f"webhook:{post['id']}"


def get_publisher() -> Publisher:
    if config.PUBLISHER == "webhook":
        return WebhookPublisher(config.WEBHOOK_URL)
    return DryRunPublisher()
