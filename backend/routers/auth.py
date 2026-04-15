"""SaforaERP - Authentication Router"""
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import jwt
import sys
sys.path.insert(0, "/home/claude/saforaerp/backend")
from config import settings

router = APIRouter()
security = HTTPBearer()

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = verify_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    return payload

@router.post("/login")
async def login(request: LoginRequest):
    from database import get_db_admin
    db = get_db_admin()
    try:
        auth_response = db.auth.sign_in_with_password({"email": request.email, "password": request.password})
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user_id = auth_response.user.id
    profile_resp = db.table("user_profiles").select("*, companies(*), branches(*)").eq("id", str(user_id)).single().execute()
    if not profile_resp.data:
        raise HTTPException(status_code=404, detail="User profile not found")
    profile = profile_resp.data
    if not profile.get("is_active"):
        raise HTTPException(status_code=403, detail="Account is inactive")
    
    token_data = {
        "sub": str(user_id), "email": request.email,
        "role": profile.get("role", "general"),
        "company_id": str(profile.get("company_id", "")),
        "branch_id": str(profile.get("branch_id", "")),
        "user_group_id": str(profile.get("user_group_id", "")),
    }
    db.table("user_profiles").update({"last_login": datetime.utcnow().isoformat()}).eq("id", str(user_id)).execute()
    db.table("user_login_history").insert({"user_id": str(user_id), "status": "success"}).execute()
    
    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token({"sub": str(user_id)}),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": str(user_id), "email": request.email,
            "full_name": profile.get("full_name"), "role": profile.get("role"),
            "company": profile.get("companies", {}), "branch": profile.get("branches", {}),
        }
    }

@router.post("/refresh")
async def refresh_token(refresh_token: str = Body(...)):
    payload = verify_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    from database import get_db_admin
    db = get_db_admin()
    p = db.table("user_profiles").select("*").eq("id", payload["sub"]).single().execute().data
    if not p or not p.get("is_active"):
        raise HTTPException(status_code=401, detail="User not found")
    token_data = {"sub": payload["sub"], "email": p.get("email"), "role": p.get("role"),
                  "company_id": str(p.get("company_id","")), "branch_id": str(p.get("branch_id",""))}
    return {"access_token": create_access_token(token_data), "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    from database import get_db_admin
    db = get_db_admin()
    profile = db.table("user_profiles").select("*, companies(*), branches(*), user_groups(*)").eq("id", current_user["sub"]).single().execute()
    return {"success": True, "data": profile.data}

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    from database import get_db_admin
    db = get_db_admin()
    db.table("user_login_history").update({"logout_at": datetime.utcnow().isoformat()}).eq("user_id", current_user["sub"]).is_("logout_at", "null").execute()
    return {"success": True, "message": "Logged out"}

@router.get("/users")
async def list_users(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["administrator","super_admin","admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    from database import get_db_admin
    db = get_db_admin()
    users = db.table("user_profiles").select("*, companies(name), branches(name), user_groups(name)").eq("company_id", current_user.get("company_id")).execute()
    return {"success": True, "data": users.data, "total": len(users.data or [])}

@router.get("/login-history")
async def login_history(current_user: dict = Depends(get_current_user)):
    from database import get_db_admin
    db = get_db_admin()
    hist = db.table("user_login_history").select("*, user_profiles(full_name, email)").order("login_at", desc=True).limit(100).execute()
    return {"success": True, "data": hist.data}
