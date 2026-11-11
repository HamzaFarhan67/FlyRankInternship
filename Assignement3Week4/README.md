# Auth Login & Protect

FastAPI authentication API using Supabase Auth.

## Setup

```bash
cd Assignement3Week4
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Set `SUPABASE_URL` and `SUPABASE_KEY` in `.env`, then start the server:

```bash
uvicorn main:app --reload --port 8000
```

Swagger UI is available at `http://localhost:8000/docs`.

## Endpoints

| Method | Route | Authentication |
| --- | --- | --- |
| POST | `/auth/signup` | No |
| POST | `/auth/login` | No |
| POST | `/auth/logout` | Bearer token |
| GET | `/public/info` | No |
| GET | `/protected/profile` | Bearer token |
| GET | `/protected/dashboard` | Bearer token |

Use the access token returned by `/auth/login` with the **Authorize** button in Swagger UI.
