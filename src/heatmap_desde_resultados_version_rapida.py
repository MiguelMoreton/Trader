import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

print("🧩 HEATMAP DESDE RESULTADOS - (usa datos guardados por el broker)")

# ==============================
# CONFIG
# ==============================
output_dir = "resultados"
os.makedirs(output_dir, exist_ok=True)

# Eje Y: % bajada para comprar (negativos)
buy_thresholds = [-2, -3, -4, -5, -6, -7, -8, -9, -10]

# Eje X: % de capital disponible invertido por operación
alloc_pcts = [0.02, 0.05, 0.10, 0.15, 0.20]

capital_total = 250000.0
sell_thresholds = [5, 4, 3, 3, 2, 1, 0]

# ==============================
# DETECTA PREFIJO DEL RUN (a partir de *_operaciones_detalladas.csv)
# ==============================
ops_files = sorted(glob.glob(os.path.join(output_dir, "*_operaciones_detalladas.csv")))
if not ops_files:
    raise FileNotFoundError(
        "No encuentro archivos '*_operaciones_detalladas.csv' dentro de 'resultados/'.\n"
        "Ejecuta primero tu script borker1_3_resultados.py para generar los CSV."
    )

ops_path = ops_files[-1]  # el más reciente por orden alfabético; normalmente basta
base = os.path.basename(ops_path).replace("_operaciones_detalladas.csv", "")
print(f"📌 Detectado prefijo de resultados: {base}")

# ==============================
# CARGA DATOS DE MERCADO GUARDADOS POR EL BROKER
# ==============================
# Este script NECESITA el dataset base (Date, Ticker, Close, Return) que usa el backtest,
# porque para el heatmap hay que re-ejecutar el backtest con distintos parámetros.
#
# Formatos admitidos (en resultados/):
# - {base}_market_data.parquet  (recomendado)
# - {base}_market_data.csv
#
parquet_path = os.path.join(output_dir, f"{base}_market_data.parquet")
csv_path = os.path.join(output_dir, f"{base}_market_data.csv")

if os.path.exists(parquet_path):
    df = pd.read_parquet(parquet_path)
    print(f"📦 Cargado: {os.path.basename(parquet_path)}")
elif os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    print(f"📄 Cargado: {os.path.basename(csv_path)}")
else:
    raise FileNotFoundError(
        "No encuentro el dataset de mercado necesario para construir el heatmap.\n\n"
        "Solución (1 vez): añade estas 2 líneas en tu broker (después de calcular df['Return']):\n"
        f"  df.to_parquet(os.path.join('{output_dir}', f'{{script_name}}_market_data.parquet'), index=False)\n"
        "  # o si prefieres CSV:\n"
        f"  df.to_csv(os.path.join('{output_dir}', f'{{script_name}}_market_data.csv'), index=False)\n\n"
        "Luego vuelve a ejecutar el broker y después este script."
    )

# Normaliza tipos/columnas
needed = {"Date", "Ticker", "Close", "Return"}
missing = needed - set(df.columns)
if missing:
    raise ValueError(f"Faltan columnas en market_data: {missing}. Debe tener {sorted(needed)}.")

df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values(["Date", "Ticker"])

# ==============================
# PRECALCULO POR DIA (MUY IMPORTANTE PARA VELOCIDAD)
# ==============================
df = df.sort_values(["Date", "Ticker"]).copy()

days = []
for d, g in df.groupby("Date", sort=True):
    # arrays numpy para iterar mucho más rápido que iterrows
    days.append((
        d,
        g["Ticker"].to_numpy(),
        g["Close"].to_numpy(dtype=float),
        g["Return"].to_numpy(dtype=float),
    ))

print(f"⚡ Precalculados {len(days)} días para acelerar el grid")

