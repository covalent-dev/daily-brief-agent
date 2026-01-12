#!/usr/bin/env python3
"""
Daily Brief Agent v1.0
Reads RSS feeds, summarizes with local LLM, outputs Markdown
"""

import feedparser
import yaml
import ollama
import json
import logging
import asyncio
import aiohttp
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict
import hashlib
import re

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "feeds.yaml"
OUTPUT_DIR = PROJECT_ROOT / "output"
CACHE_FILE = OUTPUT_DIR / "cache.json"
LOG_FILE = OUTPUT_DIR / "brief.log"

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

def load_config() -> Dict:
    """Load RSS feeds from config file"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {CONFIG_FILE}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing config file: {e}")
        raise

def ensure_output_dir() -> None:
    """Create output directory if it doesn't exist"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    logger.info(f"Output directory ready: {OUTPUT_DIR}")
def check_ollama() -> bool:
    """Check if Ollama is running and accessible"""
    try:
        ollama.list()
        logger.info("✓ Ollama is running")
        return True
    except Exception as e:
        logger.error(f"❌ Ollama not accessible: {e}")
        logger.error("Start Ollama with: ollama serve")
        return False


def check_model_exists(model_name: str) -> bool:
    """Check if the specified model is available in Ollama"""
    try:
        models = ollama.list()
        available_models = [m.get('model') or m.get('name') for m in models.get('models', [])]
        
        if model_name in available_models:
            logger.info(f"✓ Model '{model_name}' is available")
            return True
        else:
            logger.warning(f"⚠️  Model '{model_name}' not found")
            logger.info(f"Available models: {', '.join(available_models)}")
            logger.info(f"To install: ollama pull {model_name}")
            return False
    except Exception as e:
        logger.error(f"Error checking models: {e}")
        return False


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats from RSS feeds"""
    if not date_str or date_str == 'Unknown date':
        return None
    
    try:
        # feedparser provides parsed_date in time.struct_time
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except Exception:
        return None


def is_recent(article: Dict, hours: int = 48) -> bool:
    """Check if article is from the last N hours"""
    pub_date = parse_date(article.get('published', ''))
    if not pub_date:
        return True  # Include if we can't parse date
    
    cutoff = datetime.now(pub_date.tzinfo) - timedelta(hours=hours)
    return pub_date >= cutoff


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text at word boundary"""
    if len(text) <= max_length:
        return text
    
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."


def calculate_article_hash(article: Dict) -> str:
    """Generate hash for deduplication"""
    # Use title + link for uniqueness
    content = f"{article['title']}{article['link']}"
    return hashlib.md5(content.encode()).hexdigest()


def fetch_articles(feed_config: Dict, max_articles: int = 5) -> List[Dict]:
    """
    Fetch articles from a single RSS feed
    Returns list of dicts: {title, link, summary, published}
    """
    logger.info(f"📡 Fetching: {feed_config['name']}...")
    
    try:
        feed = feedparser.parse(feed_config['url'])
        
        if feed.bozo:
            logger.warning(f"  ⚠️  Feed parsing warning for {feed_config['name']}")
        
        articles = []
        for entry in feed.entries[:max_articles]:
            article = {
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', ''),
                'summary': entry.get('summary', entry.get('description', 'No summary')),
                'published': entry.get('published', 'Unknown date'),
                'source': feed_config['name'],
                'category': feed_config.get('category', 'General')
            }
            
            # Add hash for deduplication
            article['hash'] = calculate_article_hash(article)
            articles.append(article)
        
        logger.info(f"  ✓ Got {len(articles)} articles")
        return articles
        
    except Exception as e:
        logger.error(f"  ✗ Error fetching {feed_config['name']}: {e}")
        return []

def deduplicate_articles(articles: List[Dict]) -> List[Dict]:
    """Remove duplicate articles based on hash"""
    seen_hashes = set()
    unique_articles = []
    duplicates = 0
    
    for article in articles:
        article_hash = article.get('hash')
        if article_hash not in seen_hashes:
            seen_hashes.add(article_hash)
            unique_articles.append(article)
        else:
            duplicates += 1
    
    if duplicates > 0:
        logger.info(f"  ℹ️  Removed {duplicates} duplicate articles")
    
    return unique_articles


def filter_recent_articles(articles: List[Dict], hours: int = 48) -> List[Dict]:
    """Filter articles to only recent ones"""
    recent = [a for a in articles if is_recent(a, hours)]
    filtered_count = len(articles) - len(recent)
    
    if filtered_count > 0:
        logger.info(f"  ℹ️  Filtered out {filtered_count} old articles (>{hours}h)")
    
    return recent


