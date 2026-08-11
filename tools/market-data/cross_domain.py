import io,json,warnings,numpy as np,pandas as pd,pyarrow.parquet as pq
warnings.filterwarnings('ignore')
from s3lib import client
c=client(); B='market-data'
def rd(k):
    b=c.get_object(Bucket=B,Key=k)['Body'].read()
    return pq.ParquetFile(io.BytesIO(b)).read().to_pandas()
def norm_date(s): return pd.to_datetime(s,errors='coerce',utc=True).dt.tz_localize(None).dt.normalize()

IDX=pd.date_range('2023-01-01','2026-08-08',freq='D')
def daily(s):
    s=s[~s.index.duplicated(keep='last')].sort_index()
    return s.reindex(IDX)

# ================= MARKET TARGETS (Y) =================
Y={}
P=pd.read_parquet('panel.parquet'); P.index=pd.to_datetime(P.index)
for col in ['SPX','NDX','RUT','HangSeng','Nikkei','DAX','WTI','Brent','Gold','Copper','NatGas','Wheat',
            'DXY','USDJPY','BTC','HYG','SEC_energy','SEC_materials']:
    if col in P: Y[col]=daily(P[col])
lvl={'VIX':P['VIX'],'UST10Y':P['UST10Y']}
# extra reaction sectors
pre='source=yfinance/symbol='
def closes(key):
    d=rd(key); d['date']=norm_date(d['date']); return daily(d.set_index('date')['close'].astype(float))
try: Y['Defense']=closes(f'defense/{pre}aerospace_def_etf/aerospace_def_etf.parquet')
except Exception as e: print('def miss',e)
try:
    air=[]
    for s in ['delta','united','american_air']:
        try: air.append(closes(f'travel/{pre}{s}/{s}.parquet'))
        except: pass
    if air: Y['Airlines']=pd.concat(air,axis=1).mean(axis=1)
except Exception as e: print('air miss',e)
try: Y['AgStocks']=closes(f'agriculture/{pre}corn_etf/corn_etf.parquet')
except Exception as e: print('ag miss',e)
try: Y['Soybeans']=closes(f'commodities_broad/{pre}soybeans/soybeans.parquet')
except: pass
try: Y['Corn']=closes(f'commodities_broad/{pre}corn/corn.parquet')
except: pass

# Y innovations: returns for prices, diff for VIX/UST
Yr={}
for k,s in Y.items(): Yr[k]=s.pct_change()
Yr['VIX']=lvl['VIX'].reindex(IDX).diff()
Yr['UST10Y']=lvl['UST10Y'].reindex(IDX).diff()
Ydf=pd.DataFrame(Yr)

# ================= EVENT SIGNALS (X) =================
X={}
def add(name,s):
    s=daily(s.astype(float));
    if s.notna().sum()>200: X[name]=s
    else: print('  thin',name,int(s.notna().sum()))

# ---- Shipping (IMF PortWatch) ----
CH={4:'RedSea',1:'Suez',6:'Hormuz',11:'Taiwan',5:'Malacca'}
allc=[]
for i in range(1,29):
    try:
        d=rd(f'chokepoints/source=imf_portwatch/chokepoint=chokepoint{i}/chokepoint{i}.parquet')
        d['date']=pd.to_datetime(d['date']).dt.normalize()
        s=d.set_index('date')['n_container'].astype(float); allc.append(s.rename(i))
        if i in CH: add('SHIP_'+CH[i],s)
    except: pass
if allc: add('SHIP_Global',pd.concat(allc,axis=1).sum(axis=1))

# ---- Conflict / war / terror ----
try:
    ce=rd('geopolitics/source=gdelt/dataset=gdelt_conflict_events/gdelt_conflict_events.parquet')
    ce['date']=pd.to_datetime(ce['SQLDATE'].astype(str),format='%Y%m%d',errors='coerce').dt.normalize()
    ce['NumMentions']=pd.to_numeric(ce['NumMentions'],errors='coerce')
    ce['QuadClass']=pd.to_numeric(ce['QuadClass'],errors='coerce')
    ce['Goldstein']=pd.to_numeric(ce['GoldsteinScale'],errors='coerce')
    add('WAR_conflict_intensity',ce[ce['QuadClass']==4].groupby('date')['NumMentions'].sum())
    add('WAR_goldstein_neg',(-ce[ce['Goldstein']<0].groupby('date')['Goldstein'].sum()))
