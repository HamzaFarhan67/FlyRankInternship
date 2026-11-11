import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from supabase import Client, create_client
from supabase_auth.errors import AuthApiError

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")

supabase: Client = create_client(supabase_url, supabase_key)
app = FastAPI(title="Auth Login & Protect API")
bearer_scheme = HTTPBearer(auto_error=False)


class AuthRequest(BaseModel):
    email: str = ""
    password: str = ""


def get_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail={"error": "Access token required"})

    try:
        response = supabase.auth.get_user(credentials.credentials)
    except AuthApiError:
        raise HTTPException(status_code=401, detail={"error": "Invalid or expired token"})
    if response.user is None:
        raise HTTPException(status_code=401, detail={"error": "Invalid or expired token"})
    return response.user


@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(request: AuthRequest):
    if not request.email.strip() or not request.password.strip():
        raise HTTPException(status_code=400, detail={"error": "Email and password are required"})

    try:
        response = supabase.auth.sign_up(
            {"email": request.email, "password": request.password}
        )
    except AuthApiError as error:
        raise HTTPException(status_code=400, detail={"error": str(error)})
    if response.user is None:
        raise HTTPException(status_code=400, detail={"error": "Unable to create account"})
    return {"user": response.user.model_dump()}


@app.post("/auth/login")
def login(request: AuthRequest):
    if not request.email.strip() or not request.password.strip():
        raise HTTPException(status_code=400, detail={"error": "Email and password are required"})

    try:
        response = supabase.auth.sign_in_with_password(
            {"email": request.email, "password": request.password}
        )
    except AuthApiError:
        raise HTTPException(status_code=401, detail={"error": "Invalid login credentials"})
    if response.session is None:
        raise HTTPException(status_code=401, detail={"error": "Invalid login credentials"})

    return {
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
    }


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user=Depends(get_authenticated_user)):
    supabase.auth.sign_out()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def profile(user=Depends(get_authenticated_user)):
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at,
    }


@app.get("/protected/dashboard")
def dashboard(user=Depends(get_authenticated_user)):
    return {"message": "Welcome to your dashboard.", "user_id": user.id}
