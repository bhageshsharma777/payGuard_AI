import os
import io
import csv
import json
import sqlite3
import secrets
from datetime import datetime, timezone
from functools import wraps

import joblib
import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file

from src.database import init_db, get_db, insert_assessment, get_assessment
from src.risk_policy import risk_decision
from src.explainability import explain_transaction
from model.predict import load_model, score_transaction

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

init_db()
MODEL, MODEL_ERROR = load_model()


def api_error(message, status=400):
    return jsonify({"error": message}), status


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "model_loaded": MODEL is not None,
        "model_error": MODEL_ERROR,
        "mode": "demo",
    })


@app.post("/api/score")
def score_one():
    if MODEL is None:
        return api_error("Model is not trained yet. Run: python model/train.py", 503)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error("Send a JSON object.")
    try:
        result = score_transaction(MODEL, payload)
    except (ValueError, TypeError, KeyError) as exc:
        return api_error(str(exc))
    result.update(risk_decision(result["risk_score"]))
    result["reasons"] = explain_transaction(payload, result)
    transaction_id = insert_assessment(payload, result)
    result["transaction_id"] = transaction_id
    return jsonify(result)


@app.post("/api/score-batch")
def score_batch():
    if MODEL is None:
        return api_error("Model is not trained yet. Run: python model/train.py", 503)
    if "file" not in request.files:
        return api_error("Upload a CSV file in the 'file' field.")
    uploaded = request.files["file"]
    if not uploaded.filename.lower().endswith(".csv"):
        return api_error("Only CSV files are supported.")
    try:
        df = pd.read_csv(uploaded, nrows=10001)
    except Exception:
        return api_error("Could not read the CSV.")
    if df.empty:
        return api_error("CSV has no rows.")
    if len(df) > 10000:
        return api_error("Maximum 10,000 rows per upload.")
    results = []
    for idx, row in df.iterrows():
        payload = row.to_dict()
        try:
            result = score_transaction(MODEL, payload)
            result.update(risk_decision(result["risk_score"]))
            result["reasons"] = explain_transaction(payload, result)
            result["row_number"] = int(idx) + 2
            result["transaction_id"] = insert_assessment(payload, result)
            results.append(result)
        except (ValueError, TypeError, KeyError) as exc:
            return api_error(f"Invalid data at CSV row {idx + 2}: {exc}")
    output = io.StringIO()
    fields = ["row_number", "transaction_id", "risk_score", "risk_level", "recommended_action", "reasons"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for item in results:
        writer.writerow({k: json.dumps(item.get(k)) if k == "reasons" else item.get(k, "") for k in fields})
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="payguard_scored_transactions.csv")


@app.get("/api/transactions")
def transactions():
    limit = min(max(request.args.get("limit", 100, type=int), 1), 500)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, created_at, amount, risk_score, risk_level, recommended_action, payment_status, review_status FROM assessments ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/transactions/<int:assessment_id>")
def transaction_detail(assessment_id):
    item = get_assessment(assessment_id)
    if not item:
        return api_error("Transaction not found.", 404)
    return jsonify(item)


@app.post("/api/transactions/<int:assessment_id>/review")
def review_transaction(assessment_id):
    payload = request.get_json(silent=True) or {}
    decision = payload.get("decision")
    reason = str(payload.get("reason", "")).strip()[:500]
    if decision not in {"confirmed_fraud", "legitimate", "needs_more_info"}:
        return api_error("decision must be confirmed_fraud, legitimate, or needs_more_info.")
    with get_db() as conn:
        row = conn.execute("SELECT id FROM assessments WHERE id = ?", (assessment_id,)).fetchone()
        if not row:
            return api_error("Transaction not found.", 404)
        conn.execute(
            "UPDATE assessments SET review_status = ?, review_reason = ?, reviewed_at = ? WHERE id = ?",
            (decision, reason, datetime.now(timezone.utc).isoformat(), assessment_id),
        )
        conn.execute(
            "INSERT INTO review_events (assessment_id, decision, reason, created_at) VALUES (?, ?, ?, ?)",
            (assessment_id, decision, reason, datetime.now(timezone.utc).isoformat()),
        )
    return jsonify({"ok": True, "transaction_id": assessment_id, "review_status": decision})


def paypal_config():
    return (
        os.getenv("PAYPAL_CLIENT_ID", ""),
        os.getenv("PAYPAL_CLIENT_SECRET", ""),
        os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com").rstrip("/"),
    )


def paypal_access_token():
    client_id, secret, base_url = paypal_config()
    if not client_id or not secret:
        raise RuntimeError("Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in .env to enable PayPal Sandbox.")
    response = requests.post(
        f"{base_url}/v1/oauth2/token",
        auth=(client_id, secret),
        data={"grant_type": "client_credentials"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


@app.get("/api/paypal/config")
def paypal_public_config():
    client_id, _, _ = paypal_config()
    return jsonify({"enabled": bool(client_id), "client_id": client_id})


@app.post("/api/paypal/orders")
def create_paypal_order():
    payload = request.get_json(silent=True) or {}
    # Amount is fixed server-side for this MVP; never trust an amount from the browser.
    amount = "10.00"
    currency = "USD"
    try:
        token = paypal_access_token()
        _, _, base_url = paypal_config()
        response = requests.post(
            f"{base_url}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "reference_id": "payguard-demo",
                    "description": "PayGuard AI Sandbox demo purchase",
                    "amount": {"currency_code": currency, "value": amount},
                }],
                "application_context": {
                    "brand_name": "PayGuard AI Demo",
                    "user_action": "PAY_NOW",
                    "return_url": request.host_url.rstrip("/") + "/?paypal=return",
                    "cancel_url": request.host_url.rstrip("/") + "/?paypal=cancel",
                },
            },
            timeout=20,
        )
        response.raise_for_status()
        order = response.json()
        return jsonify({"id": order["id"], "status": order.get("status"), "amount": amount, "currency": currency})
    except requests.RequestException:
        return api_error("PayPal Sandbox request failed. Check credentials and network settings.", 502)
    except RuntimeError as exc:
        return api_error(str(exc), 503)


@app.post("/api/paypal/orders/<order_id>/capture")
def capture_paypal_order(order_id):
    # Demo workflow: capture is permitted only after the merchant has explicitly
    # reviewed/approved the linked risk record in a production-quality workflow.
    payload = request.get_json(silent=True) or {}
    if payload.get("risk_review_approved") is not True:
        return api_error("For this demo, explicitly approve the risk review before capture.")
    try:
        token = paypal_access_token()
        _, _, base_url = paypal_config()
        response = requests.post(
            f"{base_url}/v2/checkout/orders/{order_id}/capture",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "PayPal-Request-Id": secrets.token_hex(16)},
            json={},
            timeout=20,
        )
        response.raise_for_status()
        result = response.json()
        status = result.get("status", "UNKNOWN")
        with get_db() as conn:
            conn.execute(
                "INSERT INTO payment_orders (paypal_order_id, payment_status, created_at) VALUES (?, ?, ?) "
                "ON CONFLICT(paypal_order_id) DO UPDATE SET payment_status=excluded.payment_status",
                (order_id, status, datetime.now(timezone.utc).isoformat()),
            )
        return jsonify({"id": order_id, "status": status, "paypal_response": result})
    except requests.RequestException:
        return api_error("PayPal capture request failed. Verify the order state before retrying.", 502)
    except RuntimeError as exc:
        return api_error(str(exc), 503)


@app.errorhandler(413)
def too_large(_error):
    return api_error("File is too large. Maximum upload size is 5 MB.", 413)


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
