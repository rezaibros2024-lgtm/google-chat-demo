"""End-to-end test of the daily/weekly loops with a fake LLM (no API calls, no cost)."""

from __future__ import annotations

import pytest

from marketing_team import cli, config, db
from marketing_team.agents.analytics import Analysis
from marketing_team.agents.creative import PostBatch, PostDraft
from marketing_team.agents.distribution import InboxTriage
from marketing_team.agents.email import Newsletter
from marketing_team.agents.leads import LeadScore
from marketing_team.agents.search import Article
from marketing_team.orchestrator import Orchestrator


class FakeLLM:
    def __init__(self):
        self.calls = []

    def research(self, system, prompt, effort="medium"):
        self.calls.append(("research", prompt))
        return "## Trends\n- AI receptionists are hot (https://example.com)"

    def structured(self, system, prompt, schema, effort="medium", max_tokens=16000):
        self.calls.append((schema.__name__, prompt))
        assert "<knowledge" in system  # every agent gets the knowledge base
        if schema is PostBatch:
            return PostBatch(posts=[
                PostDraft(channel="Instagram", format="short_video", hook=f"Hook {len(self.calls)}",
                          body="Body", cta="Order direct", visual_brief="cheese pull",
                          hashtags=["a", "b", "c", "d"]),
                PostDraft(channel="LinkedIn", format="text", hook="Should be dropped",
                          body="Body", cta="x", visual_brief="none", hashtags=[]),
            ])
        if schema is LeadScore:
            return LeadScore(score=150, tier="hot", reason="ready", next_action="call today",
                             draft_email="Subject: hi\n\nHello")
        if schema is InboxTriage:
            return InboxTriage(intent="wants_human", needs_human=True, reason="asked for a person",
                               draft_reply="I'll get Anwar to reply personally.")
        if schema is Analysis:
            return Analysis(what_worked=["x"], what_flopped=["y"], double_down_on=["stories"],
                            stop_doing=["listicles"], summary="Stories win.")
        if schema is Newsletter:
            return Newsletter(subject_lines=["s1", "s2", "s3"], preview_text="p", body_markdown="hi")
        if schema is Article:
            return Article(title="T", slug="t", meta_description="d", target_keyword="k",
                           body_markdown="body")
        raise AssertionError(schema)


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "CHANNELS", ["instagram"])
    db.init_all()
    yield tmp_path


def test_daily_loop_drafts_need_approval_before_publishing(tmp_data):
    orch = Orchestrator(llm=FakeLLM())
    orch.leads.add("Sam", "sam@example.com", message="Need this live next week")

    report = orch.daily()
    assert not report.errors
    assert db.count("posts", "briefs") == 1
    assert db.count("posts", "posts", "status='pending_approval'") == 1
    assert db.count("posts", "posts", "status='published'") == 0  # nothing goes out unapproved

    with db.connect("leads") as conn:
        lead = conn.execute("SELECT * FROM leads").fetchone()
    assert (lead["tier"], lead["score"], lead["status"]) == ("hot", 100, "scored")  # score clamped

    with db.connect("posts") as conn:
        post = conn.execute("SELECT * FROM posts").fetchone()
    assert post["channel"] == "instagram" and post["hashtags"] == "a b c"  # max 3 hashtags

    cli.main(["approve", str(post["id"])])
    orch.daily()
    assert db.count("posts", "posts", "status='published'") == 1
    assert list((tmp_data / "outbox").glob("post-*.md"))


def test_inbox_escalates_to_human():
    orch = Orchestrator(llm=FakeLLM())
    orch.distribution.triage("instagram", "@angry", "I want to talk to a real person")
    assert db.count("posts", "inbox", "needs_human=1 AND status='escalated'") == 1


def test_weekly_loop_feeds_learnings_back_into_research(tmp_data):
    llm = FakeLLM()
    orch = Orchestrator(llm=llm)
    orch.daily()
    report = orch.weekly()
    assert not report.errors, report.errors
    assert db.count("posts", "learnings") == 1
    assert (tmp_data / "drafts" / "t.md").exists()

    orch.research.daily_brief()
    last_research_prompt = [p for kind, p in llm.calls if kind == "research"][-1]
    assert "Stories win." in last_research_prompt


def test_one_team_failing_does_not_stop_the_others():
    class Broken(FakeLLM):
        def research(self, *a, **k):
            raise RuntimeError("network down")

    orch = Orchestrator(llm=Broken())
    orch.leads.add("Kim")
    report = orch.daily()
    assert any("research" in e for e in report.errors)
    assert db.count("leads", "leads", "status='scored'") == 1


def test_stripe_import_is_idempotent(tmp_path, capsys):
    f = tmp_path / "payments.csv"
    f.write_text("id,Created date (UTC),Amount,Currency,Status,Customer Email,Description\n"
                 "ch_1,2026-11-20,499,usd,Paid,a@b.com,Coaching\n"
                 "ch_2,2026-11-21,99,usd,Failed,c@d.com,Coaching\n")
    cli.main(["import-sales", str(f)])
    cli.main(["import-sales", str(f)])
    assert db.count("sales", "sales") == 1


def test_status_dashboard(capsys):
    cli.main(["status", "--today"])
    out = capsys.readouterr().out
    assert "waiting on you" in out and "leads.db" in out


def test_linkedin_is_never_used():
    assert "linkedin" not in [c.lower() for c in config.CHANNELS]
    orch = Orchestrator(llm=FakeLLM())
    orch.research.daily_brief()
    orch.creative.draft_from_brief()
    assert db.count("posts", "posts", "channel='linkedin'") == 0
