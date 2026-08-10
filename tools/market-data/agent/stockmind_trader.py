#!/usr/bin/env python3
"""BITFIN autonomous hourly paper-trader with a learning loop. *** SIMULATION ONLY ***"""
import os, sys, json, glob, time, datetime as dt, urllib.request
import pandas as pd
SIMULATION_ONLY = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import live as _live
except Exception:
    _live = None
def _load_env(p):
    if os.path.exists(p):
        for ln in open(p):
            ln = ln.strip()
            if ln and not ln.startswith('#') and '=' in ln:
                k, v = ln.split('=', 1); os.environ.setdefault(k, v.strip())
_load_env(os.path.join(HERE,'secrets.env'))
CFG = json.load(open(os.path.join(HERE,'config.json')))
DATA_DIR=CFG.get('data_dir','/opt/bucket_restore'); STATE=os.path.join(HERE,'state.json'); JOURNAL=os.path.join(HERE,'journal.jsonl')
GATEWAY=os.environ.get('GATEWAY_URL',CFG.get('gateway_url')); GKEY=os.environ.get('GATEWAY_KEY','')
MODEL=CFG.get('model','auto'); COST=CFG.get('cost_bps',5)/1e4
MAX_GROSS=CFG.get('max_gross',1.5); MAX_NAME=CFG.get('max_name',0.25); CAPITAL=CFG.get('capital',10000); UNIVERSE=CFG['universe']
def log(m): print(f"[{dt.datetime.now(dt.UTC).isoformat(timespec='seconds')}] {m}", flush=True)
def now(): return dt.datetime.now(dt.UTC).isoformat(timespec='seconds').replace('+00:00','Z')
def series(ds,sym):
    fs=glob.glob(f'{DATA_DIR}/{ds}/**/symbol={sym}/*.parquet',recursive=True)
    if not fs: return None
    d=pd.read_parquet(fs[0]); d['date']=pd.to_datetime(d['date']).dt.tz_localize(None).dt.normalize()
    s=d.set_index('date')['close'].astype(float).sort_index(); return s[~s.index.duplicated(keep='last')]
def _rp(s,n): return round((s.iloc[-1]/s.iloc[-1-n]-1)*100,2) if len(s)>n else None
def snapshot():
    snap,prices,above,n,asof={},{},0,0,None
    for tkr,(ds,sym) in UNIVERSE.items():
        s=series(ds,sym)
        if s is None or len(s)<160: continue
        last=float(s.iloc[-1]); asof=s.index[-1].date()
        mark=last
        if _live is not None:
            try:
                _ov=_live.live_price(tkr,s.index[-1],last)
                if _ov: mark=_ov['px']
            except Exception: pass
        prices[tkr]=mark
        ma150=s.rolling(150).mean().iloc[-1]; ma50=s.rolling(50).mean().iloc[-1]
        snap[tkr]={'px':round(last,2),'r1':_rp(s,1),'r5':_rp(s,5),'r20':_rp(s,20),'vs50':round((last/ma50-1)*100,1),'vs150':round((last/ma150-1)*100,1),'vol20':round(s.pct_change().tail(20).std()*100,2)}
        n+=1; above+=1 if last>ma150 else 0
    ctx={'asof':str(asof),'universe':n,'breadth_pct_above150':round(100*above/max(n,1))}
    vix=series('vix_complex','vix')
    if vix is not None: ctx['VIX']=round(float(vix.iloc[-1]),2)
    hyg=series('bonds_credit','hyg_high_yield')
    if hyg is not None: ctx['HYG_vs150']=round((hyg.iloc[-1]/hyg.rolling(150).mean().iloc[-1]-1)*100,1)
    return snap,prices,ctx
def load_state():
    if os.path.exists(STATE): return json.load(open(STATE))
    return {'cash':CAPITAL,'positions':{},'equity0':CAPITAL,'cycles':0,'created':now()}
def journal_tail(k=8):
    if not os.path.exists(JOURNAL): return []
    out=[]
    for ln in open(JOURNAL):
        ln=ln.strip()
        if ln:
            try: out.append(json.loads(ln))
            except Exception: pass
    return out[-k:]
def equity(st,prices):
    v=st['cash']
    for t,p in st['positions'].items(): v+=p['qty']*prices.get(t,p['avg'])
    return v
def rebalance(st,targets,prices):
    eq=equity(st,prices); fills=[]
    tw={t:max(-MAX_NAME,min(MAX_NAME,float(w))) for t,w in targets.items() if t in prices}
    gross=sum(abs(w) for w in tw.values())
    if gross>MAX_GROSS: tw={t:w*MAX_GROSS/gross for t,w in tw.items()}
    for t in list(st['positions'])+list(tw):
        if t not in prices: continue
        px=prices[t]; cur=st['positions'].get(t,{}).get('qty',0.0); tgt=tw.get(t,0.0)*eq/px; dq=tgt-cur
        if abs(dq*px)<eq*0.01: continue
        st['cash']-=dq*px+abs(dq*px)*COST
        if abs(tgt)<1e-9: st['positions'].pop(t,None)
        else: st['positions'][t]={'qty':tgt,'avg':px}
        fills.append({'t':t,'dqty':round(dq,4),'px':px,'side':'BUY' if dq>0 else 'SELL'})
    return fills,eq
