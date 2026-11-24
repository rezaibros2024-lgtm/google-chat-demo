"""Central settings. Everything is overridable with environment variables."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent

# Where the three databases + approval queue live (posts.db, leads.db, sales.db).
DATA_DIR = Path(os.getenv("MKT_DATA_DIR", Path.cwd() / "data"))

# Your business brain: voice, offer, audience, rules... edit these markdown files.
KNOWLEDGE_DIR = Path(os.getenv("MKT_KNOWLEDGE_DIR", PACKAGE_DIR / "knowledge"))

# Model used by every agent. Opus 5.5 by default; set MKT_MODEL to change it.
MODEL = os.getenv("MKT_MODEL", "claude-opus-5-5")

# Publishing: "dry-run" (default, logs only) or "webhook" (POST to Zapier/Make/n8n).
PUBLISHER = os.getenv("MKT_PUBLISHER", "dry-run")
WEBHOOK_URL = os.getenv("MKT_WEBHOOK_URL", "")

# Channels the Creative team writes for, in priority order.
CHANNELS = [
    c.strip()
    for c in os.getenv("MKT_CHANNELS", "instagram,tiktok,facebook,google").split(",")
    if c.strip()
]

# How many post ideas the daily run produces.
POSTS_PER_DAY = int(os.getenv("MKT_POSTS_PER_DAY", "2"))
