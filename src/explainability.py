def explain_transaction(payload, result):
    """Transparent demo explanations; do not claim these prove fraud."""
    reasons = []
    amount = payload.get("Amount", payload.get("amount"))
    try:
        amount = float(amount)
        if amount >= 500:
            reasons.append("Transaction amount is high relative to this demo's simple heuristic.")
    except (TypeError, ValueError):
        pass
    level = result.get("risk_level")
    if level == "HIGH":
        reasons.append("The trained model produced a high risk estimate; manual investigation is recommended.")
    elif level == "MEDIUM":
        reasons.append("The model estimate is in the medium band; consider additional verification.")
    else:
        reasons.append("The model estimate is in the lower-risk band; this does not guarantee legitimacy.")
    reasons.append("These are decision-support signals, not proof of fraud.")
    return reasons
