"""SaforaERP - Service Management Router"""
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

class JobCardCreate(BaseModel):
    job_date: date
    customer_id: str
    vehicle_model: Optional[str] = None
    vehicle_reg_no: Optional[str] = None
    chassis_no: Optional[str] = None
    engine_no: Optional[str] = None
    service_type_id: Optional[str] = None
    complaint: Optional[str] = None
    diagnosis: Optional[str] = None
    estimated_amount: Optional[float] = None
    remarks: Optional[str] = None

@router.get("/job-cards")
async def list_job_cards(status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    q = db().table("job_cards").select("*, customers(name, phone), service_types(name)").eq("company_id", current_user.get("company_id"))
    if status: q = q.eq("status", status)
    return {"success": True, "data": q.order("job_date", desc=True).execute().data}

@router.post("/job-cards")
async def create_job_card(jc: JobCardCreate, current_user: dict = Depends(get_current_user)):
    jc_no = f"JC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    result = db().table("job_cards").insert({
        "company_id": current_user.get("company_id"), "branch_id": current_user.get("branch_id"),
        "job_card_no": jc_no, **{k:v for k,v in jc.dict().items() if v is not None},
        "job_date": str(jc.job_date), "status": "received", "created_by": current_user.get("sub")
    }).execute()
    return {"success": True, "message": "Job card created", "job_card_no": jc_no}

@router.put("/job-cards/{jc_id}/status")
async def update_job_card_status(jc_id: str, status: str = Body(...), final_amount: Optional[float] = Body(None), current_user: dict = Depends(get_current_user)):
    data = {"status": status}
    if final_amount: data["final_amount"] = final_amount
    db().table("job_cards").update(data).eq("id", jc_id).execute()
    return {"success": True}

@router.get("/setup/types")
async def service_types(current_user: dict = Depends(get_current_user)):
    return {"success": True, "data": db().table("service_types").select("*").eq("company_id", current_user.get("company_id")).execute().data}
