"""
Logging configuration for the trading bot.
Sets up both file and console handlers with structured formatting.
"""

import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_dir: str = "logs", log_level: int = logging.DEBUG) -> logging.Logger:
    """
    Configure logging with file rotation and console output.

    Args:
        log_dir: Directory to store log files.
        log_level: Logging level (default DEBUG for file, INFO for console).

    Returns:
        Configured root logger.
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # --- File handler (all levels, rotated) ---
    file_handler = logging.handlers.RotatingFileHandler(
        filename=Path(log_dir) / "trading_bot.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # --- Console handler (INFO and above) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger
