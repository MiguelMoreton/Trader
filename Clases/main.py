import pandas as pd 
from data_loader import DataLoader
from Strategy import Strategy
from Backtester import Backtester
from Analisis import Analisis



def main():

    # ==============================
    # PARAMETROS
    # ==============================
    tickers =   ['NVDA','AMD','MU','LRCX','KLAC','AMAT','ON','MRVL',
    'TSLA','CVNA','RIVN','LCID','COIN','PLTR','UPST',
    'DDOG','SNOW','NET','CRWD','ZS','OKTA','TTD',
    'FANG','OXY','DVN','HAL','SLB','VST',
    'CAT','DE','URI',
    'GS','MS','COF']
    duration = 5
    capital = 250000
    buy_drop = -3
    alloc_pct = 0.1
    sell_thresholds=[5,4,3,3,2,1,0]
    min_trade = 100

    # ==============================
    # CARGA DATOS
    # ==============================
    loader = DataLoader()
    df = loader.load_data(tickers, duration)

    # ==============================
    # STRATEGY
    # ==============================
    strategy = Strategy(capital_inicial=capital, buy_drop=buy_drop, alloc_pct=alloc_pct, sell_thresholds=sell_thresholds, min_trade=min_trade)

    # ==============================
    # BACKTEST
    # ==============================
    backtester = Backtester(strategy)
    df_equity, df_ops = backtester.run(df)

    # ==============================
    # RESULTADOS
    # ==============================
    capital_final = df_equity["Equity"].iloc[-1]
    rent_total = (capital_final / capital - 1) * 100

    print("\n============================")
    print("💰 CAPITAL FINAL:", round(capital_final, 2))
    print("📈 RENTABILIDAD:", round(rent_total, 2), "%")
    print("============================")

    # ==============================
    # RESULTADOS DE ANALISIS
    # ==============================
    analisis = Analisis(df_ops=df_ops,df_equity=df_equity, capital_inicial= capital)
    
    #Resumen por accciones
    res_acciones = analisis.resultado_por_accion()
    print("\n📊 RESUMEN POR ACCION:")
    print(res_acciones)

    resumen = analisis.resumen_rentabilidad()
    print("\n📊 RESUMEN DE RENTABILIDAD: \n")
    print(resumen)


#---------------------------------
    #CREACION DE HEATMAP
    buy_thresholds = [-2, -3, -4, -5, -6, -7, -8, -9, -10]
    alloc_pcts = [0.02, 0.05, 0.10, 0.15, 0.20]

    heatmap_data = backtester.generate_heatmap_data(
        df=df,
        buy_thresholds=buy_thresholds,
        alloc_pcts=alloc_pcts,
        capital_inicial=capital,
        sell_thresholds=sell_thresholds,
        min_trade=min_trade,
        verbose=True
    )

    ruta = analisis.plot_heatmap(heatmap_data, save_dir="Clases/Resultados",
    filename="heatmap_rentabilidad.png",
    show=False,  # pon True si quieres probar a mostrarlo
    decimals=2)
    print(f"\n📁 Heatmap guardado en: {ruta}")

#-------------------------------

    df_equity.to_csv("Clases/Resultados/equity.csv", index=False)
    df_ops.to_csv("Clases/Resultados/operaciones.csv", index=False)
    print("📁 equity.csv generado")
    print("📁 operaciones.csv generado")


if __name__ == "__main__":
    main()