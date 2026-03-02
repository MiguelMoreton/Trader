
from Strategy import Strategy
import pandas as pd
import numpy as np

class Backtester:

    def __init__(self, strategy: Strategy):
        self.strategy = strategy
        self.equity_diaria = []

    def run(self, df: pd.DataFrame):

        for fecha in sorted(df['Date'].unique()):

            df_dia = df[df['Date'] == fecha]

            # 1️⃣ Ventas
            for ticker in list(self.strategy.posiciones.keys()):
                precio_actual = df_dia[df_dia['Ticker'] == ticker]['Close']
                if not precio_actual.empty:
                    self.strategy.check_sell(
                        ticker,
                        precio_actual.values[0],
                        fecha
                    )

            # 2️⃣ Compras
            for _, row in df_dia.iterrows():
                self.strategy.check_buy(row, fecha)

            # 3️⃣ Equity diaria
            valor_posiciones = 0
            for ticker, pos in self.strategy.posiciones.items():
                precio_actual = df_dia[df_dia['Ticker'] == ticker]['Close']
                if not precio_actual.empty:
                    valor_posiciones += pos['capital'] * (
                        precio_actual.values[0] / pos['precio_compra']
                    )

            equity = self.strategy.capital_disponible + valor_posiciones
            self.equity_diaria.append([fecha, equity])

        # 👇 aquí construimos los DataFrames finales

        df_equity = pd.DataFrame(self.equity_diaria, columns=["Fecha", "Equity"])

        df_ops = pd.DataFrame(self.strategy.operaciones, columns=[
            "Fecha","Ticker","Tipo","Precio",
            "Capital_Invertido","Capital_Recuperado","Beneficio","Retorno_%","Dias",
            "operaciones_abiertas","Total_Invertido_global","Total_disponible"
        ])

        return df_equity, df_ops
    
    def generate_heatmap_data(
        self,
        df: pd.DataFrame,
        buy_thresholds: list,
        alloc_pcts: list,
        capital_inicial: float,
        sell_thresholds: list,
        min_trade: float = 100.0,
        verbose: bool = True
    ) -> pd.DataFrame:
        """
        Devuelve un DataFrame 2D:
          index   -> buy_thresholds (ej [-2,-3,...])
          columns -> alloc_pcts (ej [0.02,0.05,...])
          values  -> rentabilidad total (%)
        """

        heat = np.full((len(buy_thresholds), len(alloc_pcts)), np.nan, dtype=float)

        total = len(buy_thresholds) * len(alloc_pcts)
        n = 0

        for i, drop in enumerate(buy_thresholds):
            for j, alloc in enumerate(alloc_pcts):
                n += 1
                if verbose:
                    print(f"[{n}/{total}] drop={drop}% | alloc={int(alloc*100)}%")

                # ⚠️ Importante: estrategia NUEVA por combinación (para no arrastrar estado)
                strat = Strategy(
                    capital_inicial=capital_inicial,
                    buy_drop=float(drop),
                    alloc_pct=float(alloc),
                    sell_thresholds=sell_thresholds,
                    min_trade=min_trade
                )

                bt = Backtester(strat)
                df_equity_tmp, _ = bt.run(df)

                capital_final = float(df_equity_tmp["Equity"].iloc[-1])
                rent_total = (capital_final / float(capital_inicial) - 1.0) * 100.0

                heat[i, j] = rent_total

        heat_df = pd.DataFrame(
            heat,
            index=[f"{d}%" for d in buy_thresholds],
            columns=[f"{int(a*100)}%" for a in alloc_pcts]
        )

        return heat_df