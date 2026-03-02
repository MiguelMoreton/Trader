import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

print("🚀 BACKTEST CARTERA DINÁMICA - 50% por señal")

# ==============================
# CONFIG
# ==============================
tickers = ['SPY']  # Volatility Index (VIX)
capital_total = 250000.0
sell_thresholds = [5, 4, 3, 3, 2, 1, 0]

# ==============================
# DATOS
# ==============================
end = datetime.now()
start = end - timedelta(days=1000)

print("📥 Descargando datos...")
data = yf.download(tickers, start=start, end=end, progress=False)['Close']

df = data.stack().reset_index()
df.columns = ['Date', 'Ticker', 'Close']
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values(['Date', 'Ticker'])

df['Return'] = df.groupby('Ticker')['Close'].pct_change() * 100

# Años del backtest (para anualizada)
years = (df['Date'].max() - df['Date'].min()).days / 365.25

# ==============================
# FUNCIÓN BACKTEST
# ==============================
def run_backtest(drop_threshold_pct: float):
    """
    drop_threshold_pct: por ejemplo -2 para señal ret <= -2
    Devuelve: capital_final, operaciones (DataFrame)
    """
    capital_disponible = capital_total
    posiciones = {}   # ticker -> dict
    operaciones = []

    for fecha in sorted(df['Date'].unique()):
        df_dia = df[df['Date'] == fecha]

        # 1) Ventas
        for ticker in list(posiciones.keys()):
            pos = posiciones[ticker]
            days_held = (fecha - pos['fecha_compra']).days

            precio_actual = df_dia[df_dia['Ticker'] == ticker]['Close']
            if precio_actual.empty:
                continue

            precio_actual = float(precio_actual.values[0])
            ret = (precio_actual / pos['precio_compra'] - 1) * 100

            if 1 <= days_held <= 7:
                req_pct = sell_thresholds[days_held - 1]

                if ret >= req_pct or days_held == 7:
                    capital_recuperado = pos['capital'] * (precio_actual / pos['precio_compra'])
                    capital_disponible += capital_recuperado

                    operaciones.append([fecha, ticker, 'SELL', precio_actual, capital_recuperado])
                    del posiciones[ticker]

        # 2) Compras
        for _, row in df_dia.iterrows():
            ticker = row['Ticker']
            ret = row['Return']

            if pd.isna(ret):
                continue

            # Señal de compra (caída)
            if ret <= drop_threshold_pct and ticker not in posiciones and capital_disponible > 0:
                capital_invertir = capital_disponible * 0.5

                if capital_invertir < 100:
                    continue

                posiciones[ticker] = {
                    'precio_compra': float(row['Close']),
                    'fecha_compra': fecha,
                    'capital': float(capital_invertir)
                }

                capital_disponible -= capital_invertir
                operaciones.append([fecha, ticker, 'BUY', float(row['Close']), float(capital_invertir)])

    # Cierre final
    for ticker, pos in list(posiciones.items()):
        precio_final = float(df[df['Ticker'] == ticker]['Close'].iloc[-1])
        capital_recuperado = pos['capital'] * (precio_final / pos['precio_compra'])
        capital_disponible += capital_recuperado

    df_ops = pd.DataFrame(operaciones, columns=['Fecha', 'Ticker', 'Tipo', 'Precio', 'Capital'])
    capital_final = float(capital_disponible)

    return capital_final, df_ops

# ==============================
# BARRIDO DE CAÍDAS (-1% a -25%)
# ==============================
results = []

for drop in range(1, 26):  # 1..25
    drop_threshold = -float(drop)

    capital_final, _ = run_backtest(drop_threshold)

    total_return = (capital_final / capital_total) - 1
    annualized = (capital_final / capital_total) ** (1 / years) - 1 if years > 0 else np.nan

    results.append({
        "Caída señal (%)": drop_threshold,
        "Capital inicial (€)": capital_total,
        "Capital final (€)": capital_final,
        "Rentabilidad total (%)": total_return * 100,
        "Rentabilidad anualizada (%)": annualized * 100
    })

df_results = pd.DataFrame(results)

# Formato bonito (opcional)
df_results["Capital inicial (€)"] = df_results["Capital inicial (€)"].round(2)
df_results["Capital final (€)"] = df_results["Capital final (€)"].round(2)
df_results["Rentabilidad total (%)"] = df_results["Rentabilidad total (%)"].round(2)
df_results["Rentabilidad anualizada (%)"] = df_results["Rentabilidad anualizada (%)"].round(2)

print("\n📊 RESULTADOS POR UMBRAL DE CAÍDA")
print(df_results.to_string(index=False))

df_results.to_csv("backtest_resumen_por_caida.csv", index=False)
print("\n✅ Archivo generado: backtest_resumen_por_caida.csv")


# ==============================
# 🏆 CONCLUSIÓN: MEJOR UMBRAL
# ==============================
best_total = df_results.loc[df_results["Rentabilidad total (%)"].idxmax()]
best_cagr  = df_results.loc[df_results["Rentabilidad anualizada (%)"].idxmax()]

print("\n🏆 CONCLUSIÓN (MEJOR RESULTADO)")
print(f"➡️ Mejor RENTABILIDAD TOTAL: caída {best_total['Caída señal (%)']:.0f}% "
      f"| Capital final {best_total['Capital final (€)']:,.2f}€ "
      f"| Total {best_total['Rentabilidad total (%)']:+.2f}% "
      f"| Anualizada {best_total['Rentabilidad anualizada (%)']:+.2f}%")

# Por si el mejor CAGR no coincide con el mejor total
if best_cagr["Caída señal (%)"] != best_total["Caída señal (%)"]:
    print(f"➡️ Mejor RENTABILIDAD ANUALIZADA (CAGR): caída {best_cagr['Caída señal (%)']:.0f}% "
          f"| Capital final {best_cagr['Capital final (€)']:,.2f}€ "
          f"| Total {best_cagr['Rentabilidad total (%)']:+.2f}% "
          f"| Anualizada {best_cagr['Rentabilidad anualizada (%)']:+.2f}%")