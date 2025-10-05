from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

import src.utils as utils  # <— ключевое отличие: импортируем модуль
from src.logger import setup_logging

# Логгер для views
ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "log" / "views.log"
logger = setup_logging("views", LOG_PATH)


def _nan_to_none(seq: List[float]) -> List[Optional[float]]:
    """Заменяет float('nan') на None, чтобы JSON был валидным."""
    out: List[Optional[float]] = []
    for x in seq:
        if isinstance(x, float) and math.isnan(x):
            out.append(None)
        else:
            out.append(x)
    return out


def website(dt_input: Union[str, pd.Timestamp]) -> Tuple[
    str,
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Optional[float]],
    List[str],
]:
    """
    Главная страница: возвращает (greeting, cards, top_transactions, currency_rates, stock_prices).
    """
    date = pd.to_datetime(dt_input)

    greet = utils.greetings()

    tx = utils.user_transactions(date)

    # Карточки (только расходы)
    cards: List[Dict[str, Any]] = []
    df = pd.DataFrame(tx)
    if not df.empty:
        num_col = "Номер карты" if "Номер карты" in df.columns else None
        amt_col = (
            "Сумма платежа"
            if "Сумма платежа" in df.columns
            else ("Сумма операции" if "Сумма операции" in df.columns else None)
        )
        if num_col and amt_col:
            cleaned = df[num_col].astype(str).str.replace(r"\D", "", regex=True)
            df = df.assign(
                clean_card=cleaned.where(cleaned.str.len() > 0),
                amount=pd.to_numeric(df[amt_col], errors="coerce"),
            )
            expenses = df[df["amount"] < 0].copy()
            if not expenses.empty:
                expenses["last4"] = expenses["clean_card"].str[-4:]
                expenses = expenses.dropna(subset=["last4"])
                grouped = (-expenses.groupby("last4")["amount"].sum()).round(2)
                for last4, total_spent in grouped.items():
                    cashback = round(float(total_spent) / 100, 2)
                    cards.append(
                        {
                            "last_digits": str(last4),
                            "total_spent": float(total_spent),
                            "cashback": float(cashback),
                        }
                    )
                cards.sort(key=lambda x: x["total_spent"], reverse=True)

    # Топ-5
    top = utils.max_five_transactions(date)

    # Курсы валют
    currency = _nan_to_none(utils.exchange_rate())

    # Акции
    stocks = utils.get_price_sp500()

    logger.info("website(%s) сформирован", date)
    return greet, cards, top, currency, stocks
