#!/usr/bin/env python3
"""
Daily Brief Agent v1.1
Reads RSS feeds, summarizes with local LLM, outputs Markdown/JSON
"""

import logging
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from config import load_config, ensure_output_dir
from fetch import fetch_all_articles_with_meta
from summarize import (
    check_ollama,
    check_model_exists,
    get_fallback_model,
    summarize_articles
)
from output_writer import save_failure_markdown, save_to_markdown, save_to_json, sync_to_vault

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
logger = logging.getLogger(__name__)


def _setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )


def _bool_env(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def run_daily_brief() -> dict:
    """Run the daily brief once. Designed for CLI or server use."""
    config_file = Path(os.getenv("DAILYBRIEF_CONFIG_PATH", str(PROJECT_ROOT / "config" / "feeds.yaml")))
    output_dir = Path(os.getenv("DAILYBRIEF_OUTPUT_DIR", str(PROJECT_ROOT / "output")))
    prompt_file = Path(os.getenv("DAILYBRIEF_PROMPT_PATH", str(PROJECT_ROOT / "prompts" / "brief.md")))
    cache_file = output_dir / "cache.json"
    log_file = output_dir / "brief.log"

    ensure_output_dir(output_dir)
    _setup_logging(log_file)

    logger.info("\n" + "=" * 50)
    logger.info("🚀 Daily Brief Agent v1.1 Starting")
    logger.info("=" * 50 + "\n")

    try:
        config = load_config(config_file)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {"ok": False, "error": "config_load_failed"}

    settings = config.get("settings", {}) or {}
    provider = (os.getenv("DAILYBRIEF_LLM_PROVIDER") or "").strip().lower()
    if not provider:
        provider = "groq" if os.getenv("GROQ_API_KEY") else "ollama"

    if provider == "groq":
        model_name = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        config.setdefault("settings", {})["summary_model"] = f"groq:{model_name}"
    else:
        model_name = config['settings']['summary_model']
        if not check_ollama():
            logger.error("Cannot proceed without Ollama. Exiting.")
            return {"ok": False, "error": "ollama_unavailable"}

        if not check_model_exists(model_name):
            logger.warning(f"Model '{model_name}' not available. Trying fallback...")
            fallback_model = get_fallback_model()
            if fallback_model:
                model_name = fallback_model
            else:
                logger.error("No models available. Please install one with: ollama pull <model-name>")
                return {"ok": False, "error": "ollama_model_missing"}

    retry_attempts = int(settings.get("network_retry_attempts", 3))
    retry_backoff_s = int(settings.get("network_retry_backoff_seconds", 30))

    articles = []
    fetch_meta = {}
    for attempt in range(1, max(1, retry_attempts) + 1):
        articles, fetch_meta = fetch_all_articles_with_meta(config, cache_file, use_cache=True)
        if articles or fetch_meta.get("network_ok") is not False:
            break
        if attempt < retry_attempts:
            logger.warning("Network unavailable; retrying in %ss (attempt %d/%d)", retry_backoff_s, attempt, retry_attempts)
            time.sleep(max(1, retry_backoff_s))

    if not articles and fetch_meta.get("status") == "network_unavailable":
        reason = "Network/DNS unavailable. Last good brief preserved; will retry on the next run."
        md_failed = save_failure_markdown(output_dir, reason=reason, config=config, meta=fetch_meta)
        if not _bool_env("DAILYBRIEF_DISABLE_VAULT_SYNC", default=False):
            sync_to_vault([md_failed], config)
        return {
            "ok": False,
            "error": "network_unavailable",
            "markdown": str(md_failed),
            "article_count": 0,
            "provider": provider,
            "model": model_name,
        }

    if not articles:
        logger.warning("No articles to summarize")
        summary = "No articles fetched. Feeds may be empty or temporarily unavailable."
    else:
        max_articles = config['settings'].get('max_articles_to_summarize', 20)
        articles_to_summarize = articles[:max_articles]

        logger.info(f"Summarizing {len(articles_to_summarize)} articles...\n")
        summary = summarize_articles(articles_to_summarize, model_name, prompt_file)

    logger.info("\n" + "=" * 50)
    logger.info("=== AI SUMMARY ===")
    logger.info("=" * 50 + "\n")
    print(summary)
    logger.info("\n" + "=" * 50 + "\n")

    md_file = save_to_markdown(output_dir, summary, articles, config, meta=fetch_meta)
    json_file = save_to_json(output_dir, articles, summary)
    if not _bool_env("DAILYBRIEF_DISABLE_VAULT_SYNC", default=False):
        sync_to_vault([md_file, json_file], config)

    # Convenience copies for API access (only after a non-failure run)
    try:
        latest_md = output_dir / "latest.md"
        latest_json = output_dir / "latest.json"
        shutil.copy2(md_file, latest_md)
        shutil.copy2(json_file, latest_json)
    except Exception:
        logger.exception("Failed to write latest.* copies")

    logger.info("\n✅ Daily brief generated successfully!")
    logger.info(f"📄 Markdown: {md_file}")
    logger.info(f"📊 JSON: {json_file}")
    logger.info(f"📝 Log: {log_file}\n")

    return {
        "ok": True,
        "markdown": str(md_file),
        "json": str(json_file),
        "article_count": len(articles),
        "provider": provider,
        "model": model_name,
        "cache_used": bool(fetch_meta.get("cache_used")),
        "cache_cached_at": fetch_meta.get("cache_cached_at"),
        "network_ok": fetch_meta.get("network_ok"),
    }


def main() -> None:
    """CLI entrypoint."""
    run_daily_brief()


if __name__ == "__main__":
    main()
