#!/usr/bin/env python3
"""BITFIN Academy — an AI-guided learning layer over the datalake.

Explains every dataset and factor we collect, draws live charts of any series,
and answers free-form questions via the LLM gateway — grounded in the catalog
and current market context. Teaching, not just a trading screen.
"""
import os, sys, glob, json, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
_AG = os.environ.get('BITFIN_AGENT_DIR') or next(
    (d for d in [os.path.join(os.path.dirname(HERE), 'agent'), '/opt/quant/agent_trader']
     if os.path.exists(os.path.join(d, 'stockmind_trader.py'))), HERE)
sys.path.insert(0, _AG)
from stockmind_trader import GATEWAY, GKEY, DATA_DIR  # noqa
import pandas as pd

# curated catalog: category -> [(dataset, one-line description)]
CATALOG = {
 'Equities': [
   ('sp500_stocks', 'Every S&P 500 stock — 503 names, daily OHLCV back to 2002. The core universe.'),
   ('sectors', 'The 11 SPDR sector ETFs (XLK tech, XLE energy, XLV health…). Rotation lives here.'),
   ('world_indices', 'Global stock indices (S&P, Nasdaq, DAX, Nikkei, Hang Seng…).'),
   ('israel_stocks', 'Israeli names (Wix, etc.) — local-market exposure.'),
   ('defense', 'Defense contractors (Lockheed, Raytheon…) — react to war/geopolitics.'),
   ('travel', 'Airlines & hotels — react to disease/terror/demand shocks.')],
 'Options & Volatility': [
   ('options_history', 'Full historical option chains — 10.5M rows/month (strike, type, bid/ask, expiry).'),
   ('vix_complex', 'The VIX term structure (VIX, 9-day, 3-month, VVIX) — the market’s fear gauge.'),
   ('vol_products', 'Volatility ETPs. breadth: how many stocks participate in a move.'),
   ('breadth', 'Market breadth — the % of stocks above their moving average. Narrow rallies are fragile.')],
 'Rates & Credit': [
   ('treasury_curve_rich', 'The full US Treasury yield curve (1mo→30yr). Its shape signals the cycle.'),
   ('gov_bond_yields', '240 global government-bond yield symbols.'),
   ('bonds_credit', 'Credit & duration ETFs — HYG (junk), LQD (IG), TLT (long Treasuries), MOVE (bond vol).')],
 'Macro': [
   ('macro_fred_rich', 'FRED macro series (WTI, unemployment, CPI proxies…) back to 1990.'),
   ('consumer_credit', 'US consumer-credit series.'),
   ('eia_full', 'US energy inventories & production.'),
   ('uncertainty', 'Daily economic-policy-uncertainty & risk-on/risk-off indices.')],
 'FX & Crypto': [
   ('currencies', 'Major USD pairs (JPY, EUR, CNY…) + the dollar index.'),
   ('fx_shekel', 'Shekel crosses (USD/ILS, EUR/ILS…).'),
   ('crypto', 'Bitcoin, Ethereum and majors — the risk-appetite thermometer.')],
 'Commodities': [
   ('commodities', 'Oil (WTI/Brent), gold, copper, silver, the dollar index.'),
   ('commodities_broad', 'Grains, natural gas, softs (wheat, corn, coffee…).')],
 'Alt-data (the edge)': [
   ('gdelt', 'GDELT global news/event volume — attention on crashes, shortages, ports.'),
   ('geopolitics', 'Prediction markets (Polymarket, Kalshi) + Wikipedia geopolitical attention.'),
   ('chokepoints', 'IMF PortWatch ship transits through 28 straits — incl. Bab el-Mandeb (Red Sea).'),
   ('weather', 'Open-Meteo weather for commodity regions (Permian oil, grain belts).'),
   ('earthquakes', 'USGS earthquakes (M5+) — a disaster signal.'),
   ('cftc_positioning', 'CFTC Commitments of Traders — who is positioned where (134 columns).'),
   ('attention_wikipedia', 'Wikipedia fear-lookups (Recession, Bank run, Margin call) — a leading sentiment signal.')],
}
GLOSSARY = {
 'Market breadth': 'The share of stocks above their 150-day average. High = broad, healthy uptrend; low (like 22%) = a narrow rally carried by a few mega-caps, which is fragile.',
 'VIX': 'Implied 30-day S&P volatility from options — the "fear gauge". Below ~15 = calm/complacent; above ~25 = stress. It usually spikes as prices fall.',
 'HYG vs its 150-day MA': 'HYG is the junk-bond ETF. When it trades below its 150-day average while stocks rise, credit is NOT confirming the rally — one of the most reliable warning tells (our backtest ranked it a top feature).',
 'Yield curve (2s10s)': '10-year minus 2-year yield. Inverted (negative) has preceded recessions; steepening off the lows often marks the turn.',
 'Correlation regime': 'In calm markets assets move independently; in a crisis they all fall together (correlations → 1) and diversification stops working. We measure the rolling average pairwise correlation.',
 'The butterfly effect': 'A shock in one corner (Houthi attacks → Red Sea shipping collapse) propagates days later into oil, freight and China equities. Our study showed these chains show up in discrete shocks — while at daily frequency most "signals" are noise, and human attention (fear lookups) leads better than raw event feeds.',
}

