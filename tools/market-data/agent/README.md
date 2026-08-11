# agent — STOCKMIND autonomous paper-trader  (SIMULATION ONLY)

Runs continuously on **DGXSEC**. Every hour it reads the datalake, builds a
market snapshot, asks the AI brain (local **freellmapi** gateway — ~115 free
models at `http://100.89.89.47:8899`) for target weights, and rebalances a
**virtual** long/short book with costs and risk caps. No real broker is ever
contacted (`SIMULATION_ONLY = True`). Long/short allowed up to a gross cap.

## Files
- `stockmind_trader.py` — the engine (snapshot → AI brain → paper rebalance → journal).
- `config.json` — gateway URL, model, universe (22 ETFs → datalake series), capital, risk caps.
- `secrets.env` — `GATEWAY_KEY=...` (chmod 600, **never committed**; see `secrets.env.example`).
- `systemd/` — hourly service + timer.
- writes `state.json` (book) and `journal.jsonl` (every decision) — git-ignored.

## Brain
Calls the gateway's OpenAI-compatible `/v1/chat/completions` (`model:"auto"` router).
Until `GATEWAY_KEY` is set it falls back to a rule-based trend/regime policy, so the
simulation always acts. Set the key to activate the LLM brain:
```bash
echo 'GATEWAY_KEY=freellma…' > /opt/quant/agent_trader/secrets.env && chmod 600 $_
```

## Deploy (on DGXSEC)
```bash
/opt/quant/venv/bin/pip install pandas pyarrow requests
systemctl enable --now stockmind-trader.timer     # hourly
python3 stockmind_trader.py --once                 # or run one cycle now
```
Risk caps: `max_gross` (gross leverage), `max_name` (per-position). Educational
simulation — not trading advice, not a real broker.
