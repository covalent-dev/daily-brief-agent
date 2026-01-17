# Configuration

## feeds.yaml
Key sections:
- `feeds`: list of RSS sources
- `settings`: limits, model, filters, vault sync

Example:
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

## Scheduling
See `scripts/com.covalent.daily-brief.plist` for launchd config.
