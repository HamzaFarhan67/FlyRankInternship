import hashlib
import hmac
import json
import os
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
DATABASE = Path(os.getenv("DATABASE_PATH", ROOT / "billing.db"))
PRICES = {"api_call": 1, "input_token": 1, "cached_input_token": 0, "output_token": 2}
PLANS = {
    "free": {"api_call": 1000, "ai_token": 100000},
    "pro": {"api_call": 10000, "ai_token": 1000000},
}

app = FastAPI(title="Usage Metering and Billing Engine")


def connection() -> sqlite3.Connection:
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db() -> None:
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS plans (
                name TEXT PRIMARY KEY,
                api_call_limit INTEGER NOT NULL,
                ai_token_limit INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tenants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                plan TEXT NOT NULL REFERENCES plans(name),
                status TEXT NOT NULL DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(id),
                plan TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL REFERENCES tenants(id),
                usage_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                cost_cents INTEGER NOT NULL,
                idempotency_key TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tenant_id, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS processed_webhooks (
                event_id TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        db.executemany(
            "INSERT OR IGNORE INTO plans VALUES (?, ?, ?)",
            [(name, values["api_call"], values["ai_token"]) for name, values in PLANS.items()],
        )


init_db()


class TenantRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class GenerateRequest(BaseModel):
    usage_type: str = "api_call"
    quantity: int = Field(gt=0)


class CheckoutRequest(BaseModel):
    tenant_id: str


def tenant_or_404(db: sqlite3.Connection, tenant_id: str) -> sqlite3.Row:
    tenant = db.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
    if tenant is None:
        raise HTTPException(404, "Tenant not found")
    return tenant


def usage_kind(usage_type: str) -> str:
    if usage_type == "api_call":
        return "api_call"
    if usage_type in {"ai_token", "input_token", "cached_input_token", "output_token"}:
        return "ai_token"
    raise HTTPException(422, "usage_type must be api_call or an AI token type")


def current_usage(db: sqlite3.Connection, tenant_id: str, kind: str) -> int:
    types = ("api_call",) if kind == "api_call" else (
        "ai_token", "input_token", "cached_input_token", "output_token"
    )
    marks = ",".join("?" for _ in types)
    row = db.execute(
        f"SELECT COALESCE(SUM(quantity), 0) AS total FROM usage_events "
        f"WHERE tenant_id = ? AND usage_type IN ({marks}) "
        "AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')",
        (tenant_id, *types),
    ).fetchone()
    return int(row["total"])


@app.post("/tenants", status_code=status.HTTP_201_CREATED)
def create_tenant(request: TenantRequest):
    tenant_id = hashlib.sha256(f"{request.name}:{time.time_ns()}".encode()).hexdigest()[:16]
    with connection() as db:
        db.execute("INSERT INTO tenants (id, name, plan) VALUES (?, ?, 'free')", (tenant_id, request.name))
    return {"id": tenant_id, "name": request.name, "plan": "free", "status": "active"}


@app.post("/generate")
def generate(
    request: GenerateRequest,
    tenant_id: str = Header(alias="X-Tenant-ID"),
    idempotency_key: str = Header(alias="Idempotency-Key"),
):
    if not idempotency_key.strip():
        raise HTTPException(400, "Idempotency-Key is required")
    kind = usage_kind(request.usage_type)
    with connection() as db:
        tenant = tenant_or_404(db, tenant_id)
        duplicate = db.execute(
            "SELECT * FROM usage_events WHERE tenant_id = ? AND idempotency_key = ?",
            (tenant_id, idempotency_key),
        ).fetchone()
        if duplicate:
            return {"event_id": duplicate["id"], "usage": duplicate["quantity"], "cost_cents": duplicate["cost_cents"], "duplicate": True}
        limit = db.execute(
            "SELECT api_call_limit, ai_token_limit FROM plans WHERE name = ?", (tenant["plan"],)
        ).fetchone()[0 if kind == "api_call" else 1]
        used = current_usage(db, tenant_id, kind)
        if used + request.quantity > limit:
            code = 429 if kind == "api_call" else 402
            raise HTTPException(code, f"{kind} quota exceeded: {used} used, limit {limit}")
        cost = request.quantity * PRICES.get(request.usage_type, 0)
        cursor = db.execute(
            "INSERT INTO usage_events (tenant_id, usage_type, quantity, cost_cents, idempotency_key) VALUES (?, ?, ?, ?, ?)",
            (tenant_id, request.usage_type, request.quantity, cost, idempotency_key),
        )
        return {"event_id": cursor.lastrowid, "usage": request.quantity, "cost_cents": cost, "duplicate": False}


@app.get("/usage")
def usage(tenant_id: str = Header(alias="X-Tenant-ID")):
    with connection() as db:
        tenant = tenant_or_404(db, tenant_id)
        plan = db.execute("SELECT * FROM plans WHERE name = ?", (tenant["plan"],)).fetchone()
        api_used = current_usage(db, tenant_id, "api_call")
        token_used = current_usage(db, tenant_id, "ai_token")
        cost = db.execute(
            "SELECT COALESCE(SUM(cost_cents), 0) AS total FROM usage_events WHERE tenant_id = ? "
            "AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')",
            (tenant_id,),
        ).fetchone()["total"]
        return {
            "tenant_id": tenant_id,
            "plan": tenant["plan"],
            "api_calls": {"used": api_used, "limit": plan["api_call_limit"]},
            "ai_tokens": {"used": token_used, "limit": plan["ai_token_limit"]},
            "cost_cents": cost,
        }


@app.post("/checkout")
def checkout(request: CheckoutRequest):
    if not os.getenv("STRIPE_SECRET_KEY"):
        raise HTTPException(503, "Stripe is not configured")
    try:
        import stripe
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": os.environ["STRIPE_PRO_PRICE_ID"], "quantity": 1}],
            success_url=os.getenv("STRIPE_SUCCESS_URL", "http://localhost:8000"),
            cancel_url=os.getenv("STRIPE_CANCEL_URL", "http://localhost:8000"),
            metadata={"tenant_id": request.tenant_id},
        )
    except Exception as error:
        raise HTTPException(502, f"Stripe checkout failed: {error}") from error
    return {"checkout_url": session.url}


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(default="", alias="Stripe-Signature")):
    payload = await request.body()
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret or not stripe_signature.startswith("t=") or ",v1=" not in stripe_signature:
        raise HTTPException(400, "Invalid Stripe signature")
    timestamp, signature = stripe_signature.split(",v1=", 1)
    expected = hmac.new(secret.encode(), f"{timestamp.split('=', 1)[1]}.{payload.decode()}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(400, "Invalid Stripe signature")
    event = json.loads(payload)
    event_id = event.get("id")
    if not event_id:
        raise HTTPException(400, "Missing event id")
    data = event.get("data", {}).get("object", {})
    event_type = event.get("type")
    tenant_id = data.get("metadata", {}).get("tenant_id")
    plan = "pro" if event_type in {"checkout.session.completed", "customer.subscription.updated"} else "free"
    status_value = "canceled" if event_type == "customer.subscription.deleted" else "active"
    with connection() as db:
        if db.execute("SELECT 1 FROM processed_webhooks WHERE event_id = ?", (event_id,)).fetchone():
            return {"received": True, "duplicate": True}
        if tenant_id and event_type in {
            "checkout.session.completed", "customer.subscription.updated", "customer.subscription.deleted"
        }:
            tenant_or_404(db, tenant_id)
            db.execute("UPDATE tenants SET plan = ?, status = ? WHERE id = ?", (plan, status_value, tenant_id))
            db.execute(
                "INSERT OR REPLACE INTO subscriptions (id, tenant_id, plan, status) VALUES (?, ?, ?, ?)",
                (data.get("subscription", event_id), tenant_id, plan, status_value),
            )
        db.execute("INSERT INTO processed_webhooks (event_id) VALUES (?)", (event_id,))
    return {"received": True, "duplicate": False}
