from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from src.logger import setup_logging

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "log" / "services.log"
logger = setup_logging("services", LOG_PATH)


def _ensure_transactions(transactions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(transactions, Iterable):
        raise TypeError("Неверный тип данных")
    return list(transactions)


def simple_search(search_str: str, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Простой поиск по подстроке в описании/категории.
    Требования тестов: при неверных типах — TypeError("Неверный тип данных").
    """
    if not isinstance(search_str, str) or not isinstance(transactions, list):
        raise TypeError("Неверный тип данных")

    q = search_str.lower()
    result: list[dict] = []
    for tx in transactions:
        desc = str(tx.get("Описание") or tx.get("description") or "").lower()
        cat = str(tx.get("Категория") or tx.get("category") or "").lower()
        if q in desc or q in cat:
            result.append(tx)
    logger.info("simple_search('%s') -> %d", search_str, len(result))
    return result


def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    """
    Инвесткопилка: округление трат до указанного порога (10/50/100).
    month: 'YYYY-MM'
    """
    if not isinstance(month, str) or not isinstance(transactions, list) or not isinstance(limit, int):
        raise TypeError("Неверный тип данных")

    # Месяц-границы
    dt = datetime.strptime(month, "%Y-%m")
    start = dt.replace(day=1)
    if dt.month == 12:
        end = dt.replace(year=dt.year + 1, month=1, day=1)
    else:
        end = dt.replace(month=dt.month + 1, day=1)

    total = 0.0
    for tx in transactions:
        # Берём сумму операции в оригинальной валюте (по ТЗ)
        amount = tx.get("Сумма операции") or tx.get("amount")
        date_str = tx.get("Дата операции") or tx.get("date")
        if amount is None or date_str is None:
            continue
        try:
            amount = float(amount)
            d = datetime.strptime(str(date_str), "%Y-%m-%d")
        except Exception:
            continue
        if not (start <= d < end) or amount <= 0:
            continue
        # округляем вверх к ближайшему шагу limit
        remainder = amount % limit
        delta = (limit - remainder) if remainder else 0
        total += 0 if delta == 0 else delta
    logger.info("investment_bank(%s) -> %.2f", month, total)
    return round(total, 2)


_PHONE_RE = re.compile(
    r"(?:\+7|8)\s?\(?\d{3}\)?[\s-]?\d{2,3}[\s-]?\d{2}[\s-]?\d{2}",
    flags=re.UNICODE,
)


def find_phone_transactions(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ищет транзакции, где в описании есть российский мобильный номер."""
    txs = _ensure_transactions(transactions)
    result = []
    for tx in txs:
        desc = str(tx.get("Описание") or tx.get("description") or "")
        if _PHONE_RE.search(desc):
            result.append(tx)
    logger.info("find_phone_transactions -> %d", len(result))
    return result


_PERSON_TRANSFER_RE = re.compile(
    r"\b([А-ЯЁ][а-яё]+)\s+[А-ЯЁ]\.",
    flags=re.UNICODE,
)


def find_person_transfers(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Поиск переводов физлицам:
    - Категория == 'Переводы'
    - В описании 'Имя И.' (первая буква фамилии и точка)
    """
    txs = _ensure_transactions(transactions)
    result = []
    for tx in txs:
        category = str(tx.get("Категория") or tx.get("category") or "")
        desc = str(tx.get("Описание") or tx.get("description") or "")
        if category == "Переводы" and _PERSON_TRANSFER_RE.search(desc):
            result.append(tx)
    logger.info("find_person_transfers -> %d", len(result))
    return result
