# Architecture

## Data Flow
1. Load config (`config/feeds.yaml`)
2. Fetch RSS feeds
3. Deduplicate + recency filter
4. Rank articles
5. Build prompt from template
6. Summarize via Ollama
7. Write Markdown + JSON
8. Sync to Obsidian vault

## Modules
- `src/brief.py` - Orchestrator
- `src/config.py` - Config + output directory
- `src/fetch.py` - RSS fetch + cache
- `src/summarize.py` - Prompt + LLM
- `src/output_writer.py` - Markdown/JSON + vault sync
- `src/utils.py` - Shared helpers

## External Dependencies
- Ollama (local inference)
- RSS sources defined in config
