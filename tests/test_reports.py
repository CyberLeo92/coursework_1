from __future__ import annotations

from pathlib import Path

import pandas as pd

import src.reports as reports


def test_spending_by_category_saves_file(tmp_path: Path):
    # Перекидываем каталог вывода отчётов на временный
    old_dir = reports.DATA_DIR
    reports.DATA_DIR = tmp_path
    try:
        df = pd.DataFrame(
            [
                {"Дата операции": "01.05.2020", "Категория": "Супермаркеты", "Сумма операции": -100},
                {
                    "Дата операции": "20.05.2020",
                    "Категория": "Супермаркеты",
                    "Сумма операция": -50,
                },  # опечатка — игнор
                {
                    "Дата операции": "15.04.2020",
                    "Категория": "Супермаркеты",
                    "Сумма операции": -200,
                },  # стар. месяц — игнор
                {
                    "Дата операции": "10.05.2020",
                    "Категория": "Топливо",
                    "Сумма операции": -300,
                },  # другая категория — игнор
            ]
        )
        out = reports.spending_by_category(df, "Супермаркеты", date="20.05.2020")

        # сам отчёт вернул список словарей
        assert isinstance(out, list)
        # файл создан
        files = list(tmp_path.glob("report_spending_by_category_*.json"))
        assert len(files) == 1
    finally:
        reports.DATA_DIR = old_dir


def test_spending_by_weekday_and_workday(tmp_path: Path):
    old_dir = reports.DATA_DIR
    reports.DATA_DIR = tmp_path
    try:
        df = pd.DataFrame(
            [
                {"Дата операции": "01.05.2020", "Категория": "Супермаркеты", "Сумма операции": -100},
                {"Дата операции": "02.05.2020", "Категория": "Супермаркеты", "Сумма операция": -50},
                {"Дата операции": "03.05.2020", "Категория": "Супермаркеты", "Сумма операция": -200},
                {"Дата операции": "04.05.2020", "Категория": "Супермаркеты", "Сумма операция": -300},
            ]
        )
        wd = reports.spending_by_weekday(df, date="20.05.2020")
        wb = reports.spending_by_workday(df, date="20.05.2020")

        assert isinstance(wd, list) and all("weekday" in x and "avg_amount" in x for x in wd)
        assert isinstance(wb, list)
        # два ключа — workday/weekend
        types = {x["type"] for x in wb}
        assert types.issubset({"workday", "weekend"})
        # файлы тоже должны появиться
        assert (tmp_path / "spending_by_weekday.json").exists()
        assert (tmp_path / "spending_by_workday.json").exists()
    finally:
        reports.DATA_DIR = old_dir
