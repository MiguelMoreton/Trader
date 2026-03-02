import pandas as pd

class Strategy:

    def __init__(self, capital_inicial, buy_drop, alloc_pct, sell_thresholds, min_trade):
        self.capital_inicial = float(capital_inicial)
        self.capital_disponible = float(capital_inicial)
        self.buy_drop = float(buy_drop)
        self.alloc_pct = float(alloc_pct)
        self.sell_thresholds = list(sell_thresholds)
        self.min_trade = float(min_trade)

        self.posiciones = {}
        self.operaciones = []

    def _total_invertido_global(self) -> float:
        return float(sum(pos["capital"] for pos in self.posiciones.values()))

    def _operaciones_abiertas(self) -> int:
        return int(len(self.posiciones))

    # =====================
    # BUY LOGIC
    # =====================
    def check_buy(self, row, fecha):

        if pd.isna(row["Return"]):
            return

        ticker = row["Ticker"]

        if (row["Return"] <= self.buy_drop and
                ticker not in self.posiciones and
                self.capital_disponible > 0):

            capital_invertir = self.capital_disponible * self.alloc_pct
            if capital_invertir < self.min_trade:
                return

            precio = float(row["Close"])
            cantidad = capital_invertir / precio

            # 1) Abrimos posición
            self.posiciones[ticker] = {
                "precio_compra": precio,
                "fecha_compra": fecha,
                "capital": float(capital_invertir),
                "cantidad": float(cantidad)
            }

            # 2) Actualizamos capital disponible
            self.capital_disponible -= float(capital_invertir)

            # 3) Métricas de estado (DESPUÉS de abrir)
            ops_abiertas = self._operaciones_abiertas()
            total_invertido = self._total_invertido_global()
            total_disponible = float(self.capital_disponible)

            # 4) Registramos operación con nuevas columnas
            self.operaciones.append([
                fecha, ticker, "BUY",
                precio,
                float(capital_invertir),
                0.0,
                0.0,
                0.0,
                0,
                ops_abiertas,
                total_invertido,
                total_disponible
            ])

    # =====================
    # SELL LOGIC
    # =====================
    def check_sell(self, ticker, precio_actual, fecha):

        pos = self.posiciones[ticker]
        days_held = (fecha - pos["fecha_compra"]).days

        if 1 <= days_held <= len(self.sell_thresholds):

            precio_actual = float(precio_actual)
            ret = (precio_actual / pos["precio_compra"] - 1.0) * 100.0
            required = self.sell_thresholds[days_held - 1]

            if ret >= required or days_held == len(self.sell_thresholds):

                capital_recuperado = pos["capital"] * (precio_actual / pos["precio_compra"])

                # 1) Cerramos posición (primero)
                del self.posiciones[ticker]

                # 2) Actualizamos disponible (después)
                self.capital_disponible += float(capital_recuperado)

                beneficio = float(capital_recuperado - pos["capital"])

                # 3) Métricas de estado (DESPUÉS de cerrar)
                ops_abiertas = self._operaciones_abiertas()
                total_invertido = self._total_invertido_global()
                total_disponible = float(self.capital_disponible)

                # 4) Registro
                self.operaciones.append([
                    fecha, ticker, "SELL",
                    precio_actual,
                    float(pos["capital"]),
                    float(capital_recuperado),
                    beneficio,
                    float(ret),
                    int(days_held),
                    ops_abiertas,
                    total_invertido,
                    total_disponible
                ])

