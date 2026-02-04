# Personal Briefing System

Automated AI/tech news aggregator. Pulls from RSS feeds, summarizes with local LLM, outputs Markdown. Replaces 4+ hours of manual news reading with a 10-minute brief.

## Status: v1.1 Shipped

Production-ready system generating daily briefs with scheduling.

**Month 1 checklist (Tech Progression v3):**
- ✅ Local LLM summarizer + RSS ingestion
- ✅ Configurable topics + categories
- ✅ Markdown output to Obsidian
- ✅ Scheduled runs (launchd)
- ✅ Optional email notification
- ⏳ Live deploy (planned after domain/portfolio launch)

## What It Does

**Problem:** Staying updated on AI/tech requires watching YouTube, scrolling Reddit, reading dozens of blogs (4-6 hours/day).

**Solution:** Fetches articles from 5+ sources, AI summarizes, generates formatted brief.

**Result:** 10-minute read covers everything.

## Features

**v1.1 includes:**
- RSS aggregation (5 sources: Hacker News, OpenAI, Anthropic, TechCrunch, The Verge)
- Article deduplication (removes 10-30% duplicates)
- Date filtering (only last 48 hours)
- Article ranking (AI, GPT, LLM keywords prioritized)
- Local LLM summarization (DeepSeek via Ollama)
- Markdown + JSON export
- 1-hour caching (avoids re-fetching)
- Comprehensive logging
- Prompt template (`prompts/brief.md`)
- Modular codebase (fetch/summarize/output/utils)
- Scheduled runs via launchd
- Basic sanity tests

## Tech Stack

- Python 3.x
- `feedparser` (RSS parsing)
- `ollama` (local LLM)
- `pyyaml` (config management)
- DeepSeek Coder v2:16b (summarization model)

## Setup
```bash
git clone https://github.com/covalent-dev/daily-brief-agent.git
cd daily-brief-agent

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Ollama + model
brew install ollama
ollama pull deepseek-coder-v2:16b

# Run
python3 src/brief.py
```

## Scheduled Run (macOS launchd)

1. Make the runner executable:
```bash
chmod +x /Users/taxman/covalent-dev/daily-brief-agent/scripts/run_daily_brief.sh
```

2. Copy the launchd plist:
```bash
cp /Users/taxman/covalent-dev/daily-brief-agent/scripts/com.covalent.daily-brief.plist ~/Library/LaunchAgents/
```

3. Load the job:
```bash
launchctl load ~/Library/LaunchAgents/com.covalent.daily-brief.plist
```

4. Check logs:
```bash
tail -n 50 /Users/taxman/covalent-dev/daily-brief-agent/output/launchd.log
```

This runs daily at 5:00 AM local time and also checks every 30 minutes while the Mac is awake to retry if the network was down. The runner skips before 05:00 and exits if today’s brief already exists.

**Note:** `scripts/run_daily_brief.sh` calls an optional helper at `$HOME/.local/bin/dailybrief`. If you don’t have it installed, remove that line or replace it with your own pre-run hook.

## Email Notification (Gmail + Keychain)

Store credentials in Keychain:
```bash
security add-generic-password -a "$USER" -s daily-brief-gmail-user -w "YOUR_GMAIL_ADDRESS"
security add-generic-password -a "$USER" -s daily-brief-gmail-pass -w "APP_PASSWORD"
security add-generic-password -a "$USER" -s daily-brief-email-to -w "YOUR_TO_ADDRESS"
```

The runner calls `scripts/notify_email.py` after the brief is generated.

## Configuration

Edit `config/feeds.yaml` to add/remove sources:
```yaml
feeds:
  - name: "Hacker News"
    url: "https://hnrss.org/newest?q=AI+OR+GPT+OR+LLM"
    category: "News"

settings:
  max_articles_per_feed: 5
  max_articles_to_summarize: 20
  filter_hours: 48
  summary_model: "deepseek-coder-v2:16b"
  vault_sync:
    enabled: true
    vault_path: "/Users/taxman/Taxman_Progression_v4/05_Knowledge_Base/Daily-Briefs"
```

**Topic coverage:** Add feeds for job market, crypto, or personal interests by inserting additional entries under `feeds:` and setting an appropriate `category`.

## Output

**Generates two files in `output/`:**

