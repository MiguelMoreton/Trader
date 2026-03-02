import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

import os
print("🚀 BACKTEST CARTERA DINÁMICA - INFORME COMPLETO POR ACCIÓN")

# ==============================
# CONFIG
# ==============================

tickers = [
    'NVDA','AMD','MU','LRCX','KLAC','AMAT','ON','MRVL',
    'TSLA','CVNA','RIVN','LCID','COIN','PLTR','UPST',
    'DDOG','SNOW','NET','CRWD','ZS','OKTA','TTD',
    'FANG','OXY','DVN','HAL','SLB','VST',
    'CAT','DE','URI',
    'GS','MS','COF'
]

capital_total = 250000.0
capital_disponible = capital_total
sell_thresholds = [5,4,3,3,2,1,0]

# ==============================
# DESCARGA DATOS
# ==============================

end = datetime.now()
start = end - timedelta(days=3000)

print("📥 Descargando datos...")
data = yf.download(tickers, start=start, end=end, progress=False)['Close']

df = data.stack().reset_index()
df.columns = ['Date','Ticker','Close']
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values(['Date','Ticker'])

df['Return'] = df.groupby('Ticker')['Close'].pct_change()*100

# ==============================
# VARIABLES
# ==============================

posiciones = {}
operaciones = []
equity_diaria = []
capital_total_invertido = 0

# ==============================
# BACKTEST
# ==============================

for fecha in sorted(df['Date'].unique()):

    df_dia = df[df['Date']==fecha]

    # -------- VENTAS --------
    for ticker in list(posiciones.keys()):

        pos = posiciones[ticker]
        days_held = (fecha - pos['fecha_compra']).days

        precio_actual = df_dia[df_dia['Ticker']==ticker]['Close']
        if precio_actual.empty:
            continue

        precio_actual = precio_actual.values[0]
        ret = (precio_actual/pos['precio_compra']-1)*100

        if 1 <= days_held <= 7:
            req_pct = sell_thresholds[days_held-1]

            if ret >= req_pct or days_held==7:

                capital_recuperado = pos['capital']*(precio_actual/pos['precio_compra'])
                capital_disponible += capital_recuperado

                operaciones.append([
                    fecha,ticker,'SELL',precio_actual,
                    pos['capital'],
                    capital_recuperado,
                    capital_recuperado-pos['capital'],
                    ret,
                    days_held
                ])

                del posiciones[ticker]

    # -------- COMPRAS --------
    for _,row in df_dia.iterrows():

        if pd.isna(row['Return']):
            continue

        if row['Return']<=-3 and row['Ticker'] not in posiciones and capital_disponible>0:

            capital_invertir = capital_disponible*0.1
            if capital_invertir<100:
                continue

            posiciones[row['Ticker']] = {
                'precio_compra':row['Close'],
                'fecha_compra':fecha,
                'capital':capital_invertir
            }

            capital_total_invertido += capital_invertir
            capital_disponible -= capital_invertir

            operaciones.append([
                fecha,row['Ticker'],'BUY',row['Close'],
                capital_invertir,
                0,
                0,
                0,
                0
            ])

    # -------- EQUITY DIARIA --------
    valor_posiciones = 0
    for ticker,pos in posiciones.items():
        precio_actual = df_dia[df_dia['Ticker']==ticker]['Close']
        if not precio_actual.empty:
            precio_actual = precio_actual.values[0]
            valor_posiciones += pos['capital']*(precio_actual/pos['precio_compra'])

    equity_total = capital_disponible + valor_posiciones
    equity_diaria.append([fecha,equity_total])

# ==============================
# RESULTADOS GENERALES
# ==============================

df_equity = pd.DataFrame(equity_diaria,columns=['Fecha','Equity'])
df_equity['Max_Acumulado']=df_equity['Equity'].cummax()
df_equity['Drawdown_%']=(df_equity['Equity']-df_equity['Max_Acumulado'])/df_equity['Max_Acumulado']*100

capital_final = df_equity['Equity'].iloc[-1]
max_drawdown = df_equity['Drawdown_%'].min()

print("\n💰 CAPITAL INICIAL:",capital_total)
print("💵 CAPITAL FINAL:",round(capital_final,2))
print("📈 RENTABILIDAD TOTAL:",round((capital_final/capital_total-1)*100,2),"%")
print("📉 MAX DRAWDOWN:",round(max_drawdown,2),"%")
print("💸 CAPITAL TOTAL INVERTIDO:",round(capital_total_invertido,2))

# ==============================
# OPERACIONES DF
# ==============================

df_ops = pd.DataFrame(operaciones,columns=[
    'Fecha','Ticker','Tipo','Precio',
    'Capital_Invertido',
    'Capital_Recuperado',
    'Beneficio',
    'Retorno_%',
    'Dias'
])

df_ops['Fecha']=pd.to_datetime(df_ops['Fecha'])
df_ops['Año']=df_ops['Fecha'].dt.year

ventas = df_ops[df_ops['Tipo']=='SELL']

# ==============================
# RENTABILIDAD POR ACCIÓN
# ==============================

resumen_acciones = ventas.groupby('Ticker').agg({
    'Capital_Invertido':'sum',
    'Beneficio':'sum',
    'Retorno_%':'mean',
    'Ticker':'count'
})

resumen_acciones.rename(columns={
    'Capital_Invertido':'Capital_Total_Invertido',
    'Beneficio':'Beneficio_Total',
    'Retorno_%':'Retorno_Medio_%',
    'Ticker':'Numero_Operaciones'
},inplace=True)

resumen_acciones['Rentabilidad_%']=resumen_acciones['Beneficio_Total']/resumen_acciones['Capital_Total_Invertido']*100

print("\n📊 RENTABILIDAD POR ACCIÓN")
print(resumen_acciones.sort_values('Beneficio_Total',ascending=False))

# ==============================
# RENTABILIDAD POR ACCIÓN Y AÑO
# ==============================

resumen_anual_accion = ventas.groupby(['Ticker','Año']).agg({
    'Beneficio':'sum',
    'Capital_Invertido':'sum'
})

resumen_anual_accion['Rentabilidad_%']=resumen_anual_accion['Beneficio']/resumen_anual_accion['Capital_Invertido']*100

print("\n📅 RENTABILIDAD POR ACCIÓN Y AÑO")
print(resumen_anual_accion)

# ==============================
# CONFIG EXPORTACIÓN
# ==============================

output_dir = "resultados"
os.makedirs(output_dir, exist_ok=True)

script_name = os.path.splitext(os.path.basename(__file__))[0]

# ==============================
# EXPORTACIÓN
# ==============================

df_ops.to_csv(
    os.path.join(output_dir, f"{script_name}_operaciones_detalladas.csv"),
    index=False
)

df_equity.to_csv(
    os.path.join(output_dir, f"{script_name}_curva_equity.csv"),
    index=False
)

resumen_acciones.to_csv(
    os.path.join(output_dir, f"{script_name}_resumen_por_accion.csv")
)

resumen_anual_accion.to_csv(
    os.path.join(output_dir, f"{script_name}_resumen_anual_por_accion.csv")
)

print("📁 Archivos generados en la carpeta 'resultados':")
print(f"- {script_name}_operaciones_detalladas.csv")
print(f"- {script_name}_curva_equity.csv")
print(f"- {script_name}_resumen_por_accion.csv")
print(f"- {script_name}_resumen_anual_por_accion.csv")
print("✅ INFORME COMPLETO GENERADO")