def ask_brain(snap,ctx,st,prices,memory):
    if not GKEY: return None,'no gateway key set'
    port={t:round(p['qty']*prices.get(t,p['avg'])/max(equity(st,prices),1),3) for t,p in st['positions'].items()}
    sysmsg=("You are a disciplined systematic PM running a LONG/SHORT paper book, and you LEARN from your own track record. "
            "You receive a market snapshot, your current weights, and your recent decisions with their realized P&L. Reflect on what worked, then decide TARGET WEIGHTS for the next hour. "
            f"Rules: long positive, short negative; |per-name|<={MAX_NAME}; sum|weights|<={MAX_GROSS} (rest cash). Prefer names above 150d MA; de-risk when breadth weak, VIX high, or HYG below 150d MA. "
            "Avoid needless churn — every trade costs 5bp, so only move weights when your view changes. "
            "Return STRICT JSON only: {\"targets\":{\"TICKER\":weight},\"thesis\":\"...\",\"reflection\":\"what you learned from recent P&L\",\"risk\":\"...\"}. No prose.")
    usr=json.dumps({'context':ctx,'assets':snap,'current_weights':port,'recent_history':memory,'tickers':list(prices)},separators=(',',':'))
    last='no response'
    for m in [MODEL]+[x for x in CFG.get('fallback_models',['minimax-m3','gemini-3.5-flash','glm-4.7']) if x!=MODEL]:
        body=json.dumps({'model':m,'temperature':0.3,'max_tokens':800,'stream':False,'messages':[{'role':'system','content':sysmsg},{'role':'user','content':usr}]}).encode()
        req=urllib.request.Request(GATEWAY.rstrip('/')+'/v1/chat/completions',data=body,headers={'Authorization':f'Bearer {GKEY}','Content-Type':'application/json'})
        try:
            raw=urllib.request.urlopen(req,timeout=90).read()
            if not raw: last=f'{m}:empty'; continue
            txt=(json.loads(raw)['choices'][0]['message'].get('content') or '')
            i,j=txt.find('{'),txt.rfind('}')
            if i>=0:
                dec=json.loads(txt[i:j+1])
                if isinstance(dec.get('targets'),dict): return dec,m
            last=f'{m}:no-targets'
        except Exception as e: last=f'{m}:{type(e).__name__}'
    return None,f'brain error: {last}'
def rule_fallback(snap,ctx):
    risk_off=(ctx.get('breadth_pct_above150',50)<30) or (ctx.get('VIX',15)>25) or (ctx.get('HYG_vs150',0)<0)
    picks={t:d['r20'] for t,d in snap.items() if d.get('vs150',-9)>0 and (d.get('r20') or 0)>0}; tw={}
    if picks:
        top=sorted(picks,key=picks.get,reverse=True)[:8]; budget=0.5 if risk_off else 0.9; s=sum(picks[t] for t in top) or 1
        for t in top: tw[t]=round(min(MAX_NAME,budget*picks[t]/s),3)
    if 'GLD' in snap: tw['GLD']=round(min(MAX_NAME,tw.get('GLD',0)+(0.2 if risk_off else 0.12)),3)
    return {'targets':tw,'thesis':f"rule-based ({'risk-off' if risk_off else 'risk-on'} trend-follow)",'reflection':'(deterministic rule — no learning)','risk':'fallback brain'}
def cycle():
    st=load_state(); snap,prices,ctx=snapshot()
    if not prices: log('no prices — datalake unreachable'); return
    hist=journal_tail(8)
    memory=[{'ts':r.get('ts'),'ret_pct':r.get('ret_total_pct'),'cycle_pnl':r.get('cycle_pnl'),'brain':r.get('brain'),'thesis':(r.get('thesis') or '')[:100]} for r in hist]
    prev_eq=hist[-1]['equity'] if hist else st.get('equity0',CAPITAL)
    dec,brain=ask_brain(snap,ctx,st,prices,memory)
    if dec is None:
        log(f"AI brain unavailable ({brain}); rule fallback"); dec,brain=rule_fallback(snap,ctx),'rule-fallback'
    fills,_=rebalance(st,dec.get('targets',{}),prices)
    st['cycles']+=1; eq1=equity(st,prices); json.dump(st,open(STATE,'w'),indent=1)
    rec={'ts':now(),'asof':ctx.get('asof'),'brain':brain,'equity':round(eq1,2),'cycle_pnl':round(eq1-prev_eq,2),
         'ret_total_pct':round((eq1/st['equity0']-1)*100,2),'cash_pct':round(100*st['cash']/max(eq1,1)),'n_pos':len(st['positions']),
         'breadth':ctx.get('breadth_pct_above150'),'VIX':ctx.get('VIX'),'HYG_vs150':ctx.get('HYG_vs150'),
         'fills':fills,'thesis':dec.get('thesis',''),'reflection':dec.get('reflection',''),'risk':dec.get('risk','')}
    try:
        import ledger; rec=ledger.seal(rec, ledger.head_hash(JOURNAL))
    except Exception as _e:
        log(f'ledger seal skipped: {type(_e).__name__}')
    open(JOURNAL,'a').write(json.dumps(rec)+'\n')
    log(f"[SIM] cycle {st['cycles']} | brain={brain} | equity=${eq1:,.0f} ({rec['ret_total_pct']:+.2f}%) | pnl ${rec['cycle_pnl']:+.2f} | {len(st['positions'])} pos | fills {len(fills)}")
    if rec['reflection']: log(f"       learned: {rec['reflection'][:120]}")
def main():
    assert SIMULATION_ONLY
    if '--loop' in sys.argv:
        iv=int(sys.argv[sys.argv.index('--loop')+1]); log(f"BITFIN loop every {iv}s — SIMULATION ONLY")
        while True:
            try: cycle()
            except Exception as e: log(f"cycle error: {type(e).__name__}: {e}")
            time.sleep(iv)
    else: cycle()
if __name__=='__main__': main()
