"""SaforaERP - Customer Router"""
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

class CustomerCreate(BaseModel):
    customer_code: Optional[str] = None
    customer_type: str = "individual"
    name: str
    name_bn: Optional[str] = None
    group_id: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    district_id: Optional[str] = None
    division_id: Optional[str] = None
    trade_license: Optional[str] = None
    tin: Optional[str] = None
    nid: Optional[str] = None
    credit_limit: float = 0
    credit_days: int = 0
    opening_balance: float = 0
    payment_term_id: Optional[str] = None

@router.get("/")
async def list_customers(
    page: int = Query(1), page_size: int = Query(25),
    search: Optional[str] = None, customer_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    q = db().table("customers").select("*, customer_groups(name)").eq("company_id", current_user.get("company_id")).eq("is_active", True)
    if search: q = q.or_(f"name.ilike.%{search}%,customer_code.ilike.%{search}%,phone.ilike.%{search}%")
    if customer_type: q = q.eq("customer_type", customer_type)
    result = q.order("name").execute()
    data = result.data or []
    offset = (page-1)*page_size
    return {"success": True, "data": data[offset:offset+page_size], "total": len(data)}

@router.get("/{customer_id}")
async def get_customer(customer_id: str, current_user: dict = Depends(get_current_user)):
    d = db()
    cust = d.table("customers").select("*").eq("id", customer_id).single().execute()
    if not cust.data: raise HTTPException(404, "Customer not found")
    invoices = d.table("sales_invoices").select("invoice_no, invoice_date, total_amount, paid_amount, due_amount, status").eq("customer_id", customer_id).order("invoice_date", desc=True).limit(20).execute()
    return {"success": True, "data": {**cust.data, "invoices": invoices.data or []}}

@router.post("/")
async def create_customer(c: CustomerCreate, current_user: dict = Depends(get_current_user)):
    d = db()
    data = c.dict(exclude_none=True)
    data["company_id"] = current_user.get("company_id")
    if not data.get("customer_code"):
        data["customer_code"] = f"CUST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    result = d.table("customers").insert(data).execute()
    return {"success": True, "message": "Customer created", "data": result.data}

@router.put("/{customer_id}")
async def update_customer(customer_id: str, c: CustomerCreate, current_user: dict = Depends(get_current_user)):
    data = c.dict(exclude_none=True)
    db().table("customers").update(data).eq("id", customer_id).execute()
    return {"success": True, "message": "Customer updated"}

@router.get("/{customer_id}/statement")
async def customer_statement(customer_id: str, from_date: date, to_date: date, current_user: dict = Depends(get_current_user)):
    d = db()
    invoices = d.table("sales_invoices").select("invoice_date, invoice_no, total_amount, paid_amount, due_amount").eq("customer_id", customer_id).gte("invoice_date", str(from_date)).lte("invoice_date", str(to_date)).execute()
    receipts = d.table("money_receipts").select("receipt_date, receipt_no, amount").eq("customer_id", customer_id).gte("receipt_date", str(from_date)).lte("receipt_date", str(to_date)).execute()
    return {"success": True, "data": {"invoices": invoices.data, "receipts": receipts.data}}

@router.get("/{customer_id}/ledger")
async def customer_ledger(customer_id: str, current_user: dict = Depends(get_current_user)):
    d = db()
    cust = d.table("customers").select("name, opening_balance").eq("id", customer_id).single().execute()
    invs = d.table("sales_invoices").select("invoice_date as date, invoice_no as ref, total_amount as debit, 0 as credit").eq("customer_id", customer_id).execute()
    rcpts = d.table("money_receipts").select("receipt_date as date, receipt_no as ref, 0 as debit, amount as credit").eq("customer_id", customer_id).execute()
    all_entries = sorted((invs.data or []) + (rcpts.data or []), key=lambda x: x["date"])
    balance = float(cust.data.get("opening_balance", 0)) if cust.data else 0
    for entry in all_entries:
        balance += float(entry.get("debit",0)) - float(entry.get("credit",0))
        entry["balance"] = balance
    return {"success": True, "data": {"customer": cust.data, "entries": all_entries, "closing_balance": balance}}
