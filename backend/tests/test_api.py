import os
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_intelliflow.db"
os.environ["JWT_SECRET"] = "test-only-jwt-secret-long-enough-for-tests"
os.environ["AI_PROVIDER"] = "mock"

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(client):
    response = client.post("/api/auth/register", json={
        "email": f"{uuid4().hex}@example.com",
        "password": "password123",
    })
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_requires_a_real_account_and_correct_password(client):
    registration = client.post("/api/auth/register", json={
        "email": f"{uuid4().hex}@example.com",
        "password": "correct-password",
    })
    assert registration.status_code == 201

    login = client.post("/api/auth/login", json={
        "email": registration.json()["user"]["email"],
        "password": "wrong-password",
    })
    assert login.status_code == 401

    login = client.post("/api/auth/login", json={
        "email": registration.json()["user"]["email"],
        "password": "correct-password",
    })
    assert login.status_code == 200


def test_registration_does_not_accept_a_client_selected_role(client):
    first = client.post("/api/auth/register", json={
        "email": f"{uuid4().hex}@example.com",
        "password": "correct-password",
    })
    assert first.status_code == 201
    response = client.post("/api/auth/register", json={
        "email": f"{uuid4().hex}@example.com",
        "password": "correct-password",
        "role": "Admin",
    })
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "Employee"


def test_request_workflow(client):
    headers = auth_headers(client)
    created = client.post("/api/requests", json={
        "sender": "customer@example.com",
        "subject": "Refund request",
        "message": "I am frustrated and need an urgent refund.",
    }, headers=headers)
    assert created.status_code == 201
    request_id = created.json()["id"]

    processed = client.post(f"/api/ai/process/{request_id}", headers=headers)
    assert processed.status_code == 200
    assert processed.json()["status"] == "Awaiting Approval"

    approval = client.post(f"/api/approvals/{request_id}/approve", json={
        "comments": "Reviewed",
        "draft": "Thank you for your request. Our finance team will review it.",
    }, headers=headers)
    assert approval.status_code == 200
    assert approval.json()["status"] == "Approved"


def test_create_request_rate_limit_returns_429(client):
    app.state.limiter.reset()
    headers = auth_headers(client)
    payload = {
        "sender": "customer@example.com",
        "subject": "Rate limit test",
        "message": "Testing the create request rate limit.",
    }

    try:
        responses = [
            client.post("/api/requests", json=payload, headers=headers)
            for _ in range(31)
        ]
    finally:
        app.state.limiter.reset()

    assert all(response.status_code == 201 for response in responses[:30])
    assert responses[30].status_code == 429