**`brief_YYYY-MM-DD.md`** (formatted brief):
```markdown
# 📰 Daily Tech Brief

**Date**: 2026-01-05
**Total Articles**: 20
**Model**: deepseek-coder-v2:16b

## 🤖 AI Summary
[Themed summary organized by importance]

## 📋 All Articles
### News
- **[Article Title](link)**
  *Source* - Date
  Preview text...
```

## Documentation

High-level docs live in `docs/`:
- Overview, architecture, configuration, prompting
- Output specs, operations, troubleshooting
- Changelog

## Tests

Run basic sanity checks:
```bash
python3 -m unittest tests/test_utils.py
```

**`brief_YYYY-MM-DD.json`** (raw data for further processing)

## How It Works

1. **Fetch:** Pulls articles from configured RSS feeds
2. **Deduplicate:** Removes duplicates via title+link hash
3. **Filter:** Only includes articles from last 48 hours
4. **Rank:** Prioritizes AI/GPT/LLM keywords + recency
5. **Summarize:** Sends top 20 articles to local LLM
6. **Export:** Markdown (readable) + JSON (machine-readable)
7. **Cache:** Saves articles for 1 hour (avoids re-fetching)

## Project Structure
```
daily-brief-agent/
├── src/
│   ├── brief.py          # Orchestrator
│   ├── config.py         # Config + output dir
│   ├── fetch.py          # RSS fetch + cache
│   ├── summarize.py      # LLM prompt + summarize
│   ├── output_writer.py  # Markdown/JSON output
│   └── utils.py          # Shared helpers
├── config/
│   └── feeds.yaml        # RSS feed configuration
├── prompts/
│   └── brief.md          # Prompt template
├── scripts/
│   ├── run_daily_brief.sh
│   └── com.covalent.daily-brief.plist
├── tests/
│   └── test_utils.py
├── output/
│   ├── brief_YYYY-MM-DD.md
│   ├── brief_YYYY-MM-DD.json
│   ├── cache.json
│   └── brief.log
├── requirements.txt
└── README.md
```

## Fly.io Deployment (Cloud)

This repo includes a Fly.io deployment that runs the brief on startup and then daily on a schedule.

### What runs on Fly
- A small FastAPI service (for health + manual triggers)
- A built-in scheduler loop (runs daily at the configured time)
- Output persisted on a Fly Volume at `/data/output`

### One-time setup
```bash
brew install flyctl
fly auth login

cd daily-brief-agent
fly apps create daily-brief-agent
fly volumes create dailybrief_data --region ord --size 1 --app daily-brief-agent --yes
```

### Configure secrets (required)
The cloud deployment uses Groq (local Ollama cannot be used on Fly).

```bash
fly secrets set GROQ_API_KEY=... DAILYBRIEF_ACCESS_TOKEN=... --app daily-brief-agent
```

### Deploy
```bash
fly deploy --app daily-brief-agent
```

### Endpoints
- `GET /health` (no auth) — used by Fly health checks
- `POST /run` (auth optional) — trigger a run immediately
- `GET /latest` (auth optional) — returns `latest.md` as plain text

If `DAILYBRIEF_ACCESS_TOKEN` is set, include:
```bash
curl -H "X-Dailybrief-Token: $DAILYBRIEF_ACCESS_TOKEN" https://daily-brief-agent.fly.dev/latest
```

### Scheduling
Set schedule via env vars (configured in `fly.toml` by default):
- `DAILYBRIEF_TZ` (example: `America/Chicago`)
- `DAILYBRIEF_RUN_HHMM` (example: `07:00`)
- `DAILYBRIEF_SCHEDULE_ENABLED` (`true`/`false`)

Notes:
- The Fly app is configured to keep 1 machine running so the scheduler can fire.
- Vault sync is disabled on Fly via `DAILYBRIEF_DISABLE_VAULT_SYNC=true`.

## Performance

**Day 1 execution:**
- Feed fetch: ~5 seconds (5 sources)
- Article processing: <1 second (20 articles)
- AI summarization: ~45 seconds (DeepSeek Coder v2)
- **Total: ~50 seconds**

**Memory:** ~200MB (mostly Ollama model)  
**Disk:** ~100KB per daily brief

## Why Local LLM?

- **Free:** No API costs ($0 vs $20-50/month for GPT)
- **Fast:** Local inference, no network latency
- **Private:** News summaries stay on device
- **Offline:** Works without internet (after RSS fetch)

## Example Brief

See `output/brief_2026-01-05.md` for real output.

---
