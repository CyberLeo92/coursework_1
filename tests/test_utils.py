from __future__ import annotations

import math

import pandas as pd
import pytest
import requests

import src.utils as utils


def test_exchange_rate_ok(requests_stub):
    # два запроса: USD->RUB и EUR->RUB
    requests_stub.set_side_effect(
        [
            # exchangerate.host/convert -> {"result": ...}
            type(
                "R",
                (),
                {
                    "status_code": 200,
                    "json": lambda self: {"result": 73.21},
                    "text": "OK",
                    "raise_for_status": lambda self: None,
                },
            )(),
            type(
                "R",
                (),
                {
                    "status_code": 200,
                    "json": lambda self: {"result": 87.08},
                    "text": "OK",
                    "raise_for_status": lambda self: None,
                },
            )(),
        ]
    )
    rates = utils.exchange_rate(["USD", "EUR"], "RUB")
    assert rates == [73.21, 87.08]


def test_exchange_rate_network_error(requests_stub):
    # имитация 500 -> NaN
    requests_stub.set_side_effect(
        [
            type(
                "R",
                (),
                {
                    "status_code": 500,
                    "json": lambda self: {},
                    "text": "",
                    "raise_for_status": lambda self: (_ for _ in ()).throw(Exception("HTTP 500")),
                },
            )(),
            type(
                "R",
                (),
                {
                    "status_code": 500,
                    "json": lambda self: {},
                    "text": "",
                    "raise_for_status": lambda self: (_ for _ in ()).throw(Exception("HTTP 500")),
                },
            )(),
        ]
    )
    rates = utils.exchange_rate(["USD", "EUR"], "RUB")
    assert all(isinstance(x, float) and math.isnan(x) for x in rates)


def test_get_price_sp500_ok(monkeypatch):
    # отдадим всегда {"price": "150.12"}
    def _get(*args, **kwargs):
        class R:
            status_code = 200

            def json(self):
                return {"price": "150.12"}

            def raise_for_status(self):
                return None

        return R()

    import requests

    monkeypatch.setattr(requests, "get", _get)
    out = utils.get_price_sp500(["AAPL", "MSFT"])
    assert out == ["AAPL:150.12", "MSFT:150.12"]


def test_user_transactions_filters_by_month(patch_loader):
    # дата 20 мая — берём 01.05..20.05
    res = utils.user_transactions(pd.Timestamp("2020-05-20 12:00:00"))
    # все строки в фикстуре в мае — ожидаем >0
    assert len(res) > 0
    # убедимся, что даты не выходят за предел 20.05
    for r in res:
        assert r["Дата операции"] <= pd.Timestamp("2020-05-20 12:00:00")


def test_max_five_transactions_returns_list_of_dicts(patch_loader):
    out = utils.max_five_transactions(pd.Timestamp("2020-05-20 12:00:00"))
    assert isinstance(out, list)
    assert all(isinstance(x, dict) for x in out)
    # не больше 5
    assert len(out) <= 5
    # ключи ожидаемы
    keys = {"date", "amount", "category", "description"}
    assert keys.issubset(out[0].keys())


def test__load_transactions_df_reads_and_normalizes(tmp_path, monkeypatch):
    """Читает реальный .xlsx и приводит типы: дата -> datetime, суммы -> float, номер карты -> str."""
    # готовим временный Excel
    df_in = pd.DataFrame(
        {
            "Дата операции": ["05.05.2020", "03.05.2020"],  # строки
            "Сумма платежа": ["100", "200"],  # строки-числа
            "Сумма операции": ["100", "200"],
            "Номер карты": [7197, 4556],  # числа
        }
    )
    xlsx_path = tmp_path / "operations.xlsx"
    df_in.to_excel(xlsx_path, index=False)

    # подменяем путь в utils
    monkeypatch.setattr(utils, "EXCEL_PATH", xlsx_path)

    df = utils._load_transactions_df()
    # даты действительно datetime64
    assert pd.api.types.is_datetime64_any_dtype(df["Дата операции"])
    # суммы стали числовыми
    assert df["Сумма платежа"].dtype.kind in "fi"
    assert df["Сумма операции"].dtype.kind in "fi"
    # номер карты теперь строка (для last4)
    assert isinstance(df["Номер карты"].iloc[0], str)


def test__load_transactions_df_missing_file(tmp_path, monkeypatch):
    """Покрываем ветку FileNotFoundError, когда файла нет."""
    monkeypatch.setattr(utils, "EXCEL_PATH", tmp_path / "operations.xlsx")  # не существует
    with pytest.raises(FileNotFoundError):
        utils._load_transactions_df()


def test_exchange_rate_uses_rates_map(requests_stub):
    """Курс приходит как {'rates': {'RUB': value}} — покрываем альтернативную ветку."""

    class R:
        status_code = 200
        text = "OK"

        def json(self):
            return {"rates": {"RUB": 91.23}}

        def raise_for_status(self):
            return None

    class R2:
        status_code = 200
        text = "OK"

        def json(self):
            return {"rates": {"RUB": 101.34}}

        def raise_for_status(self):
            return None

    requests_stub.set_side_effect([R(), R2()])
    rates = utils.exchange_rate(["USD", "EUR"], "RUB")
    assert rates == [91.23, 101.34]


def test_exchange_rate_empty_text_returns_nan(requests_stub):
    """Пустой ответ API -> добавляем NaN, покрываем соответствующую ветку."""

    class Empty:
        status_code = 200
        text = ""  # пусто

        def json(self):
            return {}

        def raise_for_status(self):
            return None

    requests_stub.set_side_effect([Empty(), Empty()])
    rates = utils.exchange_rate(["USD", "EUR"], "RUB")
    assert all(isinstance(x, float) and math.isnan(x) for x in rates)


def test_get_price_sp500_http_error(monkeypatch):
    """Ошибка HTTP в get_price_sp500 -> 'TICKER:None' для каждого тикера."""

    def _bad_get(*args, **kwargs):
        class R:
            def raise_for_status(self):
                raise Exception("HTTP 500")

            def json(self):
                return {}

        return R()

    monkeypatch.setattr(requests, "get", _bad_get)

    out = utils.get_price_sp500(["AAPL", "MSFT"])
    assert out == ["AAPL:None", "MSFT:None"]
