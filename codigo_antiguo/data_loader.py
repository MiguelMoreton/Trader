from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pandas as pd
import yfinance as yf


def parse_tickers(tickers_input: str) -> List[str]:
    tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
    if not tickers:
        raise ValueError('Debes introducir al menos un ticker.')
    return tickers


def download_ticker_data(
    tickers: List[str],
    base_dir: str | Path = 'data',
    days: int = 365,
) -> Dict[str, pd.DataFrame]:
    end = datetime.now()
    start = end - timedelta(days=days)

    base_path = Path(base_dir)
    base_path.mkdir(exist_ok=True)

    precios_por_ticker: Dict[str, pd.DataFrame] = {}

    for ticker in tickers:
        raw = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        if raw.empty:
            print(f'No se encontraron datos para {ticker}.')
            continue

        if isinstance(raw.columns, pd.MultiIndex):
            close_series = raw.xs('Close', axis=1, level=0).iloc[:, 0]
        else:
            close_series = raw['Close']

        df = close_series.reset_index()
        df.columns = ['Date', 'Close']
        df['Date'] = pd.to_datetime(df['Date'])

        ticker_dir = base_path / ticker.replace('/', '_')
        ticker_dir.mkdir(parents=True, exist_ok=True)
        output_file = ticker_dir / f'{ticker}_precios.csv'
        df.to_csv(output_file, index=False)

        precios_por_ticker[ticker] = df
        print(f'{ticker}: datos guardados en {output_file}')

    if not precios_por_ticker:
        raise ValueError('No se pudo descargar informacion para los tickers proporcionados.')

    return precios_por_ticker


def load_from_prompt(days: int = 365) -> Dict[str, pd.DataFrame]:
    tickers_input = input('Introduce uno o varios tickers separados por coma: ').strip()
    tickers = parse_tickers(tickers_input)
    return download_ticker_data(tickers, days=days)
