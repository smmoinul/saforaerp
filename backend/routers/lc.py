"""SaforaERP - LC Management Router"""
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

@router.get("/proforma-invoices")
async def list_pi(current_user: dict = Depends(get_current_user)):
    result = db().table("proforma_invoices").select("*, suppliers(name)").eq("company_id", current_user.get("company_id")).execute()
    return {"success": True, "data": result.data}

@router.post("/proforma-invoices")
async def create_pi(
    pi_date: date = Body(...), supplier_id: str = Body(...),
    total_amount: float = Body(...), currency_id: str = Body(...),
    validity_date: Optional[date] = Body(None), payment_terms: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    pi_no = f"PI-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    result = db().table("proforma_invoices").insert({
        "company_id": current_user.get("company_id"), "pi_no": pi_no,
        "pi_date": str(pi_date), "supplier_id": supplier_id,
        "total_amount": total_amount, "currency_id": currency_id,
        "validity_date": str(validity_date) if validity_date else None,
        "payment_terms": payment_terms, "status": "draft",
        "created_by": current_user.get("sub")
    }).execute()
    return {"success": True, "message": "PI created", "pi_no": pi_no}

@router.get("/")
async def list_lc(current_user: dict = Depends(get_current_user)):
    result = db().table("letters_of_credit").select("*, suppliers(name), banks(name)").eq("company_id", current_user.get("company_id")).execute()
    return {"success": True, "data": result.data}

@router.post("/")
async def create_lc(
    lc_date: date = Body(...), pi_id: str = Body(...), supplier_id: str = Body(...),
    bank_id: str = Body(...), lc_amount: float = Body(...), currency_id: str = Body(...),
    expiry_date: Optional[date] = Body(None), shipment_deadline: Optional[date] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    lc_no = f"LC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    result = db().table("letters_of_credit").insert({
        "company_id": current_user.get("company_id"), "lc_no": lc_no,
        "lc_date": str(lc_date), "pi_id": pi_id, "supplier_id": supplier_id,
        "bank_id": bank_id, "lc_amount": lc_amount, "currency_id": currency_id,
        "expiry_date": str(expiry_date) if expiry_date else None,
        "shipment_deadline": str(shipment_deadline) if shipment_deadline else None,
        "status": "opened", "created_by": current_user.get("sub")
    }).execute()
    return {"success": True, "message": "LC created", "lc_no": lc_no}