except Exception as e: print('conflict miss',e)
# GDELT news volume topics
try:
    nv=rd('gdelt/source=official/item=gdelt_news_volume/gdelt_news_volume.parquet')
    nv['date']=norm_date(nv['date'])
    for t in nv['topic'].unique():
        add('NEWS_'+t, nv[nv['topic']==t].set_index('date')['value'])
except Exception as e: print('nv miss',e)

# ---- Attention (Wikipedia finance/geopolitics) ----
AW={'Recession':'ATTN_Recession','Bank_run':'ATTN_BankRun','Margin_call':'ATTN_MarginCall',
    'Oil_price':'ATTN_OilPrice','Federal_Reserve':'ATTN_Fed','Financial_crisis_of_2007-2008':'ATTN_FinCrisis'}
for item,lab in AW.items():
    try:
        d=rd(f'attention_wikipedia/source=official/item={item}/{item}.parquet')
        d['date']=pd.to_datetime(d['date']).dt.normalize()
        add(lab,d.set_index('date')['views'])
    except Exception as e: pass
try:
    wa=rd('geopolitics/source=wikipedia/dataset=wiki_geopolitical_attention/wiki_geopolitical_attention.parquet')
    wa['date']=pd.to_datetime(wa['timestamp'].astype(str).str[:8],format='%Y%m%d',errors='coerce').dt.normalize()
    add('ATTN_geopolitics',wa.groupby('date')['views'].sum())
except Exception as e: print('wiki miss',e)

# ---- Uncertainty (daily EPU etc.) ----
UNC={'policy_uncertainty_us_daily':'UNC_EPU_US','risk_on_risk_off':'UNC_RiskOnOff',
     'emv_macro_business':'UNC_EMV_macro','emv_elections_governance':'UNC_EMV_politics'}
for ser,lab in UNC.items():
    try:
        d=rd(f'uncertainty/source=mixed/series={ser}/{ser}.parquet')
        d['date']=pd.to_datetime(d['date']).dt.normalize()
        add(lab,d.set_index('date')['value'])
    except Exception as e: pass

# ---- Disasters: earthquakes M5+ ----
try:
    eq=rd('sensors/source=public/dataset=earthquakes_m5plus/earthquakes_m5plus.parquet')
    eq['date']=pd.to_datetime(eq['date']).dt.normalize()
    eq['mag']=pd.to_numeric(eq['mag'],errors='coerce'); eq['sig']=pd.to_numeric(eq['sig'],errors='coerce')
    g=eq.groupby('date')
    add('QUAKE_count', g.size())
    add('QUAKE_maxmag', g['mag'].max())
    add('QUAKE_sig_sum', g['sig'].sum())
    add('QUAKE_big_M6', eq[eq['mag']>=6].groupby('date').size())
except Exception as e: print('quake miss',e)

# ---- Space weather: geomagnetic Kp ----
try:
    kp=rd('space_weather/source=official/item=planetary_k_index/planetary_k_index.parquet')
    kp['date']=pd.to_datetime(kp['time_tag']).dt.normalize()
    add('SPACE_kp_max', kp.groupby('date')['kp_index'].max())
except Exception as e: print('kp miss',e)
try:
    ss=rd('space_weather/source=official/item=solar_cycle_observed/solar_cycle_observed.parquet')
    dc=[x for x in ss.columns if 'tag' in x.lower() or 'date' in x.lower()][0]
    ss['date']=pd.to_datetime(ss[dc]).dt.normalize()
    add('SPACE_sunspots', ss.set_index('date')['ssn'])
except Exception as e: print('ssn miss',e)

# ---- Climate: ENSO ONI (seasonal -> ffill daily) ----
try:
    en=rd('sensors/source=public/dataset=enso_oni/enso_oni.parquet')
    seas={'DJF':1,'JFM':2,'FMA':3,'MAM':4,'AMJ':5,'MJJ':6,'JJA':7,'JAS':8,'ASO':9,'SON':10,'OND':11,'NDJ':12}
    en['mo']=en['SEAS'].map(seas); en=en.dropna(subset=['mo'])
    en['date']=pd.to_datetime(dict(year=en['YR'],month=en['mo'].astype(int),day=15))
    s=en.set_index('date')['ANOM'].astype(float).sort_index()
    add('CLIMATE_enso_oni', s.reindex(IDX).ffill())
except Exception as e: print('enso miss',e)

