"""`marketing` command line: the one place you, the one person, touch the system."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime

from . import config, db, knowledge


def _orch():
    from .orchestrator import Orchestrator
    return Orchestrator()


# ---------- setup ----------

def cmd_init(_):
    for p in db.init_all():
        print(f"created {p}")
    todo = knowledge.unfilled()
    if todo:
        print(f"\nNext: fill in these knowledge files in {config.KNOWLEDGE_DIR}:")
        for name in todo:
            print(f"  - {name}")


# ---------- runs ----------

def cmd_run(args):
    todo = knowledge.unfilled()
    if todo and not args.force:
        sys.exit(f"Fill in your knowledge files first ({', '.join(todo)}) or pass --force.")
    print(f"Running {args.mode} loop...")
    orch = _orch()
    report = orch.daily(args.focus) if args.mode == "daily" else orch.weekly()
    sys.exit(1 if report.errors and not report.steps else 0)


def cmd_research(args):
    print(f"brief #{_orch().research.daily_brief(args.focus)} saved")


def cmd_create(args):
    ids = _orch().creative.draft_from_brief(count=args.count)
    print(f"{len(ids)} draft(s) waiting: run `marketing review`")


# ---------- approval desk ----------

def cmd_review(_):
    with db.connect("posts") as conn:
        rows = conn.execute("SELECT * FROM posts WHERE status='pending_approval' ORDER BY id").fetchall()
    if not rows:
        print("Nothing waiting on you.")
    for r in rows:
        print(f"\n━━ #{r['id']}  {r['channel'].upper()} · {r['format']} ━━")
        print(f"HOOK: {r['hook']}\n\n{r['body']}\n\nCTA: {r['cta']}   {r['hashtags']}")
        print(f"VISUAL: {r['visual_brief']}")
    if rows:
        print("\nApprove: marketing approve <id> [<id>...]   Reject: marketing reject <id> --note '...'")


def _set_status(ids, status, note=""):
    with db.connect("posts") as conn:
        for i in ids:
            n = conn.execute(
                "UPDATE posts SET status=?, review_notes=? WHERE id=? AND status='pending_approval'",
                (status, note, i)).rowcount
            print(f"#{i}: {status}" if n else f"#{i}: not pending, skipped")


def cmd_approve(args):
    _set_status(args.ids, "approved")
    print("Approved posts go out on the next `marketing publish` or daily run.")


def cmd_reject(args):
    _set_status(args.ids, "rejected", args.note)


def cmd_publish(_):
    for pid, ext in _orch().distribution.publish_approved():
        print(f"#{pid} -> {ext}")


# ---------- inbox, leads, sales ----------

def cmd_inbox(args):
    if args.text:
        iid = _orch().distribution.triage(args.channel, args.author, args.text)
        print(f"inbox #{iid} triaged")
    with db.connect("posts") as conn:
        rows = conn.execute(
            "SELECT * FROM inbox WHERE status IN ('escalated','drafted') ORDER BY needs_human DESC, id").fetchall()
    for r in rows:
        flag = "🔴 NEEDS YOU" if r["needs_human"] else "🟢 draft ready"
        print(f"\n#{r['id']} {flag} [{r['channel']}] {r['author']} ({r['intent']}): {r['text']}")
        if r["draft_reply"]:
            print(f"   ↳ {r['draft_reply']}")


def cmd_google_review(args):
    iid = _orch().reviews.draft(args.author, args.stars, args.text)
    print(f"review reply #{iid} drafted - see `marketing inbox`")


def cmd_offers(_):
    ids = _orch().offers.plan_week()
    print(f"{len(ids)} quiet-night offer(s) waiting: run `marketing review`")


def cmd_lead(args):
    from .agents import LeadsAgent
    from .llm import LLM
    lid = LeadsAgent.add(args.name, args.email, args.company, args.source, args.message)
    print(f"lead #{lid} added")
    if args.score:
        for i, tier, score in LeadsAgent(LLM()).score_new():
            print(f"lead #{i}: {tier} ({score})")


def cmd_leads(args):
    with db.connect("leads") as conn:
        rows = conn.execute(
            "SELECT * FROM leads WHERE status != 'lost' ORDER BY COALESCE(score,-1) DESC LIMIT ?",
            (args.limit,)).fetchall()
    for r in rows:
        print(f"#{r['id']} {r['tier'] or 'unscored':9} {r['score'] if r['score'] is not None else '-':>3}  "
              f"{r['name']} <{r['email']}> {r['company']}  → {r['next_action']}")


def cmd_import_sales(args):
    """Import a Stripe 'Payments' CSV export (or any CSV with the same column names)."""
    added = 0
    with open(args.csv, newline="", encoding="utf-8") as f, db.connect("sales") as conn:
        for row in csv.DictReader(f):
            if row.get("Status", "Paid").lower() not in ("paid", "succeeded"):
                continue
            cur = conn.execute(
                """INSERT OR IGNORE INTO sales (created_at, customer, email, amount, currency,
                   product, source, external_id) VALUES (?,?,?,?,?,?,?,?)""",
                (row.get("Created date (UTC)") or db.now(),
                 row.get("Customer Description") or row.get("Customer Email") or "unknown",
                 row.get("Customer Email", ""), float(row.get("Amount", 0) or 0),
                 (row.get("Currency") or "usd").upper(), row.get("Description", ""),
                 "stripe", row.get("id") or None))
            added += cur.rowcount
    print(f"imported {added} sale(s)")


def cmd_metrics(args):
    with db.connect("posts") as conn:
        n = conn.execute(
            "UPDATE posts SET views=?, likes=?, comments=?, shares=? WHERE id=?",
            (args.views, args.likes, args.comments, args.shares, args.id)).rowcount
    print("updated" if n else "no such post")


def cmd_weekly(_):
    _orch().weekly()


# ---------- the morning dashboard ----------

def cmd_status(_):
    today = datetime.now().strftime("%Y-%m-%d")
    week = "datetime('now','-7 days')"
    rows = [
        ("posts written", db.count("posts", "posts", "created_at >= ?", (today,))),
        ("posts published", db.count("posts", "posts", "published_at >= ?", (today,))),
        ("posts this week", db.count("posts", "posts", f"published_at >= {week}")),
        ("comments triaged", db.count("posts", "inbox", "created_at >= ?", (today,))),
        ("new leads", db.count("leads", "leads", "created_at >= ?", (today,))),
        ("hot leads open", db.count("leads", "leads", "tier='hot' AND status IN ('scored','contacted')")),
        ("calls booked (week)", db.count("leads", "leads", f"status='booked' AND created_at >= {week}")),
        ("sales (week)", db.count("sales", "sales", f"created_at >= {week}")),
    ]
    waiting = (db.count("posts", "posts", "status='pending_approval'")
               + db.count("posts", "inbox", "needs_human=1 AND status='escalated'"))
    print(f"$ marketing status --today   ({today})")
    for label, val in rows:
        print(f"  {label:<22}{val:>5}")
    print(f"  {'waiting on you':<22}{waiting:>5}")
    for name, table in (("posts", "posts"), ("leads", "leads"), ("sales", "sales")):
        print(f"  {name}.db{'':<15}{db.count(name, table):>5} rows")


def main(argv=None):
    p = argparse.ArgumentParser(prog="marketing", description="Your one-person marketing team.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create the databases").set_defaults(fn=cmd_init)

    s = sub.add_parser("run", help="run the orchestrator loop")
    s.add_argument("mode", choices=["daily", "weekly"])
    s.add_argument("--focus", default="")
    s.add_argument("--force", action="store_true", help="run even if knowledge files have TODOs")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("research", help="Research team: today's brief")
    s.add_argument("--focus", default="")
    s.set_defaults(fn=cmd_research)

    s = sub.add_parser("create", help="Creative team: drafts from the latest brief")
    s.add_argument("--count", type=int, default=None)
    s.set_defaults(fn=cmd_create)

    sub.add_parser("review", help="see drafts waiting for approval").set_defaults(fn=cmd_review)
    s = sub.add_parser("approve"); s.add_argument("ids", type=int, nargs="+"); s.set_defaults(fn=cmd_approve)
    s = sub.add_parser("reject"); s.add_argument("ids", type=int, nargs="+")
    s.add_argument("--note", default=""); s.set_defaults(fn=cmd_reject)
    sub.add_parser("publish", help="publish approved posts").set_defaults(fn=cmd_publish)

    s = sub.add_parser("inbox", help="triage a comment/DM, or list the inbox")
    s.add_argument("--channel", default="instagram"); s.add_argument("--author", default="unknown")
    s.add_argument("--text", default=""); s.set_defaults(fn=cmd_inbox)

    s = sub.add_parser("google-review", help="draft a reply to a Google review")
    s.add_argument("author"); s.add_argument("--stars", type=int, required=True)
    s.add_argument("--text", default=""); s.set_defaults(fn=cmd_google_review)

    sub.add_parser("offers", help="write this week's quiet-night SMS/WhatsApp offers").set_defaults(fn=cmd_offers)

    s = sub.add_parser("lead", help="add a catering / party order enquiry")
    s.add_argument("name"); s.add_argument("--email", default=""); s.add_argument("--company", default="")
    s.add_argument("--source", default=""); s.add_argument("--message", default="")
    s.add_argument("--score", action="store_true", help="score it immediately")
    s.set_defaults(fn=cmd_lead)

    s = sub.add_parser("leads", help="ranked lead list"); s.add_argument("--limit", type=int, default=20)
    s.set_defaults(fn=cmd_leads)

    s = sub.add_parser("import-sales", help="import a Stripe payments CSV"); s.add_argument("csv")
    s.set_defaults(fn=cmd_import_sales)

    s = sub.add_parser("metrics", help="record a post's performance")
    s.add_argument("id", type=int)
    for k in ("views", "likes", "comments", "shares"):
        s.add_argument(f"--{k}", type=int, default=0)
    s.set_defaults(fn=cmd_metrics)

    sub.add_parser("weekly", help="analytics + newsletter + SEO article").set_defaults(fn=cmd_weekly)

    s = sub.add_parser("status", help="the morning dashboard")
    s.add_argument("--today", action="store_true"); s.set_defaults(fn=cmd_status)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
