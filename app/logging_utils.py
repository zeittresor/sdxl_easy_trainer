import logging
from pathlib import Path
from .constants import LOG_DIR_NAME

def setup_logging(base_dir: Path) -> Path:
    log_dir = base_dir / LOG_DIR_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return log_file
