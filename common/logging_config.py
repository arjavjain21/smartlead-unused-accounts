import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(log_path: str) -> logging.Logger:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logger = logging.getLogger("smartlead_toolkit")
    logger.setLevel(logging.INFO)
    # Avoid duplicate handlers if called multiple times
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        ch.setFormatter(ch_formatter)
        logger.addHandler(ch)

        fh = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
        fh.setLevel(logging.INFO)
        fh_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh.setFormatter(fh_formatter)
        logger.addHandler(fh)
    return logger