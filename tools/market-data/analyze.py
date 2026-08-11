import io,json,warnings,numpy as np,pandas as pd,pyarrow.parquet as pq
warnings.filterwarnings('ignore')
from s3lib import client
c=client(); B='market-data'
P=pd.read_parquet('panel.parquet'); P.index=pd.to_datetime(P.index)
# add Cape of Good Hope (diversion route) for the Red Sea story
try:
    d=pq.ParquetFile(io.BytesIO(c.get_object(Bucket=B,Key='chokepoints/source=imf_portwatch/chokepoint=chokepoint7/chokepoint7.parquet')['Body'].read())).read().to_pandas()
    d['date']=pd.to_datetime(d['date']).dt.normalize()
    P['SHIP_CapeGoodHope']=d.set_index('date')['n_container'].astype(float).reindex(P.index)
except Exception as e: print("cape miss",e)

PRICE=['SPX','NDX','RUT','HangSeng','Nikkei','DAX','EuroStoxx','CAC','FTSE','China_MSCI','China_Internet','Alibaba',
 'SEC_tech','SEC_energy','SEC_financials','SEC_industrials','SEC_materials','SEC_utilities','SEC_healthcare',
 'SEC_cons_staples','SEC_cons_discretionary','SEC_real_estate','SEC_comm_services',
 'HYG','LQD','TLT','IEF','WTI','Brent','Gold','Copper','DXY','NatGas','Wheat','USDJPY','USDCNY','USDEUR','BTC','ETH']
LEVEL=['VIX','VIX9D','VIX3M','VVIX','MOVE','UST2Y','UST10Y','UST_2s10s']

ret=P[PRICE].pct_change()
lvchg=P[LEVEL].diff()
out={'meta':{'rows':int(P.shape[0]),'cols':int(P.shape[1]),'start':str(P.index.min().date()),'end':str(P.index.max().date())}}

# ---------- 1. Correlation matrix (returns/level-changes) ----------
HEAT=['SPX','NDX','RUT','HangSeng','Nikkei','DAX','China_Internet','SEC_tech','SEC_energy',
      'WTI','Brent','Gold','Copper','DXY','HYG','TLT','UST10Y','VIX','BTC','ETH','USDJPY','USDCNY','NatGas','Wheat']
M=pd.concat([ret,lvchg],axis=1)[HEAT].dropna(how='all')
cm=M.corr(min_periods=200).round(3)
out['corr']={'labels':HEAT,'matrix':cm.reindex(index=HEAT,columns=HEAT).values.tolist()}
# strongest pairs
pairs=[]
for i in range(len(HEAT)):
    for j in range(i+1,len(HEAT)):
        v=cm.iloc[i,j]
        if pd.notna(v): pairs.append((HEAT[i],HEAT[j],float(v)))
pairs.sort(key=lambda x:-abs(x[2]))
out['top_corr']=[{'a':a,'b':b,'r':round(r,3)} for a,b,r in pairs[:15]]

# ---------- 2. Systemic co-movement (rolling avg pairwise corr of equities) ----------
EQ=['SPX','NDX','RUT','HangSeng','Nikkei','DAX','EuroStoxx','CAC','FTSE']
er=ret[EQ]
def avg_pairwise(win):
    res={}
    for dt in er.index[::5]:
        w=er.loc[:dt].tail(win)
        if w.dropna(how='all').shape[0]>=win*0.6:
            cc=w.corr(); n=len(EQ)
            vals=cc.values[np.triu_indices(n,1)]
            vals=vals[~np.isnan(vals)]
            if len(vals): res[dt]=float(np.nanmean(vals))
    return pd.Series(res)
sysc=avg_pairwise(42)
out['syscorr']={'dates':[str(d.date()) for d in sysc.index],'vals':[round(v,3) for v in sysc.values]}

# ---------- 3. Crisis timeline: SPX drawdown + VIX (weekly) ----------
spx=P['SPX'].dropna()
dd=(spx/spx.cummax()-1)*100
wk=P.resample('W').last()
out['timeline']={
 'dates':[str(d.date()) for d in wk.index],
 'spx':[None if pd.isna(v) else round(v,1) for v in (wk['SPX']/spx.iloc[0]*100)],
 'vix':[None if pd.isna(v) else round(v,2) for v in wk['VIX']],
 'dd':[None if pd.isna(v) else round(v,2) for v in (wk['SPX']/spx.cummax().reindex(wk.index)-1)*100],
 'redsea':[None if pd.isna(v) else round(v,1) for v in wk['SHIP_RedSea_BabMandeb']],
 'cape':[None if pd.isna(v) else round(v,1) for v in wk.get('SHIP_CapeGoodHope',pd.Series(index=wk.index))],
 'newscrash':[None if pd.isna(v) else round(v,1) for v in wk['NEWS_stock_market_crash']],
}

