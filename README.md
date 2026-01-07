# Daily Brief Agent

Automated AI/tech news aggregator. Pulls from RSS feeds, summarizes with local LLM, outputs Markdown. Replaces 4+ hours of manual news reading with a 10-minute brief.

## Status: v1.0 Shipped ✅

Production-ready system generating daily briefs.

## What It Does

**Problem:** Staying updated on AI/tech requires watching YouTube, scrolling Reddit, reading dozens of blogs (4-6 hours/day).

**Solution:** Fetches articles from 5+ sources, AI summarizes, generates formatted brief.

**Result:** 10-minute read covers everything.

## Features

**v1.0 includes:**
- RSS aggregation (5 sources: Hacker News, OpenAI, Anthropic, TechCrunch, The Verge)
- Article deduplication (removes 10-30% duplicates)
- Date filtering (only last 48 hours)
- Article ranking (AI, GPT, LLM keywords prioritized)
- Local LLM summarization (DeepSeek via Ollama)
- Markdown + JSON export
- 1-hour caching (avoids re-fetching)
- Comprehensive logging

## Tech Stack

- Python 3.x
- `feedparser` (RSS parsing)
- `ollama` (local LLM)
- `pyyaml` (config management)
- DeepSeek Coder v2:16b (summarization model)

## Setup
```bash
git clone https://github.com/taxman-dev/daily-brief-agent.git
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
```

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

**`brief_YYYY-MM-DD.json`** (raw data for further processing)

## How It Works

1. **Fetch:** Pulls articles from configured RSS feeds
2. **Deduplicate:** Removes duplicates via title+link hash
3. **Filter:** Only includes articles from last 48 hours
4. **Rank:** Prioritizes AI/GPT/LLM keywords + recency
5. **Summarize:** Sends top 20 articles to local LLM
6. **Export:** Markdown (readable) + JSON (machine-readable)
7. **Cache:** Saves articles for 1 hour (avoids re-fetching)

## Roadmap

**Week 2:** YouTube module (auto-summarize AI channel videos)  
**Week 3:** Reddit module (top posts from r/LocalLLaMA, r/MachineLearning)  
**Week 4:** Deploy to Fly.io (runs automatically at 6am daily)

## Project Structure
```
daily-brief-agent/
├── src/
│   └── brief.py          # Main script (400+ lines)
├── config/
│   └── feeds.yaml        # RSS feed configuration
├── output/
│   ├── brief_YYYY-MM-DD.md
│   ├── brief_YYYY-MM-DD.json
│   ├── cache.json
│   └── brief.log
├── requirements.txt
└── README.md
```

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

