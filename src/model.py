from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display


def backtest_contexto(
    df: pd.DataFrame,
    ticker: str,
    caida_pct: int,
    hold_days: int,
    capital_start: float,
) -> Tuple[float, List[dict]]:
    work = df.copy().reset_index(drop=True)
    work['ret_diaria_pct'] = work['Close'].pct_change() * 100

    capital = capital_start
    operaciones: List[dict] = []
    i = 1

    while i < len(work) - hold_days:
        if work.loc[i, 'ret_diaria_pct'] <= -caida_pct:
            buy_i = i
            sell_i = i + hold_days

            precio_compra = float(work.loc[buy_i, 'Close'])
            precio_venta = float(work.loc[sell_i, 'Close'])
            capital_aportado = capital
            capital_liquidado = capital_aportado * (precio_venta / precio_compra)
            ret_op = (capital_liquidado / capital_aportado - 1) * 100

            operaciones.append(
                {
                    'Ticker': ticker,
                    'Caida_%': caida_pct,
                    'Dias_salida': hold_days,
                    'Fecha_inicio': work.loc[buy_i, 'Date'].date(),
                    'Fecha_final': work.loc[sell_i, 'Date'].date(),
                    'Precio_compra': round(precio_compra, 4),
                    'Precio_venta': round(precio_venta, 4),
                    'Capital_aportado': round(capital_aportado, 2),
                    'Capital_liquidado': round(capital_liquidado, 2),
                    'Rentabilidad_operacion_%': round(ret_op, 4),
                }
            )

            capital = capital_liquidado
            i = sell_i + 1
        else:
            i += 1

    rentabilidad_total = (capital / capital_start - 1) * 100
    return rentabilidad_total, operaciones


def run_context_analysis(
    precios_por_ticker: Dict[str, pd.DataFrame],
    capital_inicial: float = 10000.0,
    caidas: List[int] | None = None,
    dias_salida: List[int] | None = None,
    base_dir: str | Path = 'data',
) -> None:
    if caidas is None:
        caidas = list(range(3, 11))
    if dias_salida is None:
        dias_salida = list(range(1, 8))

    base_path = Path(base_dir)

    for ticker, df_ticker in precios_por_ticker.items():
        ticker_dir = base_path / ticker.replace('/', '_')

        resultados_por_caida = []
        for c in caidas:
            rentabilidades = [
                backtest_contexto(df_ticker, ticker, c, d, capital_inicial)[0]
                for d in dias_salida
            ]
            resultados_por_caida.append(sum(rentabilidades) / len(rentabilidades))

        resultados_por_dias = []
        for d in dias_salida:
            rentabilidades = [
                backtest_contexto(df_ticker, ticker, c, d, capital_inicial)[0]
                for c in caidas
            ]
            resultados_por_dias.append(sum(rentabilidades) / len(rentabilidades))

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(caidas, resultados_por_caida, marker='o')
        ax.set_title(f'{ticker} - Rentabilidad media vs caida (%)')
        ax.set_xlabel('Caida estudiada (%)')
        ax.set_ylabel('Rentabilidad obtenida (%)')
        ax.grid(True, alpha=0.3)
        plt.show()

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(dias_salida, resultados_por_dias, marker='o', color='darkorange')
        ax.set_title(f'{ticker} - Rentabilidad media vs dias de salida')
        ax.set_xlabel('Dias hasta la venta')
        ax.set_ylabel('Rentabilidad obtenida (%)')
        ax.grid(True, alpha=0.3)
        plt.show()

        todas_operaciones: List[dict] = []
        for c in caidas:
            for d in dias_salida:
                _, ops = backtest_contexto(df_ticker, ticker, c, d, capital_inicial)
                todas_operaciones.extend(ops)

        tabla_ops = pd.DataFrame(todas_operaciones)
        if tabla_ops.empty:
            print(f'{ticker}: no hubo operaciones en los contextos evaluados.')
        else:
            tabla_ops = tabla_ops.sort_values(
                ['Caida_%', 'Dias_salida', 'Fecha_inicio']
            ).reset_index(drop=True)
            display(tabla_ops)
            tabla_ops.to_csv(ticker_dir / f'{ticker}_operaciones_contextos.csv', index=False)
            print(f'Tabla guardada en {ticker_dir / f"{ticker}_operaciones_contextos.csv"}')
