#!/usr/bin/env python3
"""
Daily Brief Agent v1.1
Reads RSS feeds, summarizes with local LLM, outputs Markdown/JSON
"""

import logging
from pathlib import Path

from config import load_config, ensure_output_dir
from fetch import fetch_all_articles
from summarize import (
    check_ollama,
    check_model_exists,
    get_fallback_model,
    summarize_articles
)
from output_writer import save_to_markdown, save_to_json, sync_to_vault

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "feeds.yaml"
OUTPUT_DIR = PROJECT_ROOT / "output"
CACHE_FILE = OUTPUT_DIR / "cache.json"
LOG_FILE = OUTPUT_DIR / "brief.log"
PROMPT_FILE = PROJECT_ROOT / "prompts" / "brief.md"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main execution function."""
    logger.info("\n" + "=" * 50)
    logger.info("🚀 Daily Brief Agent v1.1 Starting")
    logger.info("=" * 50 + "\n")

    try:
        config = load_config(CONFIG_FILE)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    ensure_output_dir(OUTPUT_DIR)

    if not check_ollama():
        logger.error("Cannot proceed without Ollama. Exiting.")
        return

    model_name = config['settings']['summary_model']
    if not check_model_exists(model_name):
        logger.warning(f"Model '{model_name}' not available. Trying fallback...")
        fallback_model = get_fallback_model()
        if fallback_model:
            model_name = fallback_model
        else:
            logger.error("No models available. Please install one with: ollama pull <model-name>")
            return

    articles = fetch_all_articles(config, CACHE_FILE, use_cache=True)
    if not articles:
        logger.warning("No articles to summarize")
        summary = "No articles fetched. Feeds may be empty or temporarily unavailable."
    else:
        max_articles = config['settings'].get('max_articles_to_summarize', 20)
        articles_to_summarize = articles[:max_articles]

        logger.info(f"Summarizing {len(articles_to_summarize)} articles...\n")
        summary = summarize_articles(articles_to_summarize, model_name, PROMPT_FILE)

    logger.info("\n" + "=" * 50)
    logger.info("=== AI SUMMARY ===")
    logger.info("=" * 50 + "\n")
    print(summary)
    logger.info("\n" + "=" * 50 + "\n")

    md_file = save_to_markdown(OUTPUT_DIR, summary, articles, config)
    json_file = save_to_json(OUTPUT_DIR, articles, summary)
    sync_to_vault([md_file, json_file], config)

    logger.info("\n✅ Daily brief generated successfully!")
    logger.info(f"📄 Markdown: {md_file}")
    logger.info(f"📊 JSON: {json_file}")
    logger.info(f"📝 Log: {LOG_FILE}\n")


if __name__ == "__main__":
    main()
