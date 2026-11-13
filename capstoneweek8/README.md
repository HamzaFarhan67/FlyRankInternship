# Usage Metering and Billing Engine

FastAPI service for idempotent usage metering, monthly quotas, integer-cent costs, and Stripe test-mode subscription synchronization.

## Run

```bash
cd capstoneweek8
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Create a tenant, then send `X-Tenant-ID` and a unique `Idempotency-Key` to `/generate`. Read totals from `/usage`.

Free limits are 1,000 API calls and 100,000 AI tokens per month. Pro limits are 10,000 API calls and 1,000,000 AI tokens. API quota failures return 429; AI token quota failures return 402.

## Architecture

```text
HTTP routes -> quota and pricing logic -> SQLite tables
Stripe Checkout -> signed webhook -> tenant subscription mirror
```

## Limitations

Stripe Checkout requires Stripe test-mode environment variables and a Stripe CLI webhook forwarder. There is no invoicing, proration, overage billing, or background reconciliation job.
