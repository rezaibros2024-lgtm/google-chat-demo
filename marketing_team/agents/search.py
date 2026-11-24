"""Search & Website: SEO writer + repurposer (best social post -> blog article)."""

from __future__ import annotations

from pydantic import BaseModel

from .. import config, db
from .base import Agent


class Article(BaseModel):
    title: str
    slug: str
    meta_description: str
    target_keyword: str
    body_markdown: str


class SearchAgent(Agent):
    role = """
You are Search & Website (SEO Writer, Repurposer, Page Updater).
Write genuinely useful articles that answer the searcher's question fully,
with clear H2s, short paragraphs, and one CTA to the offer.
"""

    def repurpose_best_post(self) -> str:
        with db.connect("posts") as conn:
            post = conn.execute(
                """SELECT hook, body FROM posts WHERE status='published'
                   ORDER BY (likes + comments*3 + shares*5 + views/100) DESC LIMIT 1"""
            ).fetchone()
            brief = conn.execute("SELECT body FROM briefs ORDER BY id DESC LIMIT 1").fetchone()
        if not post and not brief:
            raise RuntimeError("nothing to repurpose yet - run research or publish a post first")
        source = f"{post['hook']}\n{post['body']}" if post else brief["body"]
        art = self.llm.structured(
            self.system,
            f"Turn this into an 800-1200 word SEO blog article:\n<source>\n{source}\n</source>",
            Article,
            effort="high",
        )
        out_dir = config.DATA_DIR / "drafts"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{art.slug or 'article'}.md"
        path.write_text(
            f"---\ntitle: {art.title}\ndescription: {art.meta_description}\n"
            f"keyword: {art.target_keyword}\n---\n\n{art.body_markdown}\n",
            encoding="utf-8",
        )
        return str(path)
