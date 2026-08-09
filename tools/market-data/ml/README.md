# ml — training on the DGX Spark boxes

Trading-AI training that runs on the two **NVIDIA GB10 (DGX Spark)** nodes
(128 GB unified, aarch64). Architecture, engine choices and roadmap:
see `../examples/ml_plan.html`.

Plane split:
- **DGXMAIN** — data & serving (Storj ETL, feature store on Postgres, Dify,
  backtest, scheduler). Already runs Dify + Postgres + nginx.
- **DGXSEC** — training & compute (GBM, deep-TS + foundation fine-tune, RL,
  Optuna/MLflow). Clean box.

## baseline.py
Walk-forward LightGBM predicting next-day S&P direction from 10 assets, run
on DGXSEC against `/opt/bucket_restore`. Honest floor: **ACC 51.9% / AUC
0.516, long-flat Sharpe 0.41** — daily index timing has ~no durable edge, so
the real models target cross-sectional ranking, multi-horizon & vol-targeted
returns, regime conditioning, and bootstrap-survived alt-data.

```bash
python3 -m venv /opt/quant/venv
/opt/quant/venv/bin/pip install pandas pyarrow scikit-learn lightgbm
/opt/quant/venv/bin/python baseline.py
```
