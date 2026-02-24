import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

print("🚀 BACKTEST 20 NASDAQ - 1000 días - 500€ cada una")

# 20 NASDAQ TOP
tickers = [
    # Top 25 NASDAQ 100 (Market Cap líderes 2026)
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AVGO', 'COST', 'NFLX',
    'ASML', 'AMD', 'CRM', 'ORCL', 'ADBE', 'TXN', 'AMAT', 'QCOM', 'INTC', 'NOW',
    'WMT', 'AMGN', 'KLAC', 'PANW', 'GILD',
    
    # 26-50: Tech/Semis/Cloud
    'MU', 'SNPS', 'CDNS', 'MRVL', 'CSX', 'NXPI', 'PCAR', 'ROP', 'REGN', 'VRTX',
    'ADSK', 'CCEP', 'MCHP', 'DDOG', 'KDP', 'TRI', 'TTWO', 'WDAY', 'CTAS', 'MRNA',
    
    # 51-75: Software/Health/Consumo
    'CSGP', 'FANG', 'MNST', 'ODFL', 'DXCM', 'TTD', 'CPRT', 'IDXX', 'XEL', 'FAST',
    'MELI', 'ZS', 'ANSS', 'TEAM', 'DLTR', 'SBUX', 'CTSH', 'EXC', 'BKR', 'MDLZ',
    
    # 76-100: Diversos (Energy/Telecom/Industrial)
    'ADP', 'DASH', 'CMCSA', 'ILMN', 'GFS', 'WBD', 'ON', 'HON', 'VRSK', 'KHC'
]

end = datetime.now() - timedelta(days=730) 
start = end - timedelta(days=1100)  
capital_inicial_total = 10000.0
capital_por_empresa = 500.0  # 500€ x 20 = 10K

# Descargar todos datos
print("📥 Descargando 20 tickers...")
data = yf.download(tickers, start=start, end=end, progress=False)['Close']
df = data.stack().reset_index().rename(columns={'level_1':'Ticker', 0:'Close'})
df['Date'] = pd.to_datetime(df['Date']).dt.date
df = df.sort_values(['Ticker','Date']).reset_index(drop=True)

# Escalera % por día
sell_thresholds = [5, 4, 3, 3, 2, 1, 0]

# Backtest por empresa
resultados = {}
todas_operaciones = []

for ticker in tickers:
    tdf = df[df['Ticker']==ticker].copy()
    if len(tdf) < 50: continue  # Skip datos insuficientes
    
    tdf['Return'] = tdf['Close'].pct_change() * 100
    capital = capital_por_empresa
    position = 0
    buy_price = 0.0
    buy_day = -1
    ops_ticker = []
    
    for i in range(1, len(tdf)):
        today_price = tdf['Close'].iloc[i]
        today_ret = tdf['Return'].iloc[i]
        
        # COMPRA: -3% sin posición
        if today_ret <= -3 and position == 0:
            position = 1
            buy_price = tdf['Close'].iloc[i]
            buy_day = i
            capital_invertido = capital
            capital = 0
            ops_ticker.append(['BUY', tdf['Date'].iloc[i], buy_price, capital_invertido])
        
        # VENTA escalera D1-D7
        elif position == 1 and buy_day < i <= buy_day + 7:
            days_held = i - buy_day
            req_pct = sell_thresholds[days_held - 1]
            ret_since_buy = (today_price / buy_price - 1) * 100
            
            if ret_since_buy >= req_pct:
                capital = capital_invertido * (today_price / buy_price)
                ops_ticker.append([f'SELL+{req_pct}%D{days_held}', tdf['Date'].iloc[i], today_price, capital])
                position = 0
                buy_day = -1
            elif days_held == 7:
                capital = capital_invertido * (today_price / buy_price)
                ops_ticker.append(['SELL D7', tdf['Date'].iloc[i], today_price, capital])
                position = 0
                buy_day = -1
    
    # Final
    if position == 1:
        capital = capital_invertido * (tdf['Close'].iloc[-1] / buy_price)
    
    resultados[ticker] = capital
    ops_ticker_df = pd.DataFrame(ops_ticker, columns=['Tipo','Fecha','Precio','Capital'])
    ops_ticker_df['Ticker'] = ticker
    todas_operaciones.append(ops_ticker_df)
    
    print(f"  {ticker}: {capital:.0f}€ (+{(capital/500-1)*100:+.1f}%)")

# RESULTADOS FINALES
df_resultados = pd.DataFrame(list(resultados.items()), columns=['Ticker','Capital_Final'])
df_resultados['Rendimiento'] = (df_resultados['Capital_Final']/500 - 1)*100
df_resultados = df_resultados.sort_values('Rendimiento', ascending=False)

capital_final_total = df_resultados['Capital_Final'].sum()
print(f"\n💰 INICIAL TOTAL: €10.000")
print(f"💵 FINAL TOTAL: €{capital_final_total:,.0f}")
print(f"📈 RENDIMIENTO CARTERA: {(capital_final_total/10000-1)*100:+.1f}%")
print(f"🏆 TOP 5:")
print(df_resultados.head().round(0))

# GUARDAR
df_resultados.to_csv('NASDAQ20_backtest_resultados.csv', index=False)
pd.concat(todas_operaciones).to_csv('NASDAQ20_todas_operaciones.csv', index=False)
df.to_csv('NASDAQ20_datos_1000dias.csv', index=False)

print("\n✅ ARCHIVOS:")
print("- NASDAQ20_backtest_resultados.csv")
print("- NASDAQ20_todas_operaciones.csv") 
print("- NASDAQ20_datos_1000dias.csv")

años = 1100 / 365
cagr = (capital_final_total / 10000)**(1/años) - 1
print(f"CAGR real: {cagr*100:.2f}% anual")
