"""Baseline next-day S&P direction model — walk-forward LightGBM.

Runs on DGXSEC against the locally restored datalake at /opt/bucket_restore
(mirror of the market-data Storj bucket). Purpose: prove the train→backtest
loop end-to-end and set an honest baseline. Result on 2,388 OOS days:
accuracy 51.9% / AUC 0.516, long-flat Sharpe 0.41 — i.e. naive daily index
timing has ~no durable edge. Use this as the floor the real models must beat
(cross-sectional ranking, multi-horizon, regime-aware — see ../examples/ml_plan.html).

    /opt/quant/venv/bin/python baseline.py
"""
import glob, warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
R = '/opt/bucket_restore'

def load(ds, sym):
    f = glob.glob(f'{R}/{ds}/**/symbol={sym}/*.parquet', recursive=True)
    if not f:
        return None
    d = pd.read_parquet(f[0])
    d['date'] = pd.to_datetime(d['date']).dt.tz_localize(None).dt.normalize()
    s = d.set_index('date')['close'].astype(float).sort_index()
    return s[~s.index.duplicated(keep='last')]

A = {'SPX': ('world_indices', 'sp500_us'), 'NDX': ('world_indices', 'nasdaq_us'),
     'VIX': ('vix_complex', 'vix'), 'WTI': ('commodities', 'wti_oil'),
     'Gold': ('commodities', 'gold'), 'DXY': ('commodities', 'dollar_index'),
     'Copper': ('commodities', 'copper'), 'HYG': ('bonds_credit', 'hyg_high_yield'),
     'TLT': ('bonds_credit', 'tlt_20y_treasury'), 'BTC': ('crypto', 'bitcoin')}
px = {k: load(*v) for k, v in A.items()}
px = {k: v for k, v in px.items() if v is not None}
P = pd.DataFrame(px)
P = P.reindex(P['SPX'].dropna().index).ffill(limit=3)   # trade on SPX days
ret = P.pct_change()

F = pd.DataFrame(index=P.index)
for l in [1, 2, 3, 5, 10]:
    F[f'SPX_r{l}'] = ret['SPX'].shift(l - 1)            # past returns incl. t
F['SPX_vol10'] = ret['SPX'].rolling(10).std()
F['SPX_mom20'] = P['SPX'].pct_change(20)
F['SPX_ma_dist'] = P['SPX'] / P['SPX'].rolling(50).mean() - 1
F['VIX_lvl'] = P['VIX']; F['VIX_chg'] = ret['VIX']; F['VIX_chg5'] = P['VIX'].pct_change(5)
for k in ['NDX', 'WTI', 'Gold', 'DXY', 'Copper', 'HYG', 'TLT', 'BTC']:
    if k in ret:
        F[f'{k}_r'] = ret[k]
F['dow'] = F.index.dayofweek

y = (ret['SPX'].shift(-1) > 0).astype(int)               # next-day direction
fwd = ret['SPX'].shift(-1)                                # next-day return
data = F.join(y.rename('y')).join(fwd.rename('fwd')).dropna()
Xcols = list(F.columns)

import lightgbm as lgb
from sklearn.metrics import accuracy_score, roc_auc_score

preds = []
start, step = 600, 21                                     # warmup, retrain cadence
for i in range(start, len(data) - 1, step):
    tr, te = data.iloc[:i], data.iloc[i:i + step]
    m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.02, num_leaves=31,
                           subsample=0.8, colsample_bytree=0.8, min_child_samples=40,
                           reg_lambda=1.0, verbose=-1)
    m.fit(tr[Xcols], tr['y'])
    p = m.predict_proba(te[Xcols])[:, 1]
    preds.append(pd.DataFrame({'p': p, 'y': te['y'].values, 'fwd': te['fwd'].values}, index=te.index))

Rd = pd.concat(preds)
acc = accuracy_score(Rd['y'], (Rd['p'] > 0.5).astype(int))
auc = roc_auc_score(Rd['y'], Rd['p'])
pos = (Rd['p'] > 0.5).astype(float)
turn = pos.diff().abs().fillna(pos)
strat = pos * Rd['fwd'] - 0.0005 * turn                   # 5 bp cost per turnover
sharpe = lambda x: np.sqrt(252) * x.mean() / (x.std() + 1e-9)
print(f"OOS {Rd.index.min().date()}..{Rd.index.max().date()} n={len(Rd)}")
print(f"direction  ACC={acc:.4f}  AUC={auc:.4f}")
print(f"long/flat  Sharpe={sharpe(strat):.2f}  cumret={(1 + strat).prod() - 1:+.1%}")
print(f"buy&hold   Sharpe={sharpe(Rd['fwd']):.2f}  cumret={(1 + Rd['fwd']).prod() - 1:+.1%}")