def load_cache() -> Dict:
    """Load cached articles from previous run"""
    if not CACHE_FILE.exists():
        return {'articles': [], 'timestamp': None}
    
    try:
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
            logger.info(f"  ℹ️  Loaded cache from {cache.get('timestamp', 'unknown time')}")
            return cache
    except Exception as e:
        logger.warning(f"  ⚠️  Could not load cache: {e}")
        return {'articles': [], 'timestamp': None}


def save_cache(articles: List[Dict]) -> None:
    """Save articles to cache"""
    cache = {
        'articles': articles,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
        logger.info(f"  ℹ️  Saved {len(articles)} articles to cache")
    except Exception as e:
        logger.warning(f"  ⚠️  Could not save cache: {e}")


def fetch_all_articles(config: Dict, use_cache: bool = True) -> List[Dict]:
    """Fetch from all configured feeds"""
    # Check cache first
    if use_cache:
        cache = load_cache()
        if cache.get('timestamp'):
            cache_time = datetime.fromisoformat(cache['timestamp'])
            if datetime.now() - cache_time < timedelta(hours=1):
                logger.info("✓ Using cached articles (less than 1 hour old)")
                return cache['articles']
    
    all_articles = []
    max_per_feed = config['settings']['max_articles_per_feed']
    
    for feed_config in config['feeds']:
        articles = fetch_articles(feed_config, max_per_feed)
        all_articles.extend(articles)
    
    logger.info(f"\n📰 Total articles fetched: {len(all_articles)}")
    
    # Deduplicate
    all_articles = deduplicate_articles(all_articles)
    logger.info(f"📰 Unique articles: {len(all_articles)}")
    
    # Filter recent
    filter_hours = config['settings'].get('filter_hours', 48)
    all_articles = filter_recent_articles(all_articles, filter_hours)
    logger.info(f"📰 Recent articles: {len(all_articles)}\n")
    
    # Save to cache
    save_cache(all_articles)
    
    return all_articles

def rank_articles(articles: List[Dict]) -> List[Dict]:
    """Simple ranking based on keywords and recency"""
    keywords = ['AI', 'GPT', 'LLM', 'breakthrough', 'release', 'launch', 'announced']
    
    for article in articles:
        score = 0
        title_lower = article['title'].lower()
        
        # Keyword matching
        for keyword in keywords:
            if keyword.lower() in title_lower:
                score += 2
        
        # Recency bonus
        if is_recent(article, hours=24):
            score += 3
        
        article['rank_score'] = score
    
    return sorted(articles, key=lambda x: x.get('rank_score', 0), reverse=True)


def summarize_articles(articles: List[Dict], model: str) -> str:
    """
    Send articles to LLM for summarization
    Returns summarized text
    """
    logger.info("🤖 Summarizing with AI...\n")
    
    # Rank articles for better summary
    ranked_articles = rank_articles(articles)
    
    # Build prompt with proper formatting
    articles_text = ""
    for i, article in enumerate(ranked_articles, 1):
        articles_text += f"\n{i}. **{article['title']}**\n"
        articles_text += f"   - Source: {article['source']}\n"
        articles_text += f"   - Category: {article['category']}\n"
        articles_text += f"   - Link: {article['link']}\n"
        articles_text += f"   - Preview: {truncate_text(article['summary'], 300)}\n"
    
    prompt = f"""You are a tech news curator creating a daily brief. Below are today's articles from various tech/AI sources.

Your task:
1. Create a well-organized summary using proper Markdown formatting
2. Group articles by theme or importance
3. For significant articles, explain:
   - What happened (1-2 sentences)
   - Why it matters
4. Use markdown headers (##), bullet points, and **bold** for emphasis
5. Be concise and actionable
6. Include article links where relevant

Articles:
{articles_text}

Format your response as clean Markdown with clear sections.
"""
    
    # Call Ollama
    try:
        response = ollama.chat(
            model=model,
            messages=[{
                'role': 'user',
                'content': prompt
            }]
        )
        
        summary = response['message']['content']
        logger.info("✓ Summary generated\n")
        return summary
        
    except Exception as e:
        logger.error(f"✗ Error calling LLM: {e}")
        return "Error generating summary. Please check if the model is available."



def save_to_markdown(summary: str, articles: List[Dict], config: Dict) -> Path:
    """Save summary and articles to markdown file"""
    timestamp = datetime.now()
    date_str = timestamp.strftime("%Y-%m-%d")
    time_str = timestamp.strftime("%H:%M:%S")
    output_file = OUTPUT_DIR / f"brief_{date_str}.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write(f"# 📰 Daily Tech Brief\n\n")
        f.write(f"**Date**: {date_str}  \n")
        f.write(f"**Generated**: {time_str}  \n")
        f.write(f"**Total Articles**: {len(articles)}  \n")
        f.write(f"**Model**: {config['settings']['summary_model']}\n\n")
        f.write("---\n\n")
        
        # AI Summary
        f.write("## 🤖 AI Summary\n\n")
        f.write(summary)
        f.write("\n\n---\n\n")
        
        # Full article list grouped by category
        f.write("## 📋 All Articles\n\n")
        
        # Group by category
        by_category = defaultdict(list)
        for article in articles:
            by_category[article['category']].append(article)
        
        for category, cat_articles in by_category.items():
            f.write(f"### {category}\n\n")
            for article in cat_articles:
                f.write(f"- **[{article['title']}]({article['link']})**  \n")
                f.write(f"  *{article['source']}* - {article['published']}  \n")
                f.write(f"  {truncate_text(article['summary'], 150)}\n\n")
        
        # Footer
        f.write("---\n\n")
        f.write(f"*Generated by Daily Brief Agent on {timestamp.strftime('%Y-%m-%d at %H:%M:%S')}*\n")
    
    logger.info(f"✓ Markdown saved to: {output_file}")
    return output_file


def save_to_json(articles: List[Dict], summary: str) -> Path:
    """Save raw data to JSON for further processing"""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"brief_{timestamp}.json"
    
    data = {
        'generated_at': datetime.now().isoformat(),
        'summary': summary,
        'article_count': len(articles),
        'articles': articles
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✓ JSON saved to: {output_file}")
    return output_file


def sync_to_vault(files: List[Path], config: Dict) -> None:
    """Copy output files to Obsidian vault if enabled"""
    vault_config = config.get('settings', {}).get('vault_sync', {})

    if not vault_config.get('enabled', False):
        return

    vault_path = vault_config.get('vault_path')
    if not vault_path:
        logger.warning("Vault sync enabled but no vault_path configured")
        return

    vault_path = Path(vault_path)
    vault_path.mkdir(parents=True, exist_ok=True)

    for source_path in files:
        if source_path and source_path.exists():
            dest_path = vault_path / source_path.name
            shutil.copy2(source_path, dest_path)
            logger.info(f"📁 Synced to Obsidian: {dest_path}")


def get_fallback_model() -> Optional[str]:
    """Get first available model as fallback"""
    try:
        models = ollama.list()
        available = models.get('models', [])
        if available:
            fallback = available[0]['name']
            logger.info(f"  ℹ️  Using fallback model: {fallback}")
            return fallback
    except Exception:
        pass
    return None


def main():
    """Main execution function"""
    logger.info("\n" + "="*50)
    logger.info("🚀 Daily Brief Agent v1.0 Starting")
    logger.info("="*50 + "\n")
    
    # Load config
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return
    
    # Setup
    ensure_output_dir()
    
    # Check Ollama
    if not check_ollama():
        logger.error("Cannot proceed without Ollama. Exiting.")
        return
    
    # Check model
    model_name = config['settings']['summary_model']
    if not check_model_exists(model_name):
        logger.warning(f"Model '{model_name}' not available. Trying fallback...")
        fallback_model = get_fallback_model()
        if fallback_model:
            model_name = fallback_model
        else:
            logger.error("No models available. Please install one with: ollama pull <model-name>")
            return
    
    # Fetch articles
    articles = fetch_all_articles(config, use_cache=True)
    
    if not articles:
        logger.warning("No articles to summarize")
        return
    
    # Summarize
    max_articles = config['settings'].get('max_articles_to_summarize', 20)
    articles_to_summarize = articles[:max_articles]
    
    logger.info(f"Summarizing {len(articles_to_summarize)} articles...\n")
    summary = summarize_articles(articles_to_summarize, model_name)
    
    # Display summary
    logger.info("\n" + "="*50)
    logger.info("=== AI SUMMARY ===")
    logger.info("="*50 + "\n")
    print(summary)
    logger.info("\n" + "="*50 + "\n")
    
    # Save outputs
    md_file = save_to_markdown(summary, articles, config)
    json_file = save_to_json(articles, summary)

    # Sync to Obsidian vault
    sync_to_vault([md_file, json_file], config)

    logger.info("\n✅ Daily brief generated successfully!")
    logger.info(f"📄 Markdown: {md_file}")
    logger.info(f"📊 JSON: {json_file}")
    logger.info(f"📝 Log: {LOG_FILE}\n")


if __name__ == "__main__":
    main()


