import yfinance as yf

import yfinance as yf
from datetime import datetime

def get_live_prices(tickers):
    """
    Devuelve un diccionario con:
        - precio actual
        - hora del último dato de mercado
        - hora local de consulta
    
    :param tickers: lista de strings con los tickers (ej: ['AAPL', 'MSFT'])
    :return: dict {ticker: {price, market_time, query_time}}
    """
    
    prices = {}
    query_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d", interval="1m")
            
            if not data.empty:
                last_price = data['Close'].iloc[-1]
                market_time = data.index[-1].strftime("%Y-%m-%d %H:%M:%S")
                
                prices[ticker] = {
                    "price": round(last_price, 2),
                    "market_time": market_time,
                    "query_time": query_time
                }
            else:
                prices[ticker] = None
                
        except Exception as e:
            prices[ticker] = f"Error: {e}"
    
    return prices