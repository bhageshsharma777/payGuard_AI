import os
import subprocess
import sys

import pytest

# The app requires a trained model. Run `python model/train.py` before tests.
@pytest.fixture
def client():
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
