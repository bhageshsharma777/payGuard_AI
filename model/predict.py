import os
import joblib
import pandas as pd

FEATURES = ["Time", "Amount"]


def load_model():
    path = os.getenv("MODEL_PATH", os.path.join(os.path.dirname(__file__), "fraud_pipeline.joblib"))
    if not os.path.exists(path):
        return None, f"Model file not found: {path}"
    try:
        return joblib.load(path), None
    except Exception as exc:
        return None, str(exc)


def score_transaction(model, payload):
    row = {}
    for feature in FEATURES:
        value = payload.get(feature, payload.get(feature.lower()))
        if value is None:
            raise ValueError(f"Missing required feature: {feature}")
        try:
            row[feature] = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Feature {feature} must be numeric.")
    frame = pd.DataFrame([row], columns=FEATURES)
    probabilities = model.predict_proba(frame)[0]
    classes = list(model.classes_)
    fraud_index = classes.index(1) if 1 in classes else len(probabilities) - 1
    score = float(probabilities[fraud_index])
    return {"risk_score": round(score, 4), "model_version": "baseline-v1"}
