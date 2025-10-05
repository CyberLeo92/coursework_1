from __future__ import annotations

from datetime import datetime
# Логгер для main
from pathlib import Path

import pandas as pd

from src.logger import setup_logging
from src.reports import spending_by_category
from src.views import website

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "log" / "main.log"
logger = setup_logging("main", LOG_PATH)


def main() -> None:
    """
    Демонстрация всех реализованных функций без интерактива.
    Здесь можно «склеить» результат для ручной проверки/печати,
    но сам модуль остаётся чистым для импорта и тестов.
    """
    # 1) Страница «Главная»
    greet, cards, top, currency, stocks = website(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )  # для проверки можно заменить на website("2020-05-20 12:00:00")
    logger.info("Greeting: %s", greet)
    logger.info("Cards: %s", cards)
    logger.info("Top-5: %s", top)
    logger.info("Currency: %s", currency)
    logger.info("Stocks: %s", stocks)

    # 2) Отчёт — пример (если есть DataFrame транзакций)
    # Для демонстрации: пустой df — отчёт вернёт пустой список и файл JSON
    df = pd.DataFrame(columns=["Дата операции", "Категория", "Сумма операции", "Сумма платежа"])
    _ = spending_by_category(df, category="Супермаркеты", date=datetime.now().strftime("%d.%m.%Y"))


if __name__ == "__main__":
    main()
