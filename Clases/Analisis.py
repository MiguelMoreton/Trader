import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os


class Analisis:
    def __init__(self, df_ops: pd.DataFrame, df_equity: pd.DataFrame, capital_inicial: float):
        """
        df_ops: DataFrame de operaciones con columnas:
            ['Fecha','Ticker','Tipo','Precio','Capital_Invertido','Capital_Recuperado','Beneficio','Retorno_%','Dias']
        df_equity: DataFrame con columnas ['Fecha','Equity']
        capital_inicial: capital inicial del backtest (float)
        """
        self.df_ops = df_ops.copy()
        self.df_equity = df_equity.copy()
        self.capital_inicial = float(capital_inicial)

        # Normaliza fechas por si acaso
        if "Fecha" in self.df_ops.columns:
            self.df_ops["Fecha"] = pd.to_datetime(self.df_ops["Fecha"])
        if "Fecha" in self.df_equity.columns:
            self.df_equity["Fecha"] = pd.to_datetime(self.df_equity["Fecha"])

    # ============================================================
    # 1) Resultado por acción (ticker)
    # ============================================================
    def resultado_por_accion(self) -> pd.DataFrame:
        """
        Devuelve un DataFrame con métricas por ticker usando solo ventas (SELL):
        - Capital_Total_Invertido
        - Beneficio_Total
        - Retorno_Medio_%
        - Numero_Operaciones (ventas)
        - Rentabilidad_% = Beneficio_Total / Capital_Total_Invertido
        """
        if self.df_ops.empty:
            return pd.DataFrame()

        ventas = self.df_ops[self.df_ops["Tipo"] == "SELL"].copy()
        if ventas.empty:
            return pd.DataFrame()

        resumen = ventas.groupby("Ticker").agg(
            Capital_Total_Invertido=("Capital_Invertido", "sum"),
            Beneficio_Total=("Beneficio", "sum"),
            Retorno_Medio_=("Retorno_%", "mean"),
            Numero_Operaciones=("Ticker", "count")
        )

        # Evita división por 0
        resumen["Rentabilidad_%"] = np.where(
            resumen["Capital_Total_Invertido"] > 0,
            (resumen["Beneficio_Total"] / resumen["Capital_Total_Invertido"]) * 100.0,
            np.nan
        )

        # Ajuste nombre de columna (estética)
        resumen.rename(columns={"Retorno_Medio_": "Retorno_Medio_%"}, inplace=True)

        return resumen.sort_values("Beneficio_Total", ascending=False)

    # ============================================================
    # 2) Rentabilidad total, CAGR y duración
    # ============================================================
    def resumen_rentabilidad(self) -> dict:
        """
        Devuelve:
          - capital_inicial
          - capital_final
          - rentabilidad_total_pct
          - duracion_anios
          - cagr_pct
        """
        if self.df_equity.empty:
            return {
                "capital_inicial": self.capital_inicial,
                "\n capital_final": np.nan,
                "\n rentabilidad_total_pct": np.nan,
                "\n duracion_anñs": np.nan,
                "\n CAGR": np.nan,
            }

        capital_final = float(self.df_equity["Equity"].iloc[-1])
        rent_total = (capital_final / self.capital_inicial - 1.0) * 100.0

        fecha_min = self.df_equity["Fecha"].min()
        fecha_max = self.df_equity["Fecha"].max()
        duracion_anios = (fecha_max - fecha_min).days / 365.25 if pd.notna(fecha_min) and pd.notna(fecha_max) else np.nan

        if duracion_anios and duracion_anios > 0:
            cagr = (capital_final / self.capital_inicial) ** (1.0 / duracion_anios) - 1.0
            cagr_pct = cagr * 100.0
        else:
            cagr_pct = np.nan

        return {
            "capital_inicial": self.capital_inicial,
            "capital_final": capital_final,
            "rentabilidad_total_pct": rent_total,
            "duracion_anios": duracion_anios,
            "cagr_pct": cagr_pct,
        }

    # ============================================================
    # 3) Heatmap como el de la foto
    # ============================================================
    
    """def plot_heatmap(
        self,
        heat_df: pd.DataFrame,
        title: str = "Heatmap de rentabilidad total (%)",
        xlabel: str = "% capital por operación",
        ylabel: str = "% bajada para comprar",
        annotate: bool = True,
        decimals: int = 1,
        save_dir: str = "Clases/Resultados",
        filename: str = "heatmap_rentabilidad.png",
        show: bool = False,     # 👈 pon True si quieres intentar mostrar
        dpi: int = 200
    ) -> str:

        if heat_df is None or heat_df.empty:
            raise ValueError("heat_df está vacío. Pásame un DataFrame con la matriz del heatmap.")

        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)

        heat = heat_df.to_numpy(dtype=float)

        fig, ax = plt.subplots(figsize=(10, 6))
        im = ax.imshow(heat, aspect="auto")

        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        ax.set_xticks(np.arange(len(heat_df.columns)))
        ax.set_yticks(np.arange(len(heat_df.index)))
        ax.set_xticklabels([str(c) for c in heat_df.columns])
        ax.set_yticklabels([str(i) for i in heat_df.index])

        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Rentabilidad total (%)")

        if annotate:
            for i in range(heat.shape[0]):
                for j in range(heat.shape[1]):
                    val = heat[i, j]
                    if np.isfinite(val):
                        ax.text(j, i, f"{val:.{decimals}f}", ha="center", va="center", fontsize=9)

        plt.tight_layout()

        # ✅ Guardar imagen
        plt.savefig(save_path, dpi=dpi)

        # ✅ Mostrar solo si lo pides (en muchos entornos no aparecerá)
        if show:
            plt.show()

        # ✅ Cerrar para evitar consumo de memoria en bucles
        plt.close(fig)

        return save_path"""