"""SaforaERP - Accounts Router"""
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
import sys
sys.path.insert(0, "/home/claude/saforaerp/backend")
from routers.auth import get_current_user

router = APIRouter()
def db():
    from database import get_db_admin
    return get_db_admin()

class VoucherLine(BaseModel):
    account_id: str
    debit_amount: float = 0
    credit_amount: float = 0
    narration: Optional[str] = None

class VoucherCreate(BaseModel):
    voucher_date: date
    voucher_type: str  # debit, credit, journal, contra, mixed
    narration: Optional[str] = None
    reference_no: Optional[str] = None
    lines: List[VoucherLine]

@router.get("/chart-of-accounts")
async def list_coa(parent_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    q = db().table("chart_of_accounts").select("*").eq("company_id", current_user.get("company_id")).eq("is_active", True)
    if parent_id: q = q.eq("parent_id", parent_id)
    return {"success": True, "data": q.order("account_code").execute().data}

@router.post("/chart-of-accounts")
async def create_account(
    account_code: str = Body(...), account_name: str = Body(...),
    parent_id: Optional[str] = Body(None), gl_category_id: Optional[str] = Body(None),
    account_type: str = Body(...), balance_type: str = Body("debit"),
    opening_balance: float = Body(0),
    current_user: dict = Depends(get_current_user)
):
    result = db().table("chart_of_accounts").insert({
        "company_id": current_user.get("company_id"),
        "account_code": account_code, "account_name": account_name,
        "parent_id": parent_id, "gl_category_id": gl_category_id,
        "account_type": account_type, "balance_type": balance_type,
        "opening_balance": opening_balance
    }).execute()
    return {"success": True, "data": result.data}

@router.get("/vouchers")
async def list_vouchers(
    voucher_type: Optional[str] = None, from_date: Optional[date] = None,
    to_date: Optional[date] = None, current_user: dict = Depends(get_current_user)
):
    q = db().table("vouchers").select("*").eq("company_id", current_user.get("company_id"))
    if voucher_type: q = q.eq("voucher_type", voucher_type)
    if from_date: q = q.gte("voucher_date", str(from_date))
    if to_date: q = q.lte("voucher_date", str(to_date))
    return {"success": True, "data": q.order("voucher_date", desc=True).execute().data}

@router.post("/vouchers")
async def create_voucher(voucher: VoucherCreate, current_user: dict = Depends(get_current_user)):
    d = db()
    if abs(sum(l.debit_amount for l in voucher.lines) - sum(l.credit_amount for l in voucher.lines)) > 0.01:
        raise HTTPException(400, "Debit and credit must be equal")
    voucher_no = f"V-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    total_dr = sum(l.debit_amount for l in voucher.lines)
    header = d.table("vouchers").insert({
        "company_id": current_user.get("company_id"), "branch_id": current_user.get("branch_id"),
        "voucher_no": voucher_no, "voucher_date": str(voucher.voucher_date),
        "voucher_type": voucher.voucher_type, "narration": voucher.narration,
        "reference_no": voucher.reference_no,
        "total_debit": total_dr, "total_credit": total_dr,
        "status": "posted", "created_by": current_user.get("sub")
    }).execute()
    vid = header.data[0]["id"]
    for line in voucher.lines:
        d.table("voucher_lines").insert({**line.dict(), "voucher_id": vid}).execute()
    return {"success": True, "message": "Voucher created", "voucher_no": voucher_no}

@router.get("/reports/trial-balance")
async def trial_balance(fiscal_year_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    d = db()
    accounts = d.table("chart_of_accounts").select("id, account_code, account_name, account_type, balance_type, opening_balance").eq("company_id", current_user.get("company_id")).eq("is_leaf", True).execute()
    result = []
    for acc in (accounts.data or []):
        lines = d.table("voucher_lines").select("debit_amount, credit_amount").eq("account_id", acc["id"]).execute()
        total_dr = sum(float(l.get("debit_amount",0)) for l in (lines.data or []))
        total_cr = sum(float(l.get("credit_amount",0)) for l in (lines.data or []))
        ob = float(acc.get("opening_balance", 0))
        if acc.get("balance_type") == "debit":
            balance = ob + total_dr - total_cr
        else:
            balance = ob + total_cr - total_dr
        result.append({**acc, "total_debit": total_dr, "total_credit": total_cr, "balance": balance})
    return {"success": True, "data": result}

@router.get("/reports/cash-book")
async def cash_book(from_date: date, to_date: date, current_user: dict = Depends(get_current_user)):
    d = db()
    cash_acc = d.table("chart_of_accounts").select("id").eq("company_id", current_user.get("company_id")).eq("account_type", "asset").ilike("account_name", "%cash%").execute()
    if not cash_acc.data: return {"success": True, "data": []}
    acc_ids = [a["id"] for a in cash_acc.data]
    vouchers = d.table("voucher_lines").select("*, vouchers(voucher_date, voucher_no, narration)").in_("account_id", acc_ids).gte("vouchers.voucher_date", str(from_date)).lte("vouchers.voucher_date", str(to_date)).execute()
    return {"success": True, "data": vouchers.data}
