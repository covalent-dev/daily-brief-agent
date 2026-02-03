# Personal Briefing System

Automated AI/tech news aggregator. Pulls from RSS feeds, summarizes with LLM, outputs Markdown. Replaces hours of manual news reading with a 10-minute brief.

## Status: v1.2 — Live on Fly.io 🚀

**URL:** https://daily-brief-agent.fly.dev/

| Feature | Status |
|---------|--------|
| RSS aggregation | ✅ |
| LLM summarization | ✅ (Groq cloud + Ollama local) |
| Markdown + JSON output | ✅ |
| Obsidian vault sync | ✅ |
| Scheduled runs (local) | ✅ launchd |
| Scheduled runs (cloud) | ✅ Fly.io 7:00 AM daily |
| Email notification | ✅ |
| Auto-sync to Obsidian | ✅ Cron job |

## Quick Access

```bash
# Add to ~/.zshrc
alias brief="curl -s https://daily-brief-agent.fly.dev/latest -H 'X-Dailybrief-Token: YOUR_TOKEN'"
alias brief-run="curl -s -X POST https://daily-brief-agent.fly.dev/run -H 'X-Dailybrief-Token: YOUR_TOKEN'"
```

Then:
```bash
brief          # Get latest brief
brief-run      # Trigger new generation
```

## What It Does

**Problem:** Staying updated on AI/tech requires watching YouTube, scrolling Reddit, reading dozens of blogs.

**Solution:** Fetches articles from 5+ sources, AI summarizes, generates formatted brief.

**Result:** 10-minute read covers everything.

## Fly.io Deployment (Production)

The app runs on Fly.io with:
- FastAPI service (health + API endpoints)
- Built-in scheduler (runs daily at configured time)
- Persistent storage on Fly Volume
- Groq LLM for cloud summarization

### Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | No | Health check |
| `POST /run` | Token | Trigger brief generation |
| `GET /latest` | Token | Get latest brief as markdown |

Auth header: `X-Dailybrief-Token: YOUR_TOKEN`

### Environment Variables

```bash
# Required
GROQ_API_KEY=...              # Groq API key for LLM
DAILYBRIEF_ACCESS_TOKEN=...   # API auth token

# Optional (defaults shown)
DAILYBRIEF_TZ=America/Chicago
DAILYBRIEF_RUN_HHMM=07:00
DAILYBRIEF_SCHEDULE_ENABLED=true
```

### Deploy Commands

```bash
fly auth login
fly deploy --app daily-brief-agent
fly secrets set GROQ_API_KEY=... DAILYBRIEF_ACCESS_TOKEN=...
fly logs --app daily-brief-agent
```

## Local Setup

```bash
git clone https://github.com/covalent-dev/daily-brief-agent.git
cd daily-brief-agent

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# For local LLM (optional)
brew install ollama
ollama pull deepseek-coder-v2:16b

python3 src/brief.py
```

## Configuration

Edit `config/feeds.yaml`:

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
    vault_path: "/path/to/obsidian/vault/Daily-Briefs"
```

## Scheduled Local Runs (macOS)

```bash
# Load launchd job
cp scripts/com.covalent.daily-brief.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.covalent.daily-brief.plist

# Check logs
tail -f output/launchd.log
```

Runs daily at 5:00 AM local time.

## Output

**Markdown brief:**
```markdown
# 📰 Daily Tech Brief

**Date**: 2026-01-31
**Total Articles**: 16
**Model**: groq:llama-3.1-8b-instant

## 🤖 AI Summary
[Organized by topic]

## 📋 All Articles
- **[Article Title](link)**
  *Source* - Date
```

**Files:**
- `output/brief_YYYY-MM-DD.md` — Formatted brief
- `output/brief_YYYY-MM-DD.json` — Raw data
- `output/latest.md` — Symlink to most recent

## Project Structure

```
daily-brief-agent/
├── src/
│   ├── brief.py          # Orchestrator
│   ├── server.py         # FastAPI (Fly.io)
│   ├── fetch.py          # RSS fetch + cache
│   ├── summarize.py      # LLM (Ollama/Groq)
│   └── output_writer.py  # Markdown/JSON
├── config/feeds.yaml     # RSS sources
├── prompts/brief.md      # LLM prompt
├── Dockerfile            # Fly.io container
├── fly.toml              # Fly.io config
└── requirements.txt
```

## Performance

| Metric | Local (Ollama) | Cloud (Groq) |
|--------|----------------|--------------|
| Total time | ~50s | ~15s |
| LLM call | ~45s | ~10s |
| Memory | ~200MB | ~50MB |

---

*Updated: 2026-01-31 | v1.2 — Live on Fly.io*
