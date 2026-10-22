"""Train a baseline demo model.

If data/creditcard.csv exists, uses its Time, Amount and Class columns.
Otherwise creates synthetic data so the app can be run end-to-end immediately.
Synthetic results are for demonstration only and are not evidence of real-world
fraud detection performance.
"""
import os
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_PATH = os.path.join(ROOT, "data", "creditcard.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "fraud_pipeline.joblib")
FEATURES = ["Time", "Amount"]
LABEL = "Class"


def synthetic_data(n=12000, seed=42):
    """Create deliberately learnable synthetic data for smoke-testing the app.

    This distribution is artificial and must never be presented as real-world
    fraud performance. A real submission should train and report results on a
    permitted labeled dataset and use a more informative feature set.
    """
    rng = np.random.default_rng(seed)
    label = rng.binomial(1, 0.06, n)
    time = rng.uniform(0, 172800, n)
    # Fraud examples are shifted toward larger amounts and a synthetic time
    # window. These intentionally visible signals make the starter model demo
    # easier to inspect; they are not realistic fraud rules.
    normal = label == 0
    fraud = label == 1
    amount = np.empty(n, dtype=float)
    amount[normal] = rng.lognormal(mean=3.1, sigma=1.0, size=normal.sum())
    amount[fraud] = rng.lognormal(mean=5.0, sigma=0.9, size=fraud.sum())
    time[fraud] = rng.uniform(0, 24000, fraud.sum())
    amount = np.clip(amount, 0.5, 2500)
    return pd.DataFrame({"Time": time, "Amount": amount, "Class": label})


def main():
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        missing = set(FEATURES + [LABEL]) - set(df.columns)
        if missing:
            raise ValueError(f"Dataset missing columns: {sorted(missing)}")
        df = df[FEATURES + [LABEL]].dropna()
        print(f"Using public dataset: {DATA_PATH}")
    else:
        df = synthetic_data()
        print("Using SYNTHETIC demo data. Metrics are not real-world performance.")
    X = df[FEATURES].astype(float)
    y = df[LABEL].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("classifier", RandomForestClassifier(
            n_estimators=160,
            class_weight="balanced",
            random_state=42,
            min_samples_leaf=2,
            n_jobs=-1,
        )),
    ])
    model.fit(X_train, y_train)
    probabilities = model.predict_proba(X_test)[:, list(model.classes_).index(1)]
    predictions = (probabilities >= 0.5).astype(int)
    print("\nEvaluation report (threshold=0.50):")
    print(classification_report(y_test, predictions, zero_division=0))
    print("Confusion matrix:\n", confusion_matrix(y_test, predictions))
    print("Average precision / PR-AUC summary:", round(average_precision_score(y_test, probabilities), 4))
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"\nSaved model: {MODEL_PATH}")


if __name__ == "__main__":
    main()
