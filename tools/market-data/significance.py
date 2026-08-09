import io,json,warnings,numpy as np,pandas as pd,pyarrow.parquet as pq
warnings.filterwarnings('ignore'); np.random.seed(42)
from s3lib import client
c=client(); B='market-data'
def rd(k):
    b=c.get_object(Bucket=B,Key=k)['Body'].read()
    return pq.ParquetFile(io.BytesIO(b)).read().to_pandas()
def nd(s): return pd.to_datetime(s,errors='coerce',utc=True).dt.tz_localize(None).dt.normalize()
IDX=pd.date_range('2023-01-01','2026-08-08',freq='D')
def daily(s): s=s[~s.index.duplicated(keep='last')].sort_index(); return s.reindex(IDX)

# ---- rebuild market targets Y (same as cross_domain) ----
P=pd.read_parquet('panel.parquet'); P.index=pd.to_datetime(P.index)
Yr={}
for col in ['SPX','NDX','RUT','HangSeng','Nikkei','DAX','WTI','Brent','Gold','Copper','NatGas','Wheat','DXY','USDJPY','BTC','HYG','SEC_energy','SEC_materials']:
    if col in P: Yr[col]=daily(P[col]).pct_change()
Yr['VIX']=daily(P['VIX']).diff(); Yr['UST10Y']=daily(P['UST10Y']).diff()
pre='source=yfinance/symbol='
def closes(k): d=rd(k); d['date']=nd(d['date']); return daily(d.set_index('date')['close'].astype(float))
try: Yr['Defense']=closes(f'defense/{pre}aerospace_def_etf/aerospace_def_etf.parquet').pct_change()
except: pass
try:
    air=[closes(f'travel/{pre}{s}/{s}.parquet') for s in ['delta','united','american_air']]
    Yr['Airlines']=pd.concat(air,axis=1).mean(axis=1).pct_change()
except: pass
try: Yr['AgStocks']=closes(f'agriculture/{pre}corn_etf/corn_etf.parquet').pct_change()
except: pass
try: Yr['Soybeans']=closes(f'commodities_broad/{pre}soybeans/soybeans.parquet').pct_change()
except: pass
try: Yr['Corn']=closes(f'commodities_broad/{pre}corn/corn.parquet').pct_change()
except: pass
Ydf=pd.DataFrame(Yr)

# ---- signals -> innovations + sparsity ----
X=pd.read_parquet('signals.parquet'); X.index=pd.to_datetime(X.index)
def innov(s): d=s.diff(); return (d-d.mean())/d.std()
Xi=pd.DataFrame({k:innov(X[k]) for k in X.columns})
active={k: float((X[k].diff().abs()>1e-9).mean()) for k in X.columns}   # fraction of days the signal actually moves

LAGS=list(range(1,11))
def best_lead(x,y):
    best=0.0;bl=0
    for k in LAGS:
        a=x[:-k]; b=y[k:]
        m=~(np.isnan(a)|np.isnan(b))
        if m.sum()>60:
            r=np.corrcoef(a[m],b[m])[0,1]
            if abs(r)>abs(best): best=r;bl=k
    return best,bl
def boot_p(x,y,obs,M=500):
    N=len(x); cnt=1
    for _ in range(M):
        r,_=best_lead(np.roll(x,np.random.randint(5,N-5)),y)
        if abs(r)>=abs(obs): cnt+=1
    return cnt/(M+1)

signals=list(Xi.columns); markets=list(Ydf.columns)
def dom(s):
    for p,d in [('SHIP_','Shipping'),('WAR_','War/Conflict'),('NEWS_','News'),('ATTN_','Attention'),
                ('UNC_','Uncertainty'),('QUAKE_','Earthquakes'),('SPACE_','Space weather'),
                ('CLIMATE_','Climate'),('WX_','Weather')]:
        if s.startswith(p): return d
    return 'Other'

chains=[]
for si in signals:
    xa=Xi[si].values
    for mk in markets:
        ya=Ydf[mk].values
        r,bl=best_lead(xa,ya)
        if abs(r)>=0.10:
            chains.append({'signal':si,'market':mk,'lag':bl,'r':round(float(r),3),
                           'domain':dom(si),'active':round(active[si],2)})
# bootstrap p for each candidate
for ch in chains:
    ch['p']=round(boot_p(Xi[ch['signal']].values, Ydf[ch['market']].values, ch['r']),3)
    ch['robust']= (ch['p']<0.05) and (ch['active']>=0.5) and (abs(ch['r'])>=0.12)
chains.sort(key=lambda x:(not x['robust'], -abs(x['r'])))

robust=[c for c in chains if c['robust']]
spurious=[c for c in chains if not c['robust']]
# domain robust strength
dm={}
for c in chains:
    dm.setdefault(c['domain'],{'robust':0,'tested':0,'maxr':0})
    dm[c['domain']]['tested']+=1
    dm[c['domain']]['robust']+= 1 if c['robust'] else 0
    dm[c['domain']]['maxr']=max(dm[c['domain']]['maxr'],abs(c['r']))

out=json.load(open('findings2.json'))
out['sig_meta']={'bootstrap':500,'rule':'p<0.05 (circular-rotation null) AND signal moves >=50% of days AND |r|>=0.12',
                 'n_candidates':len(chains),'n_robust':len(robust)}
out['robust_chains']=robust[:30]
out['spurious_examples']=sorted(spurious,key=lambda x:-abs(x['r']))[:12]
out['domain_verdict']=dm
out['active']={k:round(v,2) for k,v in active.items()}
json.dump(out,open('findings2.json','w'),indent=1)

print(f"candidates(|r|>=.10): {len(chains)} | robust: {len(robust)}")
print("\n=== ROBUST butterfly chains (survive bootstrap + not sparse) ===")
for c in robust[:20]:
    print(f"  [{c['domain']:<13}] {c['signal']:<24} --{c['lag']:+d}d--> {c['market']:<11} r={c['r']:+.2f} p={c['p']:.3f} act={c['active']:.2f}")
print("\n=== MIRAGES rejected (high r, fail bootstrap or sparse) ===")
for c in out['spurious_examples'][:10]:
    why='sparse' if c['active']<0.5 else ('p=%.2f'%c['p'])
    print(f"  [{c['domain']:<13}] {c['signal']:<22} -> {c['market']:<11} r={c['r']:+.2f}  REJECT({why})")
print("\n=== DOMAIN VERDICT (robust/tested, maxr) ===")
for d,v in sorted(dm.items(),key=lambda x:-x[1]['robust']):
    print(f"  {d:<15} robust {v['robust']}/{v['tested']:<3} maxr={v['maxr']:.2f}")
PY_DONE=1
print("\nwrote findings2.json (enriched)")
