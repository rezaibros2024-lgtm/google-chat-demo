# Juniors Pizza & Kebab — AI Marketing Team

An orchestrator plus 8 specialist AI agents running on Claude. It writes and publishes your content, triages comments, scores leads and learns from your results. **Nothing goes out without your approval.**

```
           Knowledge files (offer · audience · voice · channels · rules · compliance)
                                        │
                                 ┌──────▼───────┐
                                 │ Orchestrator │  marketing run daily | weekly
                                 └──────┬───────┘
  ┌─────────┬─────────┬────────────┬──────┼──────┬──────────┬──────────┬───────────┐
Research Creative Distribution Reviews  Offers   Leads     Email    Analytics
(trends) (Insta,  (publish,    (Google  (Tue/Wed (catering, (news-  (what worked →
         TikTok,  comments,    review   SMS &    parties)   letter)  feeds Research)
         FB, GBP) escalation)  replies) WhatsApp)
  └─────────┴─────────┴────────────┴──────┼──────┴──────────┴──────────┴───────────┘
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

Weekly: `marketing run weekly` runs the analytics, writes the quiet-night SMS/WhatsApp offers (they wait for your approval) and a newsletter draft in `data/drafts/`. Approved SMS offers always go to `data/outbox/` so you can send them from your own SMS tool to opted-in customers. They never go out through the social media webhook.

Other commands:

| Command | What it does |
|---|---|
| `marketing inbox --channel instagram --author @sam --text "..."` | Triage a comment or DM. Draft reply, or 🔴 escalate to you |
| `marketing google-review "Sam" --stars 5 --text "..."` | Draft a reply to a Google review. Reviews of 1–3 stars are always flagged for you |
| `marketing offers` | Write this week's quiet-night offers (`MKT_QUIET_NIGHTS`, default Tuesday,Wednesday) |
| `marketing lead "Cheltenham FC" --message "Pizza for 30 kids Sat" --score` | Add a catering or party enquiry and score it |
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
| `MKT_QUIET_NIGHTS` | `Tuesday,Wednesday` |
| `MKT_POSTS_PER_DAY` | `2` (per channel) |
| `MKT_DATA_DIR` | `./data` |
| `MKT_PUBLISHER` / `MKT_WEBHOOK_URL` | `dry-run` / empty |

## Tests

```bash
pip install -e '.[dev]' && pytest
```

The tests use a fake model, so they cost nothing.