# ==============================
# BACKTEST PARAMETRIZADO
# ==============================
def run_backtest_fast(days, buy_drop_pct, alloc_pct, capital_total, sell_thresholds):
    capital_disponible = float(capital_total)
    posiciones = {}  # ticker -> dict(precio_compra, fecha_compra, capital)
    equity_last = capital_disponible

    for fecha, tick_arr, close_arr, ret_arr in days:
        # ===== VENTAS =====
        if posiciones:
            for ticker in list(posiciones.keys()):
                pos = posiciones[ticker]
                days_held = (fecha - pos["fecha_compra"]).days

                if 1 <= days_held <= 7:
                    # localizar precio actual del ticker en el día (búsqueda lineal, pero arrays pequeños)
                    # para acelerar un poco: usa mask
                    mask = (tick_arr == ticker)
                    if not mask.any():
                        continue
                    precio_actual = float(close_arr[mask][0])

                    ret = (precio_actual / pos["precio_compra"] - 1.0) * 100.0
                    req_pct = sell_thresholds[days_held - 1]

                    if ret >= req_pct or days_held == 7:
                        capital_recuperado = pos["capital"] * (precio_actual / pos["precio_compra"])
                        capital_disponible += capital_recuperado
                        del posiciones[ticker]

        # ===== COMPRAS =====
        # compra si Return <= buy_drop_pct (y return no NaN)
        # evitamos iterrows: operamos con masks
        valid = ~np.isnan(ret_arr)
        buy_mask = valid & (ret_arr <= buy_drop_pct)

        if buy_mask.any() and capital_disponible > 0:
            # recorremos candidatos del día
            idxs = np.where(buy_mask)[0]
            for k in idxs:
                ticker = tick_arr[k]
                if ticker in posiciones:
                    continue

                capital_invertir = capital_disponible * alloc_pct
                if capital_invertir < 100:
                    continue

                posiciones[ticker] = {
                    "precio_compra": float(close_arr[k]),
                    "fecha_compra": fecha,
                    "capital": float(capital_invertir),
                }
                capital_disponible -= float(capital_invertir)

                if capital_disponible <= 0:
                    break

        # ===== EQUITY (solo última, para rentabilidad total) =====
        valor_posiciones = 0.0
        if posiciones:
            # suma valor marcado a mercado
            for ticker, pos in posiciones.items():
                mask = (tick_arr == ticker)
                if mask.any():
                    precio_actual = float(close_arr[mask][0])
                    valor_posiciones += pos["capital"] * (precio_actual / pos["precio_compra"])

        equity_last = capital_disponible + valor_posiciones

    return (equity_last / float(capital_total) - 1.0) * 100.0

# ==============================
# GRID + HEATMAP
# ==============================
print("🧮 Calculando rejilla de parámetros...")
heat = np.full((len(buy_thresholds), len(alloc_pcts)), np.nan, dtype=float)

total = len(buy_thresholds) * len(alloc_pcts)
n = 0

for i, bt in enumerate(buy_thresholds):
    for j, ap in enumerate(alloc_pcts):
        n += 1
        # progreso para Codespaces
        print(f"[{n}/{total}] caída {bt}% | capital {int(ap*100)}%")
        heat[i, j] = run_backtest_fast(
            days, buy_drop_pct=bt, alloc_pct=ap,
            capital_total=capital_total, sell_thresholds=sell_thresholds
        )
heat_csv_path = os.path.join(output_dir, f"{base}_heatmap_rentabilidad.csv")
heat_df = pd.DataFrame(
    heat,
    index=[f"{bt}%" for bt in buy_thresholds],
    columns=[f"{int(ap*100)}%" for ap in alloc_pcts]
)
heat_df.to_csv(heat_csv_path, index=True)

print("🎨 Dibujando heatmap...")
fig, ax = plt.subplots(figsize=(10, 6))
im = ax.imshow(heat, aspect="auto")

ax.set_xticks(np.arange(len(alloc_pcts)))
ax.set_yticks(np.arange(len(buy_thresholds)))
ax.set_xticklabels([f"{int(ap*100)}%" for ap in alloc_pcts])
ax.set_yticklabels([f"{bt}%" for bt in buy_thresholds])

ax.set_xlabel("% capital por operación")
ax.set_ylabel("% bajada para comprar")
ax.set_title("Heatmap de rentabilidad total (%)")

cbar = fig.colorbar(im, ax=ax)
cbar.set_label("Rentabilidad total (%)")

for i in range(len(buy_thresholds)):
    for j in range(len(alloc_pcts)):
        val = heat[i, j]
        if np.isfinite(val):
            ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=9)

plt.tight_layout()
heat_png_path = os.path.join(output_dir, f"{base}_heatmap_rentabilidad.png")
plt.savefig(heat_png_path, dpi=200)
plt.show()

print("\n✅ Archivos generados en 'resultados/':")
print(f"- {os.path.basename(heat_csv_path)}")
print(f"- {os.path.basename(heat_png_path)}")
