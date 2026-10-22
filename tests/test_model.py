from src.risk_policy import risk_decision


def test_risk_policy_high():
    assert risk_decision(0.9)["recommended_action"] == "REVIEW"


def test_risk_policy_medium():
    assert risk_decision(0.5)["risk_level"] == "MEDIUM"


def test_risk_policy_low():
    assert risk_decision(0.1)["risk_level"] == "LOW"
