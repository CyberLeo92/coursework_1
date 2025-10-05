from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    name: str,
    path: str | Path,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Создаёт именованный логгер с выводом в консоль и в файл.

    :param name: имя логгера (например, "services" / "reports")
    :param path: путь к .log файлу
    :param level: уровень логирования
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # не дублируем хендлеры

    logger.setLevel(level)

    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Консоль
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Файл
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
