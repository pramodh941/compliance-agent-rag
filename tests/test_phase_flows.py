import os
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "agent-worker"))

from workflows.report_generation import build_report


BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")


def test_report_generation_summary():
    report = build_report(
        [
            {
                "email_id": "e1",
                "analysis": {
                    "risk_level": "HIGH",
                    "violations": [
                        {"policy": "MNPI", "reason": "Confidential data shared"}
                    ],
                },
            },
            {
                "email_id": "e2",
                "analysis": {
                    "risk_level": "LOW",
                    "violations": [],
                },
            },
        ]
    )

    assert report["email_count"] == 2
    assert report["violation_count"] == 1
    assert report["risk_summary"] == {"HIGH": 1, "LOW": 1}
    assert report["violations"][0]["email_id"] == "e1"


e2e = pytest.mark.skipif(
    os.getenv("RUN_E2E") != "1",
    reason="Set RUN_E2E=1 when the docker-compose stack is running.",
)


@e2e
def test_phase1_agent_flow():
    response = requests.post(
        f"{BASE_URL}/agents/run",
        json={
            "input": "What is the insider trading policy?",
            "session_id": "pytest-phase1",
        },
        timeout=260,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["result"]["answer"]["status"] == "success"
    assert "material non-public information" in payload["result"]["answer"]["answer"].lower()


@e2e
def test_phase2_persistence_and_phase3_report():
    response = requests.post(
        f"{BASE_URL}/agents/run",
        json={
            "input": "What is the insider trading policy?",
            "session_id": "pytest-phase2",
        },
        timeout=260,
    )
    assert response.status_code == 200

    ingest = requests.post(f"{BASE_URL}/ingest", timeout=60)
    assert ingest.status_code == 200
    assert ingest.json()["email_count"] >= 25

    session = requests.get(f"{BASE_URL}/agents/sessions/pytest-phase2", timeout=30)
    assert session.status_code == 200
    assert session.json()["messages"]

    report = requests.get(f"{BASE_URL}/reports/compliance-summary?limit=25", timeout=30)
    assert report.status_code == 200
    body = report.json()
    assert body["email_count"] == 25
    assert body["alert_count"] >= 1