# ---- Weather (commodity regions) ----
def wx(loc,metric):
    d=rd(f'weather/source=open_meteo/location={loc}/{loc}.parquet')
    d['date']=pd.to_datetime(d['date']).dt.tz_localize(None).dt.normalize()
    return d.set_index('date')[metric].astype(float)
try: add('WX_permian_temp', wx('us_permian_oil','temperature_2m_max'))
except Exception as e: pass
try: add('WX_henryhub_temp', wx('us_henryhub_gas_la','temperature_2m_max'))
except Exception as e: pass
try:
    gr=[]
    for loc in ['brazil_soy_matogrosso','argentina_pampas']:
        try: gr.append(wx(loc,'precipitation_sum'))
        except: pass
    if gr: add('WX_grain_precip', pd.concat(gr,axis=1).mean(axis=1))
except Exception as e: pass

print("signals built:",len(X),"| markets:",Ydf.shape[1])
Xdf=pd.DataFrame(X)
Xdf.to_parquet('signals.parquet')

# ================= CROSS-DOMAIN LEAD-LAG =================
# innovation of each signal = daily change (captures jumps); z-scored for scale-free compare
def innov(s):
    d=s.diff()
    return (d-d.mean())/d.std()
Xi=pd.DataFrame({k:innov(v) for k,v in X.items()})

LAGS=list(range(-3,11))   # k>0 => signal leads market by k days
def best(xs,ys):
    df=pd.concat([xs.rename('x'),ys.rename('y')],axis=1).replace([np.inf,-np.inf],np.nan)
    row={}
    for k in LAGS:
        r=df['x'].corr(df['y'].shift(-k))
        row[k]=None if pd.isna(r) else round(float(r),3)
    lead={k:v for k,v in row.items() if k>=1 and v is not None}
    bl=max(lead,key=lambda k:abs(lead[k])) if lead else None
    return row, (bl, row.get(bl) if bl else None), row.get(0)

signals=list(Xi.columns); markets=list(Ydf.columns)
matrix=[]      # best-lead corr per (signal,market)
lagmat=[]      # best-lead lag
contemp=[]
chains=[]
for si in signals:
    mrow=[]; lrow=[]; crow=[]
    for mk in markets:
        full,(bl,bc),c0=best(Xi[si],Ydf[mk])
        mrow.append(bc); lrow.append(bl); crow.append(c0)
        if bc is not None and bl is not None and abs(bc)>=0.12:
            chains.append({'signal':si,'market':mk,'lag':bl,'r':bc,'contemp':c0})
    matrix.append(mrow); lagmat.append(lrow); contemp.append(crow)

chains.sort(key=lambda x:-abs(x['r']))
# domain tagging
def domain(s):
    for p,d in [('SHIP_','Shipping'),('WAR_','War/Conflict'),('NEWS_','News'),('ATTN_','Attention'),
                ('UNC_','Uncertainty'),('QUAKE_','Earthquakes'),('SPACE_','Space weather'),
                ('CLIMATE_','Climate'),('WX_','Weather')]:
        if s.startswith(p): return d
    return 'Other'
for ch in chains: ch['domain']=domain(ch['signal'])

out={'meta':{'signals':len(signals),'markets':len(markets),'pairs':len(signals)*len(markets),
             'start':'2023-01-01','end':'2026-08-08'},
     'signals':signals,'markets':markets,
     'matrix':matrix,'lagmat':lagmat,'contemp':contemp,
     'chains':chains[:40]}
# domain-level: max |r| any market, per domain
dom={}
for si in signals:
    d=domain(si)
    row=[matrix[signals.index(si)][j] for j in range(len(markets))]
    mx=max([abs(v) for v in row if v is not None]+[0])
    dom.setdefault(d,[]).append(mx)
out['domain_strength']={d:round(float(np.mean(v)),3) for d,v in dom.items()}
json.dump(out,open('findings2.json','w'),indent=1)

print("\n=== TOP CROSS-DOMAIN BUTTERFLY CHAINS (signal leads market) ===")
for ch in chains[:22]:
    print(f"  [{ch['domain']:<13}] {ch['signal']:<24} --{ch['lag']:+d}d--> {ch['market']:<10} r={ch['r']:+.2f}")
print("\n=== DOMAIN PREDICTIVE STRENGTH (avg best |r| across markets) ===")
for d,v in sorted(out['domain_strength'].items(),key=lambda x:-x[1]):
    print(f"  {d:<15} {v:.2f}")
print("\nwrote findings2.json, signals.parquet")
