# portfolio — tactical book + tracker

Data-grounded portfolios built from the datalake, with a one-command tracker.

- `port_stats.py` — 2000→2026 risk/return/Sharpe/drawdown + correlations for the
  candidate building blocks (informs the weights).
- `portfolio.json` — the current book: positions, weights, entry marks, thesis,
  and rebalance triggers. Source of truth.
- `track_portfolio.py` — pull latest datalake prices, compute P&L since entry
  vs the VOO benchmark. Run any day; compare at the review date.
- `build_portfolio.py` — render `portfolio.json` into a dashboard.

The Aug-2026 book (learned from 2000-2026): 57% equity (VOO/QQQM/XLV), 20% gold,
23% short T-bills, 5% staples — a regime tilt for a narrow rally with weak breadth
and HYG below its MA150. Educational research, not investment advice.

```bash
eval "$(python3 register_access.py "$ACCESS_GRANT")"   # from ../
python3 track_portfolio.py
```
