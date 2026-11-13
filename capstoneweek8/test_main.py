import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from main import app, connection

client = TestClient(app)


def tenant():
    response = client.post("/tenants", json={"name": "Test"})
    assert response.status_code == 201
    return response.json()["id"]


def test_idempotency_and_usage():
    tenant_id = tenant()
    headers = {"X-Tenant-ID": tenant_id, "Idempotency-Key": "request-1"}
    first = client.post("/generate", headers=headers, json={"usage_type": "api_call", "quantity": 1})
    second = client.post("/generate", headers=headers, json={"usage_type": "api_call", "quantity": 1})
    assert first.status_code == second.status_code == 200
    assert second.json()["duplicate"] is True
    assert client.get("/usage", headers={"X-Tenant-ID": tenant_id}).json()["api_calls"]["used"] == 1


def test_ai_pricing():
    tenant_id = tenant()
    headers = {"X-Tenant-ID": tenant_id, "Idempotency-Key": "tokens"}
    response = client.post("/generate", headers=headers, json={"usage_type": "output_token", "quantity": 10})
    assert response.json()["cost_cents"] == 20


def test_webhook_signature_and_upgrade():
    tenant_id = tenant()
    payload = json.dumps({
        "id": "evt_test",
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"tenant_id": tenant_id}, "subscription": "sub_test"}},
    }).encode()
    secret = "whsec_test"
    import os
    os.environ["STRIPE_WEBHOOK_SECRET"] = secret
    timestamp = "1700000000"
    signature = hmac.new(secret.encode(), timestamp.encode() + b"." + payload, hashlib.sha256).hexdigest()
    headers = {"Stripe-Signature": f"t={timestamp},v1={signature}"}
    response = client.post("/webhooks/stripe", content=payload, headers=headers)
    assert response.status_code == 200
    assert client.get("/usage", headers={"X-Tenant-ID": tenant_id}).json()["plan"] == "pro"
    assert client.post("/webhooks/stripe", content=payload, headers=headers).json()["duplicate"] is True
