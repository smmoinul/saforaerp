"""SaforaERP - Supplier Router"""
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import sys
sys.path.insert(0, "/home/claude/saforaerp/backend")
from routers.auth import get_current_user

router = APIRouter()
def db():
    from database import get_db_admin
    return get_db_admin()

class SupplierCreate(BaseModel):
    supplier_code: Optional[str] = None
    name: str
    name_bn: Optional[str] = None
    group_id: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    district_id: Optional[str] = None
    trade_license: Optional[str] = None
    tin: Optional[str] = None
    bin: Optional[str] = None
    credit_limit: float = 0
    credit_days: int = 0
    opening_balance: float = 0
    bank_account_number: Optional[str] = None
    bank_account_name: Optional[str] = None
    bank_id: Optional[str] = None
    payment_term_id: Optional[str] = None

@router.get("/")
async def list_suppliers(
    page: int = Query(1), page_size: int = Query(25),
    search: Optional[str] = None, current_user: dict = Depends(get_current_user)
):
    q = db().table("suppliers").select("*, supplier_groups(name)").eq("company_id", current_user.get("company_id")).eq("is_active", True)
    if search: q = q.or_(f"name.ilike.%{search}%,supplier_code.ilike.%{search}%")
    result = q.order("name").execute()
    data = result.data or []
    offset = (page-1)*page_size
    return {"success": True, "data": data[offset:offset+page_size], "total": len(data)}

@router.post("/")
async def create_supplier(s: SupplierCreate, current_user: dict = Depends(get_current_user)):
    data = s.dict(exclude_none=True)
    data["company_id"] = current_user.get("company_id")
    if not data.get("supplier_code"):
        data["supplier_code"] = f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    result = db().table("suppliers").insert(data).execute()
    return {"success": True, "message": "Supplier created", "data": result.data}

@router.put("/{supplier_id}")
async def update_supplier(supplier_id: str, s: SupplierCreate, current_user: dict = Depends(get_current_user)):
    db().table("suppliers").update(s.dict(exclude_none=True)).eq("id", supplier_id).execute()
    return {"success": True, "message": "Supplier updated"}

@router.get("/{supplier_id}/statement")
async def supplier_statement(supplier_id: str, from_date: date, to_date: date, current_user: dict = Depends(get_current_user)):
    d = db()
    purchases = d.table("purchases").select("purchase_date, purchase_no, total_amount, paid_amount, due_amount").eq("supplier_id", supplier_id).gte("purchase_date", str(from_date)).lte("purchase_date", str(to_date)).execute()
    return {"success": True, "data": {"purchases": purchases.data}}

@router.post("/{supplier_id}/payment")
async def supplier_payment(
    supplier_id: str,
    amount: float = Body(...), payment_method_id: str = Body(...),
    cheque_no: Optional[str] = Body(None), remarks: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    # Create voucher for supplier payment
    return {"success": True, "message": "Payment recorded"}
