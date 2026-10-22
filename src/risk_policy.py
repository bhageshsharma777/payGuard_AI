def risk_decision(score):
    """Demo thresholds only; tune using validation data before real use."""
    score = float(score)
    if score >= 0.70:
        return {"risk_level": "HIGH", "recommended_action": "REVIEW"}
    if score >= 0.30:
        return {"risk_level": "MEDIUM", "recommended_action": "VERIFY"}
    return {"risk_level": "LOW", "recommended_action": "LOWER_RISK_QUEUE"}
