import logging
import sys


def setup_logging():
    """
    Configure application-wide logging.
    """

    logger = logging.getLogger()

    logger.setLevel(logging.INFO)

    if logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)


def get_logger(name: str):
    """
    Return a logger for the given module.
    """

    return logging.getLogger(name)