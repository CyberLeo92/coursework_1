from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

from src.logger import setup_logging

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LOG_PATH = ROOT / "log" / "reports.log"
logger = setup_logging("reports", LOG_PATH)


def save_report(filename: str | None = None) -> Callable:
    """
    Декоратор: сохраняет результат функции-отчёта в JSON-файл.
    - Без параметра: имя по умолчанию 'report_<func>_<YYYYmmdd_HHMMSS>.json'
    - С параметром: сохраняет в указанный filename (в папке data/)
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            name = filename or f"report_{func.__name__}_{datetime.now():%Y%m%d_%H%M%S}.json"
            out_path = DATA_DIR / name
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=_json_default)
            logger.info("Отчёт %s сохранён: %s", func.__name__, out_path)
            return result

        return wrapper

    return decorator


def _json_default(o: Any) -> str:
    if isinstance(o, (datetime,)):
        return o.isoformat()
    return str(o)


@save_report()  # без параметра — имя файла по умолчанию
def spending_by_category(
    transactions: pd.DataFrame,
    category: str,
    date: Optional[str] = None,
):
    """
    Возвращает записи по указанной категории за последние 3 месяца (включительно)
    от 'date' (формат 'DD.MM.YYYY'); при отсутствии 'date' — берём сегодня.
    Результат — список словарей, удобно использовать в JSON и для тестов.
    """
    if date is None:
        end_date = datetime.now().date()
    else:
        end_date = datetime.strptime(date, "%d.%m.%Y").date()

    start_date = end_date - timedelta(days=90)

    df = transactions.copy()
    # Нормализация дат
    if "Дата операции" in df.columns:
        dt = pd.to_datetime(df["Дата операции"], dayfirst=True, errors="coerce").dt.date
    else:
        raise ValueError("Ожидается столбец 'Дата операции' в датафрейме")

    mask = (df.get("Категория") == category) & (dt >= start_date) & (dt <= end_date)
    filtered = df.loc[mask].copy()
    return filtered.to_dict("records")


@save_report("spending_by_weekday.json")
def spending_by_weekday(transactions: pd.DataFrame, date: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Средние траты по дням недели за последние 3 месяца.
    Возвращаем список словарей [{'weekday': 'Mon', 'avg_amount': 123.45}, ...]
    """
    if date is None:
        end_date = datetime.now().date()
    else:
        end_date = datetime.strptime(date, "%d.%m.%Y").date()
    start_date = end_date - timedelta(days=90)

    df = transactions.copy()
    dt = pd.to_datetime(df["Дата операции"], dayfirst=True, errors="coerce")
    mask = (dt.dt.date >= start_date) & (dt.dt.date <= end_date)

    # Считаем расход: предполагаем, что положительные суммы — расход (или берём столбец "Сумма платежа")
    amount_col = "Сумма платежа" if "Сумма платежа" in df.columns else "Сумма операции"
    work = df.loc[mask, [amount_col]].copy()
    work["weekday"] = dt.loc[mask].dt.weekday

    grouped = work.groupby("weekday")[amount_col].mean().round(2)
    weekday_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return [{"weekday": weekday_map[i], "avg_amount": float(val)} for i, val in grouped.items()]


@save_report("spending_by_workday.json")
def spending_by_workday(transactions: pd.DataFrame, date: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Средние траты в рабочие/выходные за последние 3 месяца.
    Возвращаем [{'type': 'workday', 'avg_amount': ...}, {'type': 'weekend', 'avg_amount': ...}]
    """
    if date is None:
        end_date = datetime.now().date()
    else:
        end_date = datetime.strptime(date, "%d.%m.%Y").date()
    start_date = end_date - timedelta(days=90)

    df = transactions.copy()
    dt = pd.to_datetime(df["Дата операции"], dayfirst=True, errors="coerce")
    mask = (dt.dt.date >= start_date) & (dt.dt.date <= end_date)

    amount_col = "Сумма платежа" if "Сумма платежа" in df.columns else "Сумма операции"
    work = df.loc[mask, [amount_col]].copy()
    wday = dt.loc[mask].dt.weekday  # 0..6
    work["is_weekend"] = wday >= 5

    res = work.groupby("is_weekend")[amount_col].mean().round(2).rename(index={False: "workday", True: "weekend"})
    return [{"type": k, "avg_amount": float(v)} for k, v in res.items()]
