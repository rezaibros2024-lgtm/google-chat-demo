"""The Orchestrator ("Claude Code, the head"): decides which teams run, in what order.

daily : research -> creative drafts (to approval desk) -> score leads -> publish what you approved
weekly: analytics loop -> newsletter draft -> SEO article from the best post
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import agents
from .llm import LLM


@dataclass
class RunReport:
    steps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def ok(self, msg: str) -> None:
        self.steps.append(msg)
        print(f"  ✓ {msg}")

    def fail(self, step: str, exc: Exception) -> None:
        self.errors.append(f"{step}: {exc}")
        print(f"  ✗ {step}: {exc}")


class Orchestrator:
    def __init__(self, llm: LLM | None = None):
        self.llm = llm or LLM()
        self.research = agents.ResearchAgent(self.llm)
        self.creative = agents.CreativeAgent(self.llm)
        self.distribution = agents.DistributionAgent(self.llm)
        self.leads = agents.LeadsAgent(self.llm)
        self.email = agents.EmailAgent(self.llm)
        self.search = agents.SearchAgent(self.llm)
        self.analytics = agents.AnalyticsAgent(self.llm)

    def daily(self, focus: str = "") -> RunReport:
        r = RunReport()
        # Publish yesterday's approvals first so a failure later can't block them.
        self._step(r, "publish approved", lambda: f"published {len(self.distribution.publish_approved())} post(s)")
        brief_ok = self._step(r, "research", lambda: f"research brief #{self.research.daily_brief(focus)}")
        if brief_ok:
            self._step(r, "creative", lambda: f"{len(self.creative.draft_from_brief())} draft(s) waiting for your approval")
        self._step(r, "leads", lambda: f"scored {len(self.leads.score_new())} new lead(s)")
        return r

    def weekly(self) -> RunReport:
        r = RunReport()
        self._step(r, "analytics", lambda: "learnings saved for next week's content" if self.analytics.run() else "")
        self._step(r, "newsletter", lambda: f"newsletter draft: {self.email.weekly_newsletter()}")
        self._step(r, "seo", lambda: f"SEO article draft: {self.search.repurpose_best_post()}")
        return r

    @staticmethod
    def _step(report: RunReport, name: str, fn) -> bool:
        try:
            report.ok(fn())
            return True
        except Exception as exc:  # one team failing must not stop the others
            report.fail(name, exc)
            return False
