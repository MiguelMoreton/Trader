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
# BACKTEST PARAMETRIZADO
# ==============================
def run_backtest(df_all: pd.DataFrame,
                 buy_drop_pct: float,
                 alloc_pct: float,
                 capital_total: float,
                 sell_thresholds: list[float]) -> float:
    capital_disponible = float(capital_total)
    posiciones = {}
    equity_diaria = []

    for fecha in sorted(df_all["Date"].unique()):
        df_dia = df_all[df_all["Date"] == fecha]

        # -------- VENTAS --------
        for ticker in list(posiciones.keys()):
            pos = posiciones[ticker]
            days_held = (fecha - pos["fecha_compra"]).days

            precio_actual = df_dia.loc[df_dia["Ticker"] == ticker, "Close"]
            if precio_actual.empty:
                continue

            precio_actual = float(precio_actual.iloc[0])
            ret = (precio_actual / pos["precio_compra"] - 1.0) * 100.0

            if 1 <= days_held <= 7:
                req_pct = sell_thresholds[days_held - 1]
                if ret >= req_pct or days_held == 7:
                    capital_recuperado = pos["capital"] * (precio_actual / pos["precio_compra"])
                    capital_disponible += capital_recuperado
                    del posiciones[ticker]

        # -------- COMPRAS --------
        for _, row in df_dia.iterrows():
            if pd.isna(row["Return"]):
                continue

            if row["Return"] <= buy_drop_pct and row["Ticker"] not in posiciones and capital_disponible > 0:
                capital_invertir = capital_disponible * alloc_pct
                if capital_invertir < 100:
                    continue

                posiciones[row["Ticker"]] = {
                    "precio_compra": float(row["Close"]),
                    "fecha_compra": fecha,
                    "capital": float(capital_invertir),
                }
                capital_disponible -= float(capital_invertir)

        # -------- EQUITY DIARIA --------
        valor_posiciones = 0.0
        for ticker, pos in posiciones.items():
            precio_actual = df_dia.loc[df_dia["Ticker"] == ticker, "Close"]
            if not precio_actual.empty:
                precio_actual = float(precio_actual.iloc[0])
                valor_posiciones += pos["capital"] * (precio_actual / pos["precio_compra"])

        equity_diaria.append(capital_disponible + valor_posiciones)

    if not equity_diaria:
        return 0.0

    capital_final = float(equity_diaria[-1])
    return (capital_final / float(capital_total) - 1.0) * 100.0

# ==============================
# GRID + HEATMAP
# ==============================
print("🧮 Calculando rejilla de parámetros...")
heat = np.full((len(buy_thresholds), len(alloc_pcts)), np.nan, dtype=float)

for i, bt in enumerate(buy_thresholds):
    for j, ap in enumerate(alloc_pcts):
        heat[i, j] = run_backtest(df, buy_drop_pct=bt, alloc_pct=ap,
                                  capital_total=capital_total, sell_thresholds=sell_thresholds)

heat_df = pd.DataFrame(
    heat,
    index=[f"{bt}%" for bt in buy_thresholds],
    columns=[f"{int(ap*100)}%" for ap in alloc_pcts]
)

heat_csv_path = os.path.join(output_dir, f"{base}_heatmap_rentabilidad.csv")
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
