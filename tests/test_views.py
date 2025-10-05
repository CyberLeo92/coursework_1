from __future__ import annotations

import src.utils as utils
from src.views import website


def test_website_tuple_and_cards_clean(monkeypatch, patch_loader):
    # Мокаем сетевые функции, чтоб не ходить в интернет
    monkeypatch.setattr(utils, "exchange_rate", lambda *a, **k: [73.21, 87.08])
    monkeypatch.setattr(utils, "get_price_sp500", lambda *a, **k: ["AAPL:150.12", "MSFT:296.71"])

    greet, cards, top, currency, stocks = website("2020-05-20 12:00:00")

    assert isinstance(greet, str)
    assert isinstance(cards, list)
    assert isinstance(top, list)
    assert currency == [73.21, 87.08]
    assert stocks == ["AAPL:150.12", "MSFT:296.71"]

    # Карточки: только расходы, суммы положительные
    if cards:  # в зависимости от данных может быть пусто
        for c in cards:
            assert "last_digits" in c and len(c["last_digits"]) == 4
            assert c["total_spent"] >= 0
            # кэшбэк = 1% от суммы
            assert round(c["cashback"], 2) == round(c["total_spent"] / 100, 2)
