"""
logging_config.py — Set up logging for the scraper framework.

Call  setup_logging()  at the start of any pipeline script.
Logs go to both the console and a rotating log file.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"


def setup_logging(level: int = logging.INFO, log_file: str = "scrape.log") -> None:
    """
    Configure logging for the project.

    - Console output: INFO and above, compact format
    - File output: DEBUG and above, detailed format with timestamps
    """
    LOG_DIR.mkdir(exist_ok=True)

    # Root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console_fmt = logging.Formatter("%(levelname)-8s %(name)s - %(message)s")
    console.setFormatter(console_fmt)
    root.addHandler(console)

    # File handler
    file_handler = logging.FileHandler(LOG_DIR / log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    root.addHandler(file_handler)

    logging.info("Logging initialized — console=%s, file=%s",
                 logging.getLevelName(level), LOG_DIR / log_file)
