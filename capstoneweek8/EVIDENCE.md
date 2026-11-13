# Evidence

- Idempotency: `pytest test_main.py::test_idempotency_and_usage` passes; two requests with one key produce one usage event.
- Cost calculation: `pytest test_main.py::test_ai_pricing` passes; 10 output tokens cost 20 cents.
- Stripe webhook: `pytest test_main.py::test_webhook_signature_and_upgrade` passes; a signed event upgrades Free to Pro and a replay is ignored.
- Validation and persistence: SQLite creates `plans`, `tenants`, `subscriptions`, `usage_events`, and `processed_webhooks` at startup.
