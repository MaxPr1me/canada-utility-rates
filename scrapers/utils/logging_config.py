"""
logging_config.py — Set up logging for the scraper framework.

Call  setup_logging()  at the start of any pipeline script.
Logs go to both the console and a rotating log file.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 3


def setup_logging(level: int = logging.INFO, log_file: str = "scrape.log") -> None:
    """
    Configure logging for the project.

    - Console output: INFO and above, compact format
    - File output: DEBUG and above, detailed format with timestamps; rotates at
      LOG_MAX_BYTES, keeping LOG_BACKUP_COUNT older files
    """
    LOG_DIR.mkdir(exist_ok=True)

    # Root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # pdfminer emits per-token DEBUG records that can grow the log file to gigabytes.
    for noisy in ("pdfminer", "pdfplumber", "urllib3", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    if any(getattr(h, "_setup_logging", False) for h in root.handlers):
        return

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console_fmt = logging.Formatter("%(levelname)-8s %(name)s - %(message)s")
    console.setFormatter(console_fmt)
    console._setup_logging = True
    root.addHandler(console)

    # File handler
    file_handler = RotatingFileHandler(LOG_DIR / log_file, maxBytes=LOG_MAX_BYTES,
                                       backupCount=LOG_BACKUP_COUNT, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    file_handler._setup_logging = True
    root.addHandler(file_handler)

    logging.info("Logging initialized — console=%s, file=%s",
                 logging.getLevelName(level), LOG_DIR / log_file)