# ---------- 4. Lead-lag cross-correlation (butterfly effect) ----------
def xcorr(x,y,maxlag=10):
    x=x.replace([np.inf,-np.inf],np.nan).reindex(P.index)
    y=y.replace([np.inf,-np.inf],np.nan).reindex(P.index)
    df=pd.concat([x.rename('x'),y.rename('y')],axis=1)
    res=[]
    for k in range(-maxlag,maxlag+1):
        r=df['x'].corr(df['y'].shift(-k))  # k>0: x leads y by k days
        res.append((k,None if pd.isna(r) else round(float(r),3)))
    valid=[r for r in res if r[1] is not None]
    best=max(valid,key=lambda t:abs(t[1])) if valid else (0,None)
    return {'lags':[k for k,_ in res],'corr':[v for _,v in res],'best_lag':best[0],'best_corr':best[1]}

redsea_chg=P['SHIP_RedSea_BabMandeb'].diff(7)               # weekly shipping change (disruption<0)
ship_glob=P['SHIP_Global'].diff(7)
news_crash=P['NEWS_stock_market_crash']
conflict=P['CONFLICT_intensity']
LL={}
LL['RedSeaShip -> Brent']      = xcorr(redsea_chg, P['Brent'].pct_change())
LL['RedSeaShip -> China(HangSeng)']= xcorr(redsea_chg, ret['HangSeng'])
LL['RedSeaShip -> Wheat']      = xcorr(redsea_chg, P['Wheat'].pct_change())
LL['GlobalShip -> NatGas']     = xcorr(ship_glob, P['NatGas'].pct_change())
LL['CrashNews -> SPX']         = xcorr(news_crash, ret['SPX'])
LL['CrashNews -> VIX']         = xcorr(news_crash, P['VIX'].diff())
LL['Conflict -> Oil(Brent)']   = xcorr(conflict, P['Brent'].pct_change())
LL['Conflict -> Gold']         = xcorr(conflict, P['Gold'].pct_change())
LL['Conflict -> VIX']          = xcorr(conflict, P['VIX'].diff())
out['leadlag']=LL

# ---------- 5. Event studies ----------
EVENTS=[('SVB collapse','2023-03-10'),('Israel–Hamas war','2023-10-09'),
        ('Red Sea shipping halt','2023-12-18'),('Yen carry unwind','2024-08-05')]
ASSETS=['SPX','HangSeng','VIX','WTI','Brent','Gold','DXY','UST10Y','BTC','TLT']
ev=[]
for nm,ds in EVENTS:
    d0=pd.Timestamp(ds); row={'name':nm,'date':ds,'moves':{}}
    for a in ASSETS:
        s=P[a].dropna()
        pre=s.asof(d0-pd.Timedelta(days=3)); post=s.asof(d0+pd.Timedelta(days=5))
        if pd.notna(pre) and pd.notna(post) and pre!=0:
            row['moves'][a]= round((post-pre) if a in ('VIX','UST10Y') else (post/pre-1)*100, 2)
    ev.append(row)
out['events']=ev

# ---------- 6. Safe-haven vs risk in stress days ----------
stress=ret['SPX']< ret['SPX'].quantile(0.05)   # worst 5% SPX days
sh={}
for a in ['Gold','TLT','DXY','VIX','BTC','WTI','USDJPY']:
    if a=='VIX': sh[a]=round(float(P['VIX'].diff()[stress].mean()),2)
    else: sh[a]=round(float(ret[a][stress].mean()*100),2) if a in ret else None
out['safehaven']={'desc':'avg move on worst-5% SPX days','vals':sh,'n_days':int(stress.sum())}

json.dump(out,open('findings.json','w'),indent=1)
# ---- print summary ----
print("=== TOP CORRELATIONS (returns) ===")
for p in out['top_corr'][:10]: print(f"  {p['a']:>14} ~ {p['b']:<14} r={p['r']:+.2f}")
print("\n=== LEAD-LAG (butterfly): +lag = signal LEADS asset ===")
for k,v in LL.items(): print(f"  {k:<34} best_lag={v['best_lag']:+d}d  r={v['best_corr']:+.2f}")
print("\n=== EVENT STUDIES ([-3d..+5d] move) ===")
for e in ev:
    print(f"  {e['name']} ({e['date']}): "+", ".join(f"{a}{'+' if e['moves'].get(a,0)>=0 else ''}{e['moves'].get(a)}" for a in ['SPX','HangSeng','VIX','Brent','Gold'] if a in e['moves']))
print("\n=== SAFE-HAVEN on worst-5% SPX days (n=%d) ==="%out['safehaven']['n_days'])
for a,v in sh.items(): print(f"  {a:<8} {v:+}")
print("\nsyscorr now=%.2f  (range %.2f..%.2f)"%(sysc.values[-1],np.nanmin(sysc.values),np.nanmax(sysc.values)))
print("wrote findings.json")