def _series(dataset, symbol):
    fs = glob.glob(f'{DATA_DIR}/{dataset}/**/symbol={symbol}/*.parquet', recursive=True)
    if not fs: fs = glob.glob(f'{DATA_DIR}/{dataset}/**/*.parquet', recursive=True)[:1]
    if not fs: return None
    d = pd.read_parquet(fs[0])
    dc = next((c for c in ['date', 'Date', 'time', 'datetime', 'timestamp'] if c in d.columns), None)
    vc = next((c for c in ['close', 'value', 'adj close', 'views', 'n_container'] if c in d.columns), None)
    if not dc or not vc: return None
    d[dc] = pd.to_datetime(d[dc], errors='coerce', utc=True).dt.tz_localize(None)
    s = d.dropna(subset=[dc]).set_index(dc)[vc].astype(float).sort_index()
    s = s[~s.index.duplicated(keep='last')]
    if len(s): s = s[s.index >= (s.index.max() - pd.DateOffset(years=6))]
    step = max(1, len(s) // 400)
    s = s.iloc[::step]
    return {'dataset': dataset, 'symbol': symbol, 'col': vc,
            'points': [{'t': d.strftime('%Y-%m-%d'), 'v': round(float(v), 4)} for d, v in s.items()]}

def symbols(dataset):
    out = set()
    for f in glob.glob(f'{DATA_DIR}/{dataset}/**/symbol=*/*.parquet', recursive=True):
        for part in f.split('/'):
            if part.startswith('symbol='): out.add(part[7:])
    return sorted(out)

def catalog():
    return {'categories': CATALOG, 'glossary': GLOSSARY}

def explain(question, ctx=None):
    if not GKEY: return {'answer': 'AI tutor unavailable (no gateway key).'}
    cats = ' | '.join(f"{k}: " + ', '.join(x[0] for x in v) for k, v in CATALOG.items())
    sysmsg = ("You are the BITFIN Academy tutor — a clear, friendly teacher of markets and data. "
              "Explain simply, with intuition and a concrete example, for a beginner-to-intermediate trader. "
              "Ground answers in the platform's datasets and factors. Be practical: say why it matters for trading. "
              "Keep it under 180 words. Never give financial advice — teach.")
    usr = f"Platform datasets: {cats}\nFactor glossary keys: {', '.join(GLOSSARY)}\nCurrent market: {json.dumps(ctx) if ctx else 'n/a'}\n\nStudent question: {question}"
    for m in ['minimax-m3', 'gemini-3.5-flash', 'glm-4.7']:   # fast models first for a responsive tutor
        body = json.dumps({'model': m, 'temperature': 0.4, 'max_tokens': 400, 'stream': False,
                           'messages': [{'role': 'system', 'content': sysmsg}, {'role': 'user', 'content': usr}]}).encode()
        req = urllib.request.Request(GATEWAY.rstrip('/') + '/v1/chat/completions', data=body,
                                     headers={'Authorization': f'Bearer {GKEY}', 'Content-Type': 'application/json'})
        try:
            raw = urllib.request.urlopen(req, timeout=30).read()
            txt = (json.loads(raw)['choices'][0]['message'].get('content') or '').strip()
            if txt: return {'answer': txt, 'model': m}
        except Exception:
            continue
    return {'answer': 'Tutor is busy — try again in a moment.'}
