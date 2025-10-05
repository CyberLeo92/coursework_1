from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv

from src.logger import setup_logging

# Базовые пути/логгер
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
EXCEL_PATH = DATA_DIR / "operations.xlsx"
LOG_PATH = ROOT / "log" / "utils.log"
logger = setup_logging("utils", LOG_PATH)

# .env
load_dotenv()  # ожидаем .env в корне проекта
API_KEY_EXCHANGE = os.getenv("API_KEY_exchange", "")
API_KEY_SP = os.getenv("API_KEY_sp", "")


def greetings(now: datetime | None = None) -> str:
    """Возвращает приветствие по локальному времени."""
    now = now or datetime.now()
    h = now.hour
    if 0 <= h < 6:
        return "Доброй ночи"
    if 6 <= h < 12:
        return "Доброе утро"
    if 12 <= h < 18:
        return "Добрый день"
    return "Добрый вечер"


def _load_transactions_df() -> pd.DataFrame:
    """
    Читает Excel (.xlsx) с транзакциями и нормализует ключевые столбцы.
    Требуется openpyxl. Ищет файл под именами operations.xlsx или operation.xlsx.
    """
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Не найден {EXCEL_PATH.name} в {DATA_DIR}")
    df = pd.read_excel(EXCEL_PATH)  # openpyxl уже установлен
    # приведение типов как раньше
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True, errors="coerce")
    for col in ("Сумма платежа", "Сумма операции"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "Номер карты" in df.columns:
        df["Номер карты"] = df["Номер карты"].astype(str)
    return df


def user_transactions(date: pd.Timestamp | datetime) -> list[dict]:
    """
    Возвращает транзакции за период с 1-го числа месяца по указанную дату (включительно).
    """
    date = pd.to_datetime(date)
    start = date.replace(day=1)
    df = _load_transactions_df()

    if "Дата операции" not in df.columns:
        logger.warning("В данных отсутствует столбец 'Дата операции'")
        return []

    df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True, errors="coerce")

    mask = (df["Дата операции"] >= start) & (df["Дата операции"] <= date)
    return df.loc[mask].to_dict("records")


def max_five_transactions(date: pd.Timestamp | datetime) -> List[Dict[str, Any]]:
    """Топ-5 транзакций за период по модулю суммы платежа/операции (в убывании)."""
    tx = user_transactions(date)
    if not tx:
        return []
    df = pd.DataFrame(tx)
    col = "Сумма платежа" if "Сумма платежа" in df.columns else "Сумма операции"

    # аккуратные поля под ТЗ: дата/сумма/категория/описание
    df["_abs"] = df[col].abs()
    df_sorted = df.sort_values("_abs", ascending=False, kind="mergesort").head(5)

    out = []
    for _, row in df_sorted.iterrows():
        # форматируем дату как 'DD.MM.YYYY'
        date_str = pd.to_datetime(row["Дата операции"]).strftime("%d.%m.%Y") if pd.notna(row["Дата операции"]) else ""
        out.append(
            {
                "date": date_str,
                "amount": float(row[col]),
                "category": row.get("Категория"),
                "description": row.get("Описание"),
            }
        )
    return out


def exchange_rate(currencies: list[str] | None = None, quote: str = "RUB") -> List[float]:
    """
    Возвращает курсы заданных валют к quote (по умолчанию к RUB).
    Реализовано так, чтобы удобно мокать requests в тестах.
    """
    currencies = currencies or ["USD", "EUR"]
    rates: list[float] = []

    for base in currencies:
        try:
            url = f"https://api.exchangerate.host/convert?from={base}&to={quote}"
            params = {"api_key": API_KEY_EXCHANGE} if API_KEY_EXCHANGE else {}
            resp = requests.get(url, params=params, timeout=5)

            # Проверка статуса
            if resp.status_code != 200:
                logger.warning(f"API вернуло статус {resp.status_code} для {base}")
                rates.append(float("nan"))
                continue

            # Проверка содержимого
            if not resp.text.strip():
                logger.warning(f"Пустой ответ от API для {base}")
                rates.append(float("nan"))
                continue

            data = resp.json()

            if "result" in data and isinstance(data["result"], (int, float)):
                rate = float(data["result"])
            else:
                rates_map = data.get("rates", {})
                rate = float(next(iter(rates_map.values()))) if rates_map else float("nan")
            rates.append(rate)

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса для {base}: {e}")
            rates.append(float("nan"))
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Ошибка парсинга JSON для {base}: {e}")
            rates.append(float("nan"))

    logger.info("Курсы %s к %s: %s", currencies, quote, rates)
    return rates


def get_price_sp500(tickers: list[str] | None = None) -> list[str]:
    """
    Возвращает список строк вида 'AAPL:150.12' для заданных тикеров.
    """
    tickers = tickers or ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]
    prices: list[str] = []
    for t in tickers:
        try:
            resp = requests.get(
                "https://api.twelvedata.com/price",
                params={"symbol": t, **({"apikey": API_KEY_SP} if API_KEY_SP else {})},
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            price = data.get("price")
            # иногда приходит строкой — приведём
            price = float(price) if price is not None else None
            prices.append(f"{t}:{price}")
        except Exception as e:
            logger.warning("Не удалось получить цену %s: %s", t, e)
            prices.append(f"{t}:None")
    return prices
