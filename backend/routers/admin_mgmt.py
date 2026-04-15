"""SaforaERP - Admin Management Router"""
from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import sys; sys.path.insert(0, "/home/claude/saforaerp/backend")
from routers.auth import get_current_user
router = APIRouter()
def db():
    from database import get_db_admin
    return get_db_admin()

@router.get("/vehicles")
async def list_vehicles(current_user: dict = Depends(get_current_user)):
    return {"success": True, "data": db().table("admin_vehicles").select("*").eq("company_id", current_user.get("company_id")).execute().data}

@router.get("/complaints")
async def list_complaints(status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    q = db().table("admin_complaints").select("*").eq("company_id", current_user.get("company_id"))
    if status: q = q.eq("status", status)
    return {"success": True, "data": q.order("created_at", desc=True).execute().data}

@router.get("/procurement")
async def list_procurement(current_user: dict = Depends(get_current_user)):
    return {"success": True, "data": db().table("admin_procurement").select("*").eq("company_id", current_user.get("company_id")).execute().data}
