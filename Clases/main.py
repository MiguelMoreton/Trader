import pandas as pd 
from data_loader import DataLoader
from Strategy import Strategy
from Backtester import Backtester



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
    duration = 300

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
    equity_df = backtester.run(df)

    # ==============================
    # RESULTADOS
    # ==============================
    capital_final = equity_df["Equity"].iloc[-1]
    rent_total = (capital_final / capital - 1) * 100

    print("\n============================")
    print("💰 CAPITAL FINAL:", round(capital_final, 2))
    print("📈 RENTABILIDAD:", round(rent_total, 2), "%")
    print("============================")

    equity_df.to_csv("Clases/Resultados/equity.csv", index=False)
    print("📁 equity.csv generado")


if __name__ == "__main__":
    main()