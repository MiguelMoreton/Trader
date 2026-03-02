import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta


class DataLoader:

    def __init__(self):
        pass

    def load_data(self, tickers: list, duration_days) -> pd.DataFrame:
        """
        Descarga datos históricos para una lista de tickers.
        Devuelve DataFrame con columnas:
        Date, Ticker, Close, Return
        """
        end = datetime.now()
        start = end - timedelta(days=duration_days)

        print("📥 Descargando datos...")
        data = yf.download(
            tickers,
            start=start,
            end=end,
            progress=False
        )['Close']

        df = data.stack().reset_index()
        df.columns = ['Date', 'Ticker', 'Close']
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(['Date', 'Ticker'])

        df['Return'] = df.groupby('Ticker')['Close'].pct_change() * 100
        return df