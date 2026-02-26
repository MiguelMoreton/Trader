import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

print("🚀 BACKTEST CARTERA DINÁMICA - 50% por señal")

# ==============================
# CONFIG
# ==============================
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
capital_total = 250000.0
capital_disponible = capital_total
sell_thresholds = [5, 4, 3, 3, 2, 1, 0]

# ==============================
# DATOS
# ==============================
end = datetime.now()
start = end - timedelta(days=365)

print("📥 Descargando datos...")
data = yf.download(tickers, start=start, end=end, progress=False)['Close']

df = data.stack().reset_index()
df.columns = ['Date', 'Ticker', 'Close']
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values(['Date','Ticker'])

df['Return'] = df.groupby('Ticker')['Close'].pct_change() * 100

# ==============================
# VARIABLES BACKTEST
# ==============================
posiciones = {}   # ticker -> dict
operaciones = []

# ==============================
# BACKTEST POR FECHA
# ==============================
for fecha in sorted(df['Date'].unique()):
    
    df_dia = df[df['Date'] == fecha]
    
    # --------------------------
    # 1️⃣ Revisar ventas primero
    # --------------------------
    for ticker in list(posiciones.keys()):
        pos = posiciones[ticker]
        days_held = (fecha - pos['fecha_compra']).days
        
        precio_actual = df_dia[df_dia['Ticker']==ticker]['Close']
        if precio_actual.empty:
            continue
            
        precio_actual = precio_actual.values[0]
        ret = (precio_actual / pos['precio_compra'] - 1) * 100
        
        if 1 <= days_held <= 7:
            req_pct = sell_thresholds[days_held-1]
            
            if ret >= req_pct or days_held == 7:
                capital_recuperado = pos['capital'] * (precio_actual / pos['precio_compra'])
                capital_disponible += capital_recuperado
                
                operaciones.append([
                    fecha, ticker, 'SELL',
                    precio_actual, capital_recuperado
                ])
                
                del posiciones[ticker]

    # --------------------------
    # 2️⃣ Revisar compras
    # --------------------------
    for _, row in df_dia.iterrows():
        ticker = row['Ticker']
        ret = row['Return']
        
        if pd.isna(ret):
            continue
        
        # Señal de compra
        if ret <= -20 and ticker not in posiciones and capital_disponible > 0:
            
            capital_invertir = capital_disponible * 0.5
            
            if capital_invertir < 100:  # mínimo operativo opcional
                continue
            
            posiciones[ticker] = {
                'precio_compra': row['Close'],
                'fecha_compra': fecha,
                'capital': capital_invertir
            }
            
            capital_disponible -= capital_invertir
            
            operaciones.append([
                fecha, ticker, 'BUY',
                row['Close'], capital_invertir
            ])

# ==============================
# CIERRE FINAL
# ==============================
for ticker, pos in posiciones.items():
    precio_final = df[df['Ticker']==ticker]['Close'].iloc[-1]
    capital_recuperado = pos['capital'] * (precio_final / pos['precio_compra'])
    capital_disponible += capital_recuperado

capital_final = capital_disponible

print(f"\n💰 CAPITAL INICIAL: {capital_total:,.0f}€")
print(f"💵 CAPITAL FINAL: {capital_final:,.0f}€")
print(f"📈 RENTABILIDAD: {(capital_final/capital_total-1)*100:+.2f}%")

df_ops = pd.DataFrame(operaciones, columns=['Fecha','Ticker','Tipo','Precio','Capital'])
df_ops.to_csv("backtest_operaciones.csv", index=False)

print("✅ Archivo generado: backtest_operaciones.csv")