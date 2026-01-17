import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import ollama

from utils import is_recent, truncate_text

logger = logging.getLogger(__name__)


def check_ollama() -> bool:
    """Check if Ollama is running and accessible."""
    try:
        ollama.list()
        logger.info("✓ Ollama is running")
        return True
    except Exception as e:
        logger.error(f"❌ Ollama not accessible: {e}")
        logger.error("Start Ollama with: ollama serve")
        return False


def check_model_exists(model_name: str) -> bool:
    """Check if the specified model is available in Ollama."""
    try:
        models = ollama.list()
        available_models = [m.get('model') or m.get('name') for m in models.get('models', [])]

        if model_name in available_models:
            logger.info(f"✓ Model '{model_name}' is available")
            return True
        logger.warning(f"⚠️  Model '{model_name}' not found")
        logger.info(f"Available models: {', '.join(available_models)}")
        logger.info(f"To install: ollama pull {model_name}")
        return False
    except Exception as e:
        logger.error(f"Error checking models: {e}")
        return False


def get_fallback_model() -> Optional[str]:
    """Get first available model as fallback."""
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


def rank_articles(articles: List[Dict]) -> List[Dict]:
    """Simple ranking based on keywords and recency."""
    keywords = ['AI', 'GPT', 'LLM', 'breakthrough', 'release', 'launch', 'announced']

    for article in articles:
        score = 0
        title_lower = article['title'].lower()

        for keyword in keywords:
            if keyword.lower() in title_lower:
                score += 2

        if is_recent(article, hours=24):
            score += 3

        article['rank_score'] = score

    return sorted(articles, key=lambda x: x.get('rank_score', 0), reverse=True)


def load_prompt_template(prompt_file: Path) -> str:
    """Load prompt template from disk."""
    try:
        return prompt_file.read_text(encoding='utf-8')
    except FileNotFoundError:
        logger.warning(f"Prompt template not found: {prompt_file}")
        return ""


def build_prompt(template: str, articles: List[Dict]) -> str:
    """Build LLM prompt from template."""
    today = datetime.now().strftime("%B %d, %Y")

    articles_text = ""
    for i, article in enumerate(articles, 1):
        articles_text += f"\n{i}. **{article['title']}**\n"
        articles_text += f"   - Source: {article['source']}\n"
        articles_text += f"   - Category: {article['category']}\n"
        articles_text += f"   - Link: {article['link']}\n"
        articles_text += f"   - Preview: {truncate_text(article['summary'], 300)}\n"

    if not template:
        template = (
            "You are a tech news curator creating a daily brief for {date}.\n\n"
            "IMPORTANT RULES:\n"
            "- Each article should appear ONLY ONCE in your summary\n"
            "- Do NOT repeat or duplicate any article\n"
            "- Be concise - 1-2 sentences per article maximum\n\n"
            "Your task:\n"
            "1. Group articles by theme (AI/ML, Tech Industry, Ethics, etc.)\n"
            "2. For each article, briefly explain what happened and why it matters\n"
            "3. Use markdown headers (##) and bullet points\n"
            "4. Include the article link for each item\n\n"
            "There are exactly {articles_count} articles below. Your summary should cover each one ONCE.\n\n"
            "Articles:\n{articles_text}\n\n"
            "Format as clean Markdown. Remember: NO DUPLICATES.\n"
        )

    return template.format(
        date=today,
        articles_count=len(articles),
        articles_text=articles_text
    )


def validate_summary(summary: str) -> None:
    """Warn if summary does not match expected structure."""
    if "##" not in summary:
        logger.warning("Summary missing markdown headers (##).")
    if "- " not in summary:
        logger.warning("Summary missing bullet points.")


def summarize_articles(articles: List[Dict], model: str, prompt_file: Path) -> str:
    """Send articles to LLM for summarization."""
    logger.info("🤖 Summarizing with AI...\n")

    ranked_articles = rank_articles(articles)
    template = load_prompt_template(prompt_file)
    prompt = build_prompt(template, ranked_articles)

    try:
        response = ollama.chat(
            model=model,
            messages=[{
                'role': 'user',
                'content': prompt
            }]
        )
        summary = response['message']['content']
        validate_summary(summary)
        logger.info("✓ Summary generated\n")
        return summary
    except Exception as e:
        logger.error(f"✗ Error calling LLM: {e}")
        return "Error generating summary. Please check if the model is available."
