import pandas as pd

class Strategy:

    def __init__(self, capital_inicial, buy_drop, alloc_pct ,sell_thresholds,min_trade):

        self.capital_inicial = capital_inicial
        self.capital_disponible = capital_inicial
        self.buy_drop = buy_drop
        self.alloc_pct = alloc_pct
        self.sell_thresholds = sell_thresholds
        self.min_trade = min_trade

        self.posiciones = {}
        self.operaciones = []

    # =====================
    # BUY LOGIC
    # =====================
    def check_buy(self, row, fecha):

        if pd.isna(row['Return']):
            return

        ticker = row['Ticker']
        #print(f"🔍 Evaluando {ticker}, fecha: {fecha} | Return: {row['Return']:.2f}%")

        if (row['Return'] <= self.buy_drop and
                ticker not in self.posiciones and
                self.capital_disponible > 0):

            capital_invertir = self.capital_disponible * self.alloc_pct
            if capital_invertir < self.min_trade:
                return

            cantidad = capital_invertir / row['Close']

            self.posiciones[ticker] = {
                'precio_compra': row['Close'],
                'fecha_compra': fecha,
                'capital': capital_invertir,
                'cantidad': cantidad
            }

            self.capital_disponible -= capital_invertir

            self.operaciones.append([
                fecha, ticker, 'BUY',
                row['Close'], capital_invertir, 0, 0, 0, 0
            ])

            #print(f"🛒 BUY {ticker} a {row['Close']:.2f}")

    # =====================
    # SELL LOGIC
    # =====================
    def check_sell(self, ticker, precio_actual, fecha):

        pos = self.posiciones[ticker]
        days_held = (fecha - pos['fecha_compra']).days

        if 1 <= days_held <= len(self.sell_thresholds):

            ret = (precio_actual / pos['precio_compra'] - 1) * 100
            required = self.sell_thresholds[days_held - 1]

            if ret >= required or days_held == len(self.sell_thresholds):

                capital_recuperado = pos['capital'] * (precio_actual / pos['precio_compra'])

                self.capital_disponible += capital_recuperado

                self.operaciones.append([
                    fecha, ticker, 'SELL',
                    precio_actual,
                    pos['capital'],
                    capital_recuperado,
                    capital_recuperado - pos['capital'],
                    ret,
                    days_held
                ])

                # print(f"💰 SELL {ticker} | {ret:.2f}% en {days_held} días")

                del self.posiciones[ticker]