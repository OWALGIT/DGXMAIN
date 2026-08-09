import io,warnings,numpy as np,pandas as pd,pyarrow.parquet as pq
warnings.filterwarnings('ignore')
from s3lib import client
c=client(); B='market-data'
def load(ds,sym):
    import glob
    f=f'{ds}/source=yfinance/symbol={sym}/{sym}.parquet'
    try: b=c.get_object(Bucket=B,Key=f)['Body'].read()
    except:
        # some are eodhd/official; find it
        ks=[o['Key'] for o in c.list_objects_v2(Bucket=B,Prefix=f'{ds}/').get('Contents',[]) if f'symbol={sym}/' in o['Key']]
        if not ks: return None
        b=c.get_object(Bucket=B,Key=ks[0])['Body'].read()
    d=pq.ParquetFile(io.BytesIO(b)).read().to_pandas()
    d['date']=pd.to_datetime(d['date']).dt.tz_localize(None).dt.normalize()
    s=d.set_index('date')['close'].astype(float).sort_index()
    return s[~s.index.duplicated(keep='last')]
MENU={'VOO/SPX':('world_indices','sp500_us'),'QQQM/NDX':('world_indices','nasdaq_us'),
 'VTWO/RUT':('world_indices','russell2000_us'),'XLK tech':('sectors','tech'),
 'XLV health':('sectors','healthcare'),'XLP staples':('sectors','cons_staples'),
 'XLE energy':('sectors','energy'),'XLU utils':('sectors','utilities'),
 'TLT 20y':('bonds_credit','tlt_20y_treasury'),'IEF 7-10y':('bonds_credit','ief_7_10y_treasury'),
 'SHY 1-3y':('bonds_credit','shy_1_3y_treasury'),'HYG hy':('bonds_credit','hyg_high_yield'),
 'Gold':('commodities','gold'),'Copper':('commodities','copper'),'DXY':('commodities','dollar_index'),
 'BTC':('crypto','bitcoin')}
rows=[]
px={}
for lab,(ds,sym) in MENU.items():
    s=load(ds,sym)
    if s is None: print("MISS",lab); continue
    px[lab]=s
    s2=s[s.index>='2000-01-01']
    r=s2.pct_change().dropna()
    ann=(1+r.mean())**252-1; vol=r.std()*np.sqrt(252); shp=ann/vol if vol else np.nan
    dd=(s2/s2.cummax()-1).min()
    last=s2.iloc[-1]; ma200=s2.rolling(200).mean().iloc[-1]
    r12=s2.iloc[-1]/s2.asof(s2.index[-1]-pd.Timedelta(days=365))-1
    r3=s2.iloc[-1]/s2.asof(s2.index[-1]-pd.Timedelta(days=91))-1
    rows.append((lab,str(s2.index[0].date()),ann*100,vol*100,shp,dd*100,r12*100,r3*100,last,(last/ma200-1)*100))
df=pd.DataFrame(rows,columns=['asset','since','annRet%','vol%','Sharpe','maxDD%','ret12m%','ret3m%','last','vs200MA%'])
pd.set_option('display.width',200,'display.max_columns',20)
print(df.round(2).to_string(index=False))
# correlation of returns (since 2015 for stability), key assets
keys=['VOO/SPX','QQQM/NDX','XLV health','XLP staples','TLT 20y','Gold','HYG hy','BTC','DXY']
M=pd.DataFrame({k:px[k] for k in keys if k in px}).pct_change().loc['2015':]
print("\nCORRELATION (2015+ daily returns):")
print(M.corr().round(2).to_string())
print("\nLATEST CLOSES:", {k:round(float(px[k].iloc[-1]),2) for k in ['XLV health','XLP staples','TLT 20y','IEF 7-10y','SHY 1-3y','Gold','BTC'] if k in px})
print("data through:", max(px[k].index[-1] for k in px).date())
