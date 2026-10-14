import logging
from pathlib import Path

APP_NAME = "InsightAI"
APP_SUBTITLE = "Intelligent Text Analytics & Context Understanding"
SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
TOPIC_MODEL = "facebook/bart-large-mnli"
TOPICS = ["Technology", "Business", "Education", "Healthcare", "Entertainment"]
MAX_TEXT_CHARS = 4000
DB_PATH = "insightai.db"
LOG_DIR = "logs"
REPORT_DIR = "reports"
BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / LOG_DIR / "app.log"


def configure_logging():
    """Create the app log directory and set up a consistent file logger."""
    log_dir = BASE_DIR / LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("insightai")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(file_handler)

    return logger
