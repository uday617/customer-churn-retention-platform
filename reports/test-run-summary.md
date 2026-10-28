# Verification Run Summary

Last local verification run: 2026-10-28.

- Automated test suite: **18 passed**.
- Python compile check: passed (`python -m compileall -q src dashboard tests`).
- Full clean baseline generation: 20,000 customers, 18 months, seed `20261022`; **0 validation errors, 0 warnings**.
- Full dataset reproducibility: generated twice with identical configuration; all manifest row counts and SHA-256 checksums matched.
- Full dataset row counts: 20,000 customers; 20,000 subscriptions; 193,741 usage snapshots; 193,741 billing events; 15,915 support cases.
- Anomaly-injected smoke dataset: all four required ground-truth issue types were present and detected.
- Supervised model: logistic-regression baseline trains and returns held-out metrics when both classes and sufficient data exist; insufficient-data behavior is tested. Evaluation is a stratified customer holdout, not a true temporal backtest.
- UI runtime: Streamlit is declared in `requirements.txt`, but Streamlit was not installed in the execution environment, so the dashboard was not launched interactively here. Install dependencies and run `streamlit run dashboard/app.py` locally to verify rendering.

These results validate the synthetic workflow and automated checks; they do not establish production ML performance or real-world retention lift.
