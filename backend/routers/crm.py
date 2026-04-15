"""SaforaERP - CRM Router"""
from fastapi import APIRouter, Depends, Query, Body
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import sys; sys.path.insert(0, "/home/claude/saforaerp/backend")
from routers.auth import get_current_user
router = APIRouter()
def db():
    from database import get_db_admin
    return get_db_admin()

@router.get("/dashboard")
async def crm_dashboard(current_user: dict = Depends(get_current_user)):
    d = db()
    cid = current_user.get("company_id")
    leads = d.table("leads").select("status, count", count="exact").eq("company_id", cid).execute()
    total_leads = d.table("leads").select("id", count="exact").eq("company_id", cid).execute()
    won = d.table("leads").select("id", count="exact").eq("company_id", cid).eq("status", "converted").execute()
    return {"success": True, "data": {"total_leads": total_leads.count or 0, "won": won.count or 0, "leads_by_status": leads.data}}

@router.get("/leads")
async def list_leads(status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    q = db().table("leads").select("*").eq("company_id", current_user.get("company_id"))
    if status: q = q.eq("status", status)
    return {"success": True, "data": q.order("created_at", desc=True).execute().data}

@router.post("/leads")
async def create_lead(
    name: str = Body(...), phone: Optional[str] = Body(None),
    email: Optional[str] = Body(None), source: Optional[str] = Body(None),
    product_interest: Optional[str] = Body(None), estimated_value: Optional[float] = Body(None),
    assigned_to: Optional[str] = Body(None), notes: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    lead_no = f"LEAD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    result = db().table("leads").insert({
        "company_id": current_user.get("company_id"), "lead_no": lead_no,
        "name": name, "phone": phone, "email": email, "source": source,
        "product_interest": product_interest, "estimated_value": estimated_value,
        "assigned_to": assigned_to, "notes": notes, "status": "new"
    }).execute()
    return {"success": True, "data": result.data}

@router.put("/leads/{lead_id}/status")
async def update_lead_status(lead_id: str, status: str = Body(...), current_user: dict = Depends(get_current_user)):
    db().table("leads").update({"status": status}).eq("id", lead_id).execute()
    return {"success": True}
