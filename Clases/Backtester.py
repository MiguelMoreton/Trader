
from Strategy import Strategy
import pandas as pd

class Backtester:

    def __init__(self, strategy: Strategy):
        self.strategy = strategy
        self.equity_diaria = []

    def run(self, df: pd.DataFrame):

        for fecha in sorted(df['Date'].unique()):

            df_dia = df[df['Date'] == fecha]

            # 1️⃣ Ventas primero
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

        return pd.DataFrame(self.equity_diaria, columns=["Fecha", "Equity"])