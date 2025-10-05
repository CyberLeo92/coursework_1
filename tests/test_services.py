from __future__ import annotations

import pytest

from src.services import find_person_transfers, find_phone_transactions, investment_bank, simple_search


def test_simple_search_ok():
    tx = [
        {"Описание": "Магнит у дома", "Категория": "Супермаркеты"},
        {"Описание": "Яндекс Такси", "Категория": "Транспорт"},
    ]
    res = simple_search("магнит", tx)
    assert len(res) == 1 and res[0]["Категория"] == "Супермаркеты"


def test_simple_search_bad_types():
    with pytest.raises(TypeError) as ei:
        simple_search(123, "not a list")
    assert "Неверный тип данных" in str(ei.value)


def test_investment_bank_basic():
    # В этой функции по нашей реализации расходы должны быть положительными
    # (рассматриваем оригинальные суммы расходов как положительные).
    tx = [
        {"Дата операции": "2020-05-01", "Сумма операции": 1712},  # → округление до 1750 -> 38
        {"Дата операции": "2020-05-15", "Сумма операции": 20},  # → до 50 -> 30
        {"Дата операции": "2020-04-30", "Сумма операции": 99},  # месяц не тот -> игнор
        {"Дата операции": "2020-05-20", "Сумма операции": 100},  # без округления -> 0
    ]
    total = investment_bank("2020-05", tx, limit=50)
    assert total == pytest.approx(68.0, abs=1e-6)


def test_find_phone_transactions():
    tx = [
        {"Описание": "Я МТС +7 921 11-22-33"},
        {"Описание": "Без телефона"},
        {"Описание": "Тинькофф Мобайл +7 995 555-55-55"},
    ]
    out = find_phone_transactions(tx)
    assert len(out) == 2


def test_find_person_transfers():
    tx = [
        {"Категория": "Переводы", "Описание": "Валерий А."},
        {"Категория": "Переводы", "Описание": "Сергей З."},
        {"Категория": "Супермаркеты", "Описание": "Магнит"},
        {"Категория": "Переводы", "Описание": "Без ФИО"},
    ]
    out = find_person_transfers(tx)
    assert len(out) == 2
