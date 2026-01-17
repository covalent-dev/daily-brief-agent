# Daily Brief Agent v1 - Overview

## Purpose
Automated AI/tech news aggregator that fetches RSS feeds, summarizes with a local LLM, and outputs Markdown + JSON briefs for daily reading.

## What It Replaces
Manual reading across multiple sources (4-6 hours/day) → 10-minute brief.

## Core Capabilities (v1.1)
- RSS aggregation (multi-feed)
- Deduplication + recency filtering
- Keyword ranking
- LLM summarization via Ollama
- Markdown + JSON output
- Cache (1h TTL)
- Obsidian vault sync
- Scheduled daily run (launchd)
- Prompt template + basic tests

## Target Users
- Solo builder / contractor who needs daily market awareness
- Personal knowledge base workflows (Obsidian)
