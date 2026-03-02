from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import Literal, List

import pandas as pd
import requests


IndexName = Literal["IBEX35", "SP500", "NASDAQ100"]


@dataclass(frozen=True)
class IndexConfig:
    name: str
    url: str
    table_selector: str  # "first" o "contains:<colname>"
    ticker_column: str
    postprocess: str  # "none" | "sp500" | "ibex" | "nasdaq100"


def _fetch_html(url: str, timeout: int = 30) -> str:
    """
    Descarga HTML con headers para evitar bloqueos 403 / bots.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text


def _read_tables_from_html(html: str) -> list[pd.DataFrame]:
    """
    Parsea tablas HTML de forma robusta (evita que lxml intente leer la URL directamente).
    """
    return pd.read_html(StringIO(html))


def _select_table(tables: list[pd.DataFrame], selector: str) -> pd.DataFrame:
    """
    selector:
      - "first"
      - "contains:<COLUMN_NAME>"  -> elige la primera tabla que tenga esa columna
    """
    if selector == "first":
        if not tables:
            raise RuntimeError("No se encontraron tablas en el HTML.")
        return tables[0]

    if selector.startswith("contains:"):
        col = selector.split("contains:", 1)[1]
        for t in tables:
            if col in t.columns:
                return t
        raise RuntimeError(f"No se encontró ninguna tabla con la columna '{col}'.")

    raise ValueError(f"Selector de tabla no soportado: {selector}")


def _normalize_tickers(raw: List[str], kind: str) -> List[str]:
    """
    Normaliza tickers para yfinance.
    """
    tickers = [str(x).strip().upper() for x in raw if str(x).strip() and str(x).strip().upper() != "NAN"]

    if kind == "sp500":
        # Wikipedia usa BRK.B / BF.B pero Yahoo/yfinance usa BRK-B / BF-B
        tickers = [t.replace(".", "-") for t in tickers]
        return tickers

    if kind == "ibex":
        # Normalmente vienen ya como XXX.MC. Filtra posibles filas basura.
        tickers = [t for t in tickers if t.endswith(".MC")]
        return tickers

    if kind == "nasdaq100":
        # NASDAQ-100: normalmente símbolos US. Algunos podrían traer '.' (raro), normalizamos igual.
        tickers = [t.replace(".", "-") for t in tickers]
        return tickers

    return tickers


# Configs (fuente: Wikipedia, estable para read_html)
_CONFIG: dict[IndexName, IndexConfig] = {
    "IBEX35": IndexConfig(
        name="IBEX 35",
        url="https://en.wikipedia.org/wiki/IBEX_35",
        table_selector="contains:Ticker",
        ticker_column="Ticker",
        postprocess="ibex",
    ),
    "SP500": IndexConfig(
        name="S&P 500",
        url="https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        table_selector="first",  # la 1ª tabla suele ser la lista principal
        ticker_column="Symbol",
        postprocess="sp500",
    ),
    "NASDAQ100": IndexConfig(
        name="NASDAQ-100",
        url="https://en.wikipedia.org/wiki/Nasdaq-100",
        table_selector="contains:Ticker",
        ticker_column="Ticker",
        postprocess="nasdaq100",
    ),
}


def get_index_tickers(index: IndexName) -> List[str]:
    """
    Devuelve la lista de tickers del índice elegido: IBEX35, SP500 o NASDAQ100.
    Estrategia única para todos: requests+headers -> pd.read_html(StringIO) -> normalización.
    """
    cfg = _CONFIG.get(index)
    if cfg is None:
        raise ValueError("Índice no soportado. Usa 'IBEX35', 'SP500' o 'NASDAQ100'.")

    html = _fetch_html(cfg.url)
    tables = _read_tables_from_html(html)
    table = _select_table(tables, cfg.table_selector)

    if cfg.ticker_column not in table.columns:
        raise RuntimeError(
            f"Tabla encontrada pero no tiene la columna '{cfg.ticker_column}'. "
            f"Columnas disponibles: {list(table.columns)}"
        )

    raw = table[cfg.ticker_column].tolist()
    tickers = _normalize_tickers(raw, cfg.postprocess)

    if not tickers:
        raise RuntimeError(f"No se pudieron extraer tickers para {cfg.name}.")

    return tickers


def get_ibex35_tickers() -> List[str]:
    return get_index_tickers("IBEX35")


def get_sp500_tickers() -> List[str]:
    return get_index_tickers("SP500")


def get_nasdaq100_tickers() -> List[str]:
    return get_index_tickers("NASDAQ100")
