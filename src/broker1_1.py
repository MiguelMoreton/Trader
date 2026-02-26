import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

print("🚀 BACKTEST 20 NASDAQ - 1000 días - 500€ cada una")

# 20 NASDAQ TOP
tickers = [
    # 🔬 Semiconductores
    'NVDA',  # NVIDIA
    'AMD',   # Advanced Micro Devices
    'MU',    # Micron
    'LRCX',  # Lam Research
    'KLAC',  # KLA Corp
    'AMAT',  # Applied Materials
    'ON',    # ON Semiconductor
    'MRVL',  # Marvell
    
    # 🚗 High Growth / Especulativas
    'TSLA',  # Tesla
    'CVNA',  # Carvana
    'RIVN',  # Rivian
    'LCID',  # Lucid
    'COIN',  # Coinbase
    'PLTR',  # Palantir
    'UPST',  # Upstart
    
    # ☁️ SaaS Volátil
    'DDOG',  # Datadog
    'SNOW',  # Snowflake
    'NET',   # Cloudflare
    'CRWD',  # CrowdStrike
    'ZS',    # Zscaler
    'OKTA',  # Okta
    'TTD',   # Trade Desk
    
    # ⚡ Energía / Cíclicas
    'FANG',  # Diamondback Energy
    'OXY',   # Occidental Petroleum
    'DVN',   # Devon Energy
    'HAL',   # Halliburton
    'SLB',   # Schlumberger
    'VST',   # Vistra
    
    # 🏗️ Industriales cíclicos
    'CAT',   # Caterpillar
    'DE',    # Deere
    'URI',   # United Rentals
    
    # 🏦 Financieras sensibles ciclo
    'GS',    # Goldman Sachs
    'MS',    # Morgan Stanley
    'COF'    # Capital One
]
end = datetime.now()
start = end - timedelta(days=365)  
capital_inicial_total = 17000.0
capital_por_empresa = 500  # 500€ x 20 = 10K

# Descargar todos datos
print("📥 Descargando 20 tickers...")
data = yf.download(tickers, start=start, end=end, progress=False)['Close']
df = data.stack().reset_index().rename(columns={'level_1':'Ticker', 0:'Close'})
df['Date'] = pd.to_datetime(df['Date']).dt.date
df = df.sort_values(['Ticker','Date']).reset_index(drop=True)

# Escalera % por día
sell_thresholds = [1, 1, 1, 1, 1, 1, 0]

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
        if today_ret <= -10 and position == 0:
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
print(f"\n💰 INICIAL TOTAL: €{capital_inicial_total:,.0f}")
print(f"💵 FINAL TOTAL: €{capital_final_total:,.0f}")
print(f"📈 RENDIMIENTO CARTERA: {(capital_final_total/capital_inicial_total-1)*100:+.1f}%")
print(f"🏆 TOP 5:")
print(df_resultados.head().round(0))
print(f"🏆 bottom 5:")
print(df_resultados.tail().round(0))

# GUARDAR
df_resultados.to_csv('NASDAQ20_backtest_resultados.csv', index=False)
pd.concat(todas_operaciones).to_csv('NASDAQ20_todas_operaciones.csv', index=False)
df.to_csv('NASDAQ20_datos_1000dias.csv', index=False)

print("\n✅ ARCHIVOS:")
print("- NASDAQ20_backtest_resultados.csv")
print("- NASDAQ20_todas_operaciones.csv") 
print("- NASDAQ20_datos_1000dias.csv")

"""años = 1100 / 365
cagr = (capital_final_total / 50000)**(1/años) - 1
print(f"CAGR real: {cagr*100:.2f}% anual")"""
