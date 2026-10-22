# PayGuard AI

AI-assisted payment risk scoring and transaction review dashboard built with Flask, scikit-learn, SQLite, and optional PayPal Sandbox APIs.

> **Important:** This is an educational hackathon prototype, not a production fraud detection or payment processing system. Its initial synthetic dataset is only for testing the software flow. Model predictions are risk estimates, not proof of fraud.

## Features

- Single transaction risk scoring (`POST /api/score`)
- Batch CSV scoring and download (`POST /api/score-batch`)
- Dashboard with risk distribution and transaction history
- Human review actions with audit history
- PayPal Sandbox order creation and guarded capture endpoint
- Health endpoint and basic tests
- Synthetic training data if a public dataset is not provided

## Requirements

- Python 3.10 or newer
- VS Code or another editor
- Optional: PayPal Developer Sandbox credentials

## Windows PowerShell setup

```powershell
cd payguard-ai
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python model/train.py
python app.py
```

Open `http://127.0.0.1:5000`.

If PowerShell blocks activation, run commands using `.\.venv\Scripts\python.exe` instead, or activate the environment through the VS Code interpreter selector.

## macOS/Linux setup

```bash
cd payguard-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python model/train.py
python app.py
```

## Use a public dataset

Download a permitted copy of the Kaggle Credit Card Fraud Detection dataset and save it as `data/creditcard.csv`. The training script expects `Time`, `Amount`, and `Class` columns.

Without this file, the script creates synthetic data so the app can run immediately. Do not describe synthetic-data performance as validated fraud detection performance.

## API examples

Score one transaction:

```bash
curl -X POST http://127.0.0.1:5000/api/score \
  -H "Content-Type: application/json" \
  -d '{"Time":3600,"Amount":125.00}'
```

Check health:

```bash
curl http://127.0.0.1:5000/api/health
```

CSV upload requires a `file` field and numeric `Time` and `Amount` columns.

## PayPal Sandbox

1. Create a Sandbox REST app in the PayPal Developer Dashboard.
2. Copy its Sandbox client ID and secret into `.env`.
3. Keep `.env` out of Git.
4. Restart the server and use the PayPal Sandbox order creation panel.

This starter creates server-side Sandbox orders. A production-ready checkout demo should also render the PayPal JavaScript SDK approval buttons, handle the approval callback, and verify/capture orders server-side. Never trust client-side success alone. Test only with Sandbox accounts and credentials.

## Model limitations

- The baseline uses only `Time` and `Amount`.
- The included simple explanations are not SHAP-based and must not be presented as causal proof.
- Demo risk thresholds require validation before any real-world use.
- Public dataset results do not automatically generalize to PayPal transactions.
- No real payment card data should be collected or stored.

## Tests

```bash
python model/train.py
pytest -q
```

## Suggested next upgrades

1. Add an evaluated SHAP explanation module.
2. Add temporal validation, threshold selection, and calibration analysis.
3. Add a full PayPal JavaScript SDK checkout UI and verified capture workflow.
4. Add authentication and role-based access to review actions.
5. Add PostgreSQL and deployment configuration if required.
6. Document measured test-set results and record a short demonstration video.

## License

MIT License (see `LICENSE`).
