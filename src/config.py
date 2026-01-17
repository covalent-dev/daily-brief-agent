import logging
from pathlib import Path
from typing import Dict
import yaml

logger = logging.getLogger(__name__)


def load_config(config_file: Path) -> Dict:
    """Load RSS feeds from config file."""
    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_file}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing config file: {e}")
        raise


def ensure_output_dir(output_dir: Path) -> None:
    """Create output directory if it doesn't exist."""
    output_dir.mkdir(exist_ok=True)
    logger.info(f"Output directory ready: {output_dir}")
