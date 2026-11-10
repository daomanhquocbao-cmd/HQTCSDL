"""Cấu hình logging thống nhất cho toàn app."""
import logging

from core.config import settings


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
