"""Track the STOCKMIND tactical portfolio: pull latest datalake prices and
compute P&L since entry vs the VOO benchmark. Run any day to see the book.

    python3 track_portfolio.py            # uses portfolio.json
"""
import io,json,sys,pandas as pd,pyarrow.parquet as pq
from s3lib import client
c=client(); B='market-data'
def close(ds,sym,asof=None):
    ks=[o['Key'] for o in c.list_objects_v2(Bucket=B,Prefix=f'{ds}/').get('Contents',[]) if f'symbol={sym}/' in o['Key']]
    b=c.get_object(Bucket=B,Key=ks[0])['Body'].read()
    d=pq.ParquetFile(io.BytesIO(b)).read().to_pandas()
    d['date']=pd.to_datetime(d['date']).dt.tz_localize(None).dt.normalize()
    s=d.set_index('date')['close'].astype(float).sort_index()
    return (s.asof(pd.Timestamp(asof)) if asof else s.iloc[-1]), s.index[-1].date()

P=json.load(open(sys.argv[1] if len(sys.argv)>1 else 'portfolio.json'))
tot0=P['account_usd']; totv=0; rows=[]
for p in P['positions']:
    now,asof=close(*p['sleeve'])
    r=now/p['entry']-1; val=p['usd']*(1+r); totv+=val
    rows.append((p['etf'],p['weight']*100,p['usd'],p['entry'],round(now,2),r*100,round(val,2)))
spx_now,_=close('world_indices','sp500_us'); spx0,_=close('world_indices','sp500_us',P['entry_date'])
bench=spx_now/spx0-1
print(f"=== {P['name']} | entry {P['entry_date']} → data {asof} ===")
print(f"{'ETF':<6}{'w%':>5}{'$in':>7}{'entry':>11}{'now':>11}{'ret%':>8}{'value':>10}")
for e,w,u,en,nw,rr,vl in rows:
    print(f"{e:<6}{w:>5.0f}{u:>7.0f}{en:>11.2f}{nw:>11.2f}{rr:>+8.2f}{vl:>10.2f}")
port_ret=totv/tot0-1
print(f"\nPORTFOLIO  ${tot0:,.0f} -> ${totv:,.2f}   {port_ret*100:+.2f}%")
print(f"BENCHMARK  VOO/SPX buy&hold        {bench*100:+.2f}%")
print(f"ALPHA vs VOO                       {(port_ret-bench)*100:+.2f}%")
