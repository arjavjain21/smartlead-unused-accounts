import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logging(log_path: str) -> logging.Logger:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logger = logging.getLogger("smartlead_toolkit")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    if not any(isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler) for handler in logger.handlers):
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    target_log_path = os.path.abspath(log_path)
    for handler in list(logger.handlers):
        if isinstance(handler, RotatingFileHandler) and os.path.abspath(handler.baseFilename) != target_log_path:
            logger.removeHandler(handler)
            handler.close()

    if not any(isinstance(handler, RotatingFileHandler) and os.path.abspath(handler.baseFilename) == target_log_path for handler in logger.handlers):
        fh = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
