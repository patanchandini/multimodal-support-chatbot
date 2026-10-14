import io
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True


def test_chat_text_only(client):
    r = client.post("/chat", data={
        "session_id": "pytest-text",
        "message": "Hello, help with my order",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == "pytest-text"
    assert body["status"] in ("answered", "needs_clarification")


def test_chat_with_pdf_match(client, good_invoice_pdf):
    files = {"file": ("invoice.pdf", io.BytesIO(good_invoice_pdf), "application/pdf")}
    r = client.post("/chat",
        data={"session_id": "pytest-match",
              "message": "My order ORD-12345 for USD 149.99"},
        files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["verification"]["status"] == "match"
    assert "ORD-12345" in body["verification"]["matched_fields"].get("order_ids", [])


def test_chat_with_pdf_conflict(client, good_invoice_pdf):
    files = {"file": ("invoice.pdf", io.BytesIO(good_invoice_pdf), "application/pdf")}
    r = client.post("/chat",
        data={"session_id": "pytest-conflict",
              "message": "My order ORD-99999 for USD 500.00"},
        files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "needs_clarification"
    assert body["verification"]["status"] == "conflict"


def test_chat_rejects_injection_pdf(client, injection_pdf):
    files = {"file": ("injection.pdf", io.BytesIO(injection_pdf), "application/pdf")}
    r = client.post("/chat",
        data={"session_id": "pytest-inject",
              "message": "Help with invoice"},
        files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "rejected"


def test_chat_handles_blurry_image(client, blurry_image):
    files = {"file": ("blur.png", io.BytesIO(blurry_image), "image/png")}
    r = client.post("/chat",
        data={"session_id": "pytest-blur",
              "message": "Help"},
        files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "needs_clarification"
    assert "blurry" in body["reply"].lower() or "clearer" in body["reply"].lower()


def test_chat_handles_tiny_image(client, tiny_image):
    files = {"file": ("tiny.png", io.BytesIO(tiny_image), "image/png")}
    r = client.post("/chat",
        data={"session_id": "pytest-tiny",
              "message": "Help"},
        files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "needs_clarification"
    assert "small" in body["reply"].lower() or "clearer" in body["reply"].lower()


def test_admin_cleanup_endpoint(client):
    r = client.post("/admin/cleanup")
    assert r.status_code == 200
    assert "deleted" in r.json()