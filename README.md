# One-Person Marketing Team

An orchestrator plus 7 specialist AI agent teams running on Claude. It writes and publishes your content, triages comments, scores leads and learns from your results. **Nothing goes out without your approval.**

```
           Knowledge files (offer · audience · voice · channels · rules · compliance)
                                        │
                                 ┌──────▼───────┐
                                 │ Orchestrator │  marketing run daily | weekly
                                 └──────┬───────┘
   ┌──────────┬──────────┬─────────────┼────────────┬──────────┬───────────┐
Research   Creative  Distribution    Email        Leads      Search     Analytics
(web search) (posts,  (publish,      (newsletter) (score,    (SEO blog  (what worked →
            scripts)   comments,                  follow-up)  articles)  feeds Research)
                       escalation)
   └──────────┴──────────┴─────────────┼────────────┴──────────┴───────────┘
                         posts.db · leads.db · sales.db  (SQLite, in ./data)
                                        │
                           YOU: review → approve → publish
```

## Setup (10 minutes)

```bash
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...      # from platform.claude.com
marketing init
```

Then **fill in the 6 files in `marketing_team/knowledge/`**. This is the most important step: the agents are only as good as what you tell them about your offer, audience and voice.

## Daily use

```bash
marketing run daily        # research → drafts → score leads → publish what you approved
marketing review           # read today's drafts
marketing approve 4 5 7    # approve the ones you like
marketing reject 6 --note "too salesy"
marketing status --today   # the morning dashboard
```

Weekly: `marketing run weekly` runs the analytics, writes a newsletter draft and an SEO article. Drafts are saved in `data/drafts/`.

Other commands:

| Command | What it does |
|---|---|
| `marketing inbox --channel instagram --author @sam --text "..."` | Triage a comment or DM. Draft reply, or 🔴 escalate to you |
| `marketing lead "Sam Lee" --email sam@x.com --message "..." --score` | Add a lead and score it |
| `marketing leads` | Ranked lead list with next actions and draft emails |
| `marketing import-sales payments.csv` | Import a Stripe payments CSV export into sales.db |
| `marketing metrics 12 --views 4000 --likes 210 --comments 31` | Record how a post did (feeds the analytics loop) |

## Publishing

By default posts are written to `data/outbox/` (dry run) and you upload them yourself.

To automate it, set `MKT_PUBLISHER=webhook` and `MKT_WEBHOOK_URL=https://hooks.zapier.com/...`. Each approved post is sent as JSON to a Zapier, Make or n8n scenario, which posts it to TikTok, Instagram, Facebook and Google Business Profile (directly or through Buffer or Metricool). This takes about an hour to set up. Applying for each platform's own API can take months.

## Run it on autopilot

On a Mac or Linux server, add these to cron (`crontab -e`):

```
15 7 * * *  cd /path/to/repo && marketing run daily
40 7 * * 1  cd /path/to/repo && marketing run weekly
```

## Settings (environment variables)

| Variable | Default |
|---|---|
| `MKT_MODEL` | `claude-opus-5-5` |
| `MKT_CHANNELS` | `instagram,tiktok,facebook,google` (LinkedIn is not used) |
| `MKT_POSTS_PER_DAY` | `2` (per channel) |
| `MKT_DATA_DIR` | `./data` |
| `MKT_PUBLISHER` / `MKT_WEBHOOK_URL` | `dry-run` / empty |

## Tests

```bash
pip install -e '.[dev]' && pytest
```

The tests use a fake model, so they cost nothing.
