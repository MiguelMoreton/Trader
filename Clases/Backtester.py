
from Strategy import Strategy
import pandas as pd
import numpy as np

class Backtester:

    def __init__(self, strategy: Strategy):
        self.strategy = strategy
        self.equity_diaria = []

    def run(self, df: pd.DataFrame):

        # reset por si re-ejecutas
        self.equity_diaria = []
        open_daily = []              # resumen diario de posiciones abiertas (opcional)
        open_positions_daily = []    # detalle diario por posición (opcional)

        # Asegura tipos y orden
        df = df.copy()
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values(["Date", "Ticker"])

        for fecha in sorted(df["Date"].unique()):

            df_dia = df[df["Date"] == fecha]

            # 1️⃣ VENTAS
            for ticker in list(self.strategy.posiciones.keys()):
                precio_actual = df_dia[df_dia["Ticker"] == ticker]["Close"]
                if not precio_actual.empty:
                    self.strategy.check_sell(
                        ticker,
                        float(precio_actual.values[0]),
                        fecha
                    )

            # 2️⃣ COMPRAS
            for _, row in df_dia.iterrows():
                self.strategy.check_buy(row, fecha)

            # 3️⃣ MARK-TO-MARKET + PRINT DIARIO
            valor_posiciones = 0.0
            invertido_abierto = 0.0
            pnl_abierto = 0.0

            print(f"\n📅 Fecha: {pd.to_datetime(fecha).date()}")

            if len(self.strategy.posiciones) == 0:
                print("   ➤ No hay posiciones abiertas")
            else:
                for ticker, pos in self.strategy.posiciones.items():

                    precio_actual = df_dia[df_dia["Ticker"] == ticker]["Close"]
                    if precio_actual.empty:
                        continue

                    precio_actual = float(precio_actual.values[0])

                    # valor actual de la posición (equivalente a cantidad * precio_actual)
                    valor_actual = float(pos["capital"]) * (precio_actual / float(pos["precio_compra"]))
                    pnl = valor_actual - float(pos["capital"])
                    ret_pct = (precio_actual / float(pos["precio_compra"]) - 1.0) * 100.0

                    valor_posiciones += valor_actual
                    invertido_abierto += float(pos["capital"])
                    pnl_abierto += pnl

                    # detalle por posición (para export si quieres)
                    open_positions_daily.append([
                        fecha,
                        ticker,
                        float(pos["precio_compra"]),
                        precio_actual,
                        float(pos["capital"]),
                        float(valor_actual),
                        float(pnl),
                        float(ret_pct)
                    ])

                    # print por ticker
                    print(f"   {ticker} | PnL: {pnl:,.2f} € | Retorno: {ret_pct:+.2f}%")

            # total abierto
            ret_total_pct = (pnl_abierto / invertido_abierto) * 100.0 if invertido_abierto > 0 else 0.0
            print(f"   🔹 TOTAL CARTERA ABIERTA | PnL: {pnl_abierto:,.2f} € | Retorno: {ret_total_pct:+.2f}%")

            # 4️⃣ EQUITY DIARIA (esto era lo que te faltaba en tu bloque)
            equity = float(self.strategy.capital_disponible) + float(valor_posiciones)
            self.equity_diaria.append([fecha, equity])

            # resumen diario abierto (opcional para export)
            open_daily.append([
                fecha,
                float(invertido_abierto),
                float(valor_posiciones),
                float(pnl_abierto),
                float(self.strategy.capital_disponible),
                float(equity),
                int(len(self.strategy.posiciones)),
                float(ret_total_pct)
            ])

        # ===========================
        # DataFrames finales seguros
        # ===========================

        # ---- EQUITY ----
        if len(self.equity_diaria) > 0:
            df_equity = pd.DataFrame(self.equity_diaria, columns=["Fecha", "Equity"])
            df_equity["Fecha"] = pd.to_datetime(df_equity["Fecha"])
            df_equity = df_equity.sort_values("Fecha").reset_index(drop=True)
        else:
            df_equity = pd.DataFrame(columns=["Fecha", "Equity"])

        # ---- OPS ----
        columns_ops = [
            "Fecha","Ticker","Tipo","Precio",
            "Capital_Invertido","Capital_Recuperado","Beneficio","Retorno_%","Dias",
            "operaciones_abiertas","Total_Invertido_global","Total_disponible"
        ]

        if len(self.strategy.operaciones) > 0:
            df_ops = pd.DataFrame(self.strategy.operaciones, columns=columns_ops)
            df_ops["Fecha"] = pd.to_datetime(df_ops["Fecha"])

            numeric_cols = [
                "Precio","Capital_Invertido","Capital_Recuperado","Beneficio",
                "Retorno_%","Dias","operaciones_abiertas","Total_Invertido_global","Total_disponible"
            ]
            for col in numeric_cols:
                df_ops[col] = pd.to_numeric(df_ops[col], errors="coerce")

            df_ops = df_ops.sort_values("Fecha").reset_index(drop=True)

        else:
            df_ops = pd.DataFrame(columns=columns_ops)

        # (Opcional) si luego quieres exportarlos, los tienes aquí:
        # df_open_daily = pd.DataFrame(open_daily, columns=[
        #     "Fecha","Invertido_Abierto","Valor_Abierto","PnL_Abierto",
        #     "Cash_Disponible","Equity_Total","Num_Posiciones_Abiertas","Rent_Abierta_%"
        # ])
        # df_open_positions_daily = pd.DataFrame(open_positions_daily, columns=[
        #     "Fecha","Ticker","Precio_Compra","Precio_Actual","Capital_Invertido",
        #     "Valor_Actual","PnL","Retorno_%"
        # ])

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