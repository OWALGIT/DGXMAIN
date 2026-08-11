import io, warnings, numpy as np, pandas as pd, pyarrow.parquet as pq
warnings.filterwarnings('ignore')
from s3lib import client
c=client(); B='market-data'
def rd(key):
    b=c.get_object(Bucket=B,Key=key)['Body'].read()
    return pq.ParquetFile(io.BytesIO(b)).read().to_pandas()
def close_series(key,label):
    try:
        d=rd(key)
        d['date']=pd.to_datetime(d['date']).dt.tz_localize(None).dt.normalize()
        s=d.set_index('date')['close'].astype(float).sort_index()
        s=s[~s.index.duplicated(keep='last')]; s.name=label; return s
    except Exception as e:
        print("  MISS",label,str(e)[:50]); return None

series={}
def add(key,label):
    s=close_series(key,label)
    if s is not None: series[label]=s

pre='source=yfinance/symbol='
# --- Equity indices ---
for sym,lab in [('sp500_us','SPX'),('nasdaq_us','NDX'),('russell2000_us','RUT'),
                ('hangseng_hk','HangSeng'),('nikkei_jp','Nikkei'),('dax_de','DAX'),
                ('ftse_uk','FTSE'),('eurostoxx50','EuroStoxx'),('cac_fr','CAC')]:
    add(f'world_indices/{pre}{sym}/{sym}.parquet',lab)
# China ADRs
for sym,lab in [('china_msci_etf','China_MSCI'),('china_internet_etf','China_Internet'),('alibaba','Alibaba')]:
    add(f'china_adr/{pre}{sym}/{sym}.parquet',lab)
# Sectors
for sym in ['tech','energy','financials','industrials','materials','utilities','healthcare',
            'cons_staples','cons_discretionary','real_estate','comm_services']:
    add(f'sectors/{pre}{sym}/{sym}.parquet','SEC_'+sym)
# Volatility (levels)
for sym,lab in [('vix','VIX'),('vix9d','VIX9D'),('vix3m','VIX3M'),('vvix','VVIX')]:
    add(f'vix_complex/{pre}{sym}/{sym}.parquet',lab)
# Bonds / credit
for sym,lab in [('hyg_high_yield','HYG'),('lqd_ig_credit','LQD'),('tlt_20y_treasury','TLT'),
                ('ief_7_10y_treasury','IEF'),('move_bond_vol','MOVE')]:
    add(f'bonds_credit/{pre}{sym}/{sym}.parquet',lab)
# Commodities
for sym,lab in [('wti_oil','WTI'),('brent_oil','Brent'),('gold','Gold'),('copper','Copper'),('dollar_index','DXY')]:
    add(f'commodities/{pre}{sym}/{sym}.parquet',lab)
for sym,lab in [('natural_gas','NatGas'),('wheat','Wheat')]:
    add(f'commodities_broad/{pre}{sym}/{sym}.parquet',lab)
# FX
for sym,lab in [('usd_jpy','USDJPY'),('usd_cny','USDCNY'),('usd_eur','USDEUR')]:
    add(f'currencies/{pre}{sym}/{sym}.parquet',lab)
add('fx_shekel/source=eodhd/symbol=ILS/ILS.parquet','USDILS')
# Crypto
for sym,lab in [('bitcoin','BTC'),('ethereum','ETH')]:
    add(f'crypto/{pre}{sym}/{sym}.parquet',lab)

# --- Treasury curve (levels) ---
try:
    tc=[]
    for y in [2022,2023,2024,2025,2026]:
        try: tc.append(rd(f'treasury_curve_rich/source=treasury_gov/treasury_curve_{y}.parquet'))
        except: pass
    tc=pd.concat(tc,ignore_index=True)
    tc['date']=pd.to_datetime(tc['Date']).dt.normalize()
    tc=tc.set_index('date').sort_index()
    for col,lab in [('2 Yr','UST2Y'),('10 Yr','UST10Y')]:
        if col in tc: series[lab]=tc[col].astype(float)
    if '2 Yr' in tc and '10 Yr' in tc:
        series['UST_2s10s']=(tc['10 Yr']-tc['2 Yr']).astype(float)
except Exception as e: print("  MISS treasury",str(e)[:60])

# --- EVENT SIGNALS ---
# GDELT news volume by topic
try:
    nv=rd('gdelt/source=official/item=gdelt_news_volume/gdelt_news_volume.parquet')
    nv['date']=pd.to_datetime(nv['date']).dt.tz_localize(None).dt.normalize()
    for t in nv['topic'].unique():
        s=nv[nv['topic']==t].set_index('date')['value'].astype(float).sort_index()
        s=s[~s.index.duplicated(keep='last')]; series['NEWS_'+t]=s
except Exception as e: print("  MISS gdelt_nv",str(e)[:60])

# Chokepoint container transits (key straits)
CHOKE={4:'RedSea_BabMandeb',1:'Suez',6:'Hormuz',11:'TaiwanStrait',5:'Malacca'}
choke_all=[]
for i in range(1,29):
    try:
        d=rd(f'chokepoints/source=imf_portwatch/chokepoint=chokepoint{i}/chokepoint{i}.parquet')
        d['date']=pd.to_datetime(d['date']).dt.normalize()
        s=d.set_index('date')['n_container'].astype(float).sort_index()
        s=s[~s.index.duplicated(keep='last')]
        choke_all.append(s.rename(i))
        if i in CHOKE: series['SHIP_'+CHOKE[i]]=s
    except Exception as e: pass
if choke_all:
    series['SHIP_Global']=pd.concat(choke_all,axis=1).sum(axis=1)

# Conflict intensity (daily material-conflict mentions)
try:
    ce=rd('geopolitics/source=gdelt/dataset=gdelt_conflict_events/gdelt_conflict_events.parquet')
    ce['date']=pd.to_datetime(ce['SQLDATE'].astype(str),format='%Y%m%d',errors='coerce').dt.normalize()
    ce['NumMentions']=pd.to_numeric(ce['NumMentions'],errors='coerce')
    ce['QuadClass']=pd.to_numeric(ce['QuadClass'],errors='coerce')
    mat=ce[ce['QuadClass']==4]
    series['CONFLICT_intensity']=mat.groupby('date')['NumMentions'].sum().sort_index()
except Exception as e: print("  MISS conflict",str(e)[:60])

# Wikipedia geopolitical attention (daily total views)
try:
    wa=rd('geopolitics/source=wikipedia/dataset=wiki_geopolitical_attention/wiki_geopolitical_attention.parquet')
    wa['date']=pd.to_datetime(wa['timestamp'].astype(str).str[:8],format='%Y%m%d',errors='coerce').dt.normalize()
    wa['views']=pd.to_numeric(wa['views'],errors='coerce')
    series['ATTN_wiki_geopol']=wa.groupby('date')['views'].sum().sort_index()
except Exception as e: print("  MISS wiki",str(e)[:60])

# --- Assemble panel ---
panel=pd.DataFrame(series).sort_index()
panel=panel.loc['2023-01-01':]
panel.to_parquet('panel.parquet')
print("PANEL SHAPE:",panel.shape)
print("date range:",panel.index.min().date(),"->",panel.index.max().date())
print("columns (%d):"%panel.shape[1])
cov=panel.notna().mean().mul(100).round(0)
for c_ in panel.columns: print(f"   {c_:<22} coverage={cov[c_]:>3.0f}%  last={panel[c_].dropna().iloc[-1] if panel[c_].notna().any() else float('nan'):.2f}")
