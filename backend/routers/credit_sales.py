"""SaforaERP - Credit Sales Router"""
from fastapi import APIRouter, Depends, Query, Body
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import sys; sys.path.insert(0, "/home/claude/saforaerp/backend")
from routers.auth import get_current_user
router = APIRouter()
def db():
    from database import get_db_admin
    return get_db_admin()

class CreditSaleCreate(BaseModel):
    sale_date: date
    customer_id: str
    invoice_id: Optional[str] = None
    total_amount: float
    down_payment: float = 0
    interest_rate: float = 0
    total_installments: int
    first_installment_date: date
    guarantor_name: Optional[str] = None
    guarantor_phone: Optional[str] = None
    guarantor_nid: Optional[str] = None

@router.post("/")
async def create_credit_sale(cs: CreditSaleCreate, current_user: dict = Depends(get_current_user)):
    d = db()
    cs_no = f"CS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    financed = cs.total_amount - cs.down_payment
    total_interest = financed * (cs.interest_rate/100) * (cs.total_installments/12)
    total_payable = financed + total_interest
    installment_amt = total_payable / cs.total_installments
    
    header = d.table("credit_sales").insert({
        "company_id": current_user.get("company_id"), "branch_id": current_user.get("branch_id"),
        "credit_sale_no": cs_no, "sale_date": str(cs.sale_date),
        "customer_id": cs.customer_id, "invoice_id": cs.invoice_id,
        "total_amount": cs.total_amount, "down_payment": cs.down_payment,
        "financed_amount": financed, "interest_rate": cs.interest_rate,
        "total_installments": cs.total_installments, "installment_amount": installment_amt,
        "first_installment_date": str(cs.first_installment_date),
        "guarantor_name": cs.guarantor_name, "guarantor_phone": cs.guarantor_phone,
        "guarantor_nid": cs.guarantor_nid, "status": "active",
        "created_by": current_user.get("sub")
    }).execute()
    cs_id = header.data[0]["id"]
    
    # Generate installment schedule
    schedules = []
    for i in range(cs.total_installments):
        due_date = cs.first_installment_date + relativedelta(months=i)
        schedules.append({
            "credit_sale_id": cs_id, "installment_no": i+1,
            "due_date": str(due_date), "installment_amount": installment_amt,
            "principal_amount": financed/cs.total_installments,
            "interest_amount": total_interest/cs.total_installments,
            "status": "pending"
        })
    d.table("installment_schedules").insert(schedules).execute()
    return {"success": True, "message": "Credit sale created", "credit_sale_no": cs_no, "installment_amount": installment_amt}

@router.get("/")
async def list_credit_sales(status: Optional[str] = None, customer_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    q = db().table("credit_sales").select("*, customers(name, phone)").eq("company_id", current_user.get("company_id"))
    if status: q = q.eq("status", status)
    if customer_id: q = q.eq("customer_id", customer_id)
    return {"success": True, "data": q.order("sale_date", desc=True).execute().data}

@router.get("/{cs_id}/schedule")
async def get_schedule(cs_id: str, current_user: dict = Depends(get_current_user)):
    schedule = db().table("installment_schedules").select("*").eq("credit_sale_id", cs_id).order("installment_no").execute()
    return {"success": True, "data": schedule.data}

@router.post("/{cs_id}/collect")
async def collect_installment(cs_id: str, installment_id: str = Body(...), amount: float = Body(...), payment_method_id: str = Body(...), current_user: dict = Depends(get_current_user)):
    d = db()
    inst = d.table("installment_schedules").select("*").eq("id", installment_id).single().execute()
    if not inst.data: return {"success": False, "message": "Installment not found"}
    total_paid = float(inst.data.get("paid_amount",0)) + amount
    status = "paid" if total_paid >= float(inst.data.get("installment_amount",0)) else "partial"
    d.table("installment_schedules").update({"paid_amount": total_paid, "paid_date": str(date.today()), "status": status}).eq("id", installment_id).execute()
    return {"success": True, "message": "Collection recorded"}
