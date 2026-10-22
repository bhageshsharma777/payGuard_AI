import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.getenv("PAYGUARD_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "payguard.db"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            input_json TEXT NOT NULL,
            amount REAL,
            risk_score REAL NOT NULL,
            risk_level TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            reasons_json TEXT NOT NULL,
            payment_status TEXT DEFAULT 'NOT_LINKED',
            review_status TEXT DEFAULT 'PENDING',
            review_reason TEXT,
            reviewed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS review_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_id INTEGER NOT NULL,
            decision TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(assessment_id) REFERENCES assessments(id)
        );
        CREATE TABLE IF NOT EXISTS payment_orders (
            paypal_order_id TEXT PRIMARY KEY,
            payment_status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)


def insert_assessment(payload, result):
    amount = payload.get("Amount", payload.get("amount"))
    try:
        amount = float(amount) if amount is not None else None
    except (ValueError, TypeError):
        amount = None
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO assessments
            (created_at, input_json, amount, risk_score, risk_level, recommended_action, reasons_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                json.dumps(payload, default=str),
                amount,
                float(result["risk_score"]),
                result["risk_level"],
                result["recommended_action"],
                json.dumps(result.get("reasons", [])),
            ),
        )
        return cur.lastrowid


def get_assessment(assessment_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM assessments WHERE id = ?", (assessment_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        data["input"] = json.loads(data.pop("input_json"))
        data["reasons"] = json.loads(data.pop("reasons_json"))
        events = conn.execute(
            "SELECT decision, reason, created_at FROM review_events WHERE assessment_id = ? ORDER BY id DESC",
            (assessment_id,),
        ).fetchall()
        data["review_events"] = [dict(event) for event in events]
        return data
