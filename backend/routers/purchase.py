"""SaforaERP - Purchase Router"""
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

class POItem(BaseModel):
    item_id: str
    ordered_qty: float
    unit_id: Optional[str] = None
    unit_price: float
    discount_pct: float = 0
    vat_pct: float = 0

class POCreate(BaseModel):
    po_date: date
    supplier_id: str
    pr_id: Optional[str] = None
    expected_delivery: Optional[date] = None
    payment_term_id: Optional[str] = None
    remarks: Optional[str] = None
    items: List[POItem]

class PurchaseCreate(BaseModel):
    purchase_date: date
    invoice_no: Optional[str] = None
    invoice_date: Optional[date] = None
    supplier_id: str
    po_id: Optional[str] = None
    store_room_id: Optional[str] = None
    payment_method_id: Optional[str] = None
    other_charges: float = 0
    remarks: Optional[str] = None
    items: List[POItem]

@router.get("/requisitions")
async def list_requisitions(status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    q = db().table("purchase_requisitions").select("*, departments(name)").eq("company_id", current_user.get("company_id"))
    if status: q = q.eq("status", status)
    return {"success": True, "data": q.order("pr_date", desc=True).execute().data}

@router.post("/requisitions")
async def create_requisition(
    required_date: date = Body(...), department_id: str = Body(...),
    remarks: Optional[str] = Body(None),
    items: List[dict] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    d = db()
    pr_no = f"PR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pr = d.table("purchase_requisitions").insert({
        "company_id": current_user.get("company_id"),
        "branch_id": current_user.get("branch_id"),
        "pr_no": pr_no, "pr_date": str(date.today()),
        "required_date": str(required_date),
        "department_id": department_id, "status": "pending", "remarks": remarks,
        "created_by": current_user.get("sub")
    }).execute()
    pr_id = pr.data[0]["id"]
    for item in items:
        item["pr_id"] = pr_id
    d.table("purchase_requisition_items").insert(items).execute()
    return {"success": True, "message": "PR created", "pr_no": pr_no}

@router.get("/orders")
async def list_po(supplier_id: Optional[str] = None, status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    q = db().table("purchase_orders").select("*, suppliers(name)").eq("company_id", current_user.get("company_id"))
    if supplier_id: q = q.eq("supplier_id", supplier_id)
    if status: q = q.eq("status", status)
    return {"success": True, "data": q.order("po_date", desc=True).execute().data}

@router.post("/orders")
async def create_po(po: POCreate, current_user: dict = Depends(get_current_user)):
    d = db()
    po_no = f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    items_data = []
    sub_total = 0
    for item in po.items:
        line = item.ordered_qty * item.unit_price
        disc = line * (item.discount_pct/100)
        vat = (line-disc) * (item.vat_pct/100)
        total = line - disc + vat
        sub_total += total
        items_data.append({**item.dict(), "discount_amount": disc, "vat_amount": vat, "total_amount": total})
    
    header = d.table("purchase_orders").insert({
        "company_id": current_user.get("company_id"), "branch_id": current_user.get("branch_id"),
        "po_no": po_no, "po_date": str(po.po_date), "supplier_id": po.supplier_id,
        "pr_id": po.pr_id, "payment_term_id": po.payment_term_id,
        "total_amount": sub_total, "status": "open", "remarks": po.remarks,
        "created_by": current_user.get("sub")
    }).execute()
    po_id = header.data[0]["id"]
    for item in items_data:
        item["po_id"] = po_id
        item.pop("discount_pct", None); item.pop("vat_pct", None)
    d.table("purchase_order_items").insert(items_data).execute()
    return {"success": True, "message": "PO created", "po_no": po_no, "data": header.data}

@router.get("/purchases")
async def list_purchases(supplier_id: Optional[str] = None, from_date: Optional[date] = None, to_date: Optional[date] = None, current_user: dict = Depends(get_current_user)):
    q = db().table("purchases").select("*, suppliers(name)").eq("company_id", current_user.get("company_id"))
    if supplier_id: q = q.eq("supplier_id", supplier_id)
    if from_date: q = q.gte("purchase_date", str(from_date))
    if to_date: q = q.lte("purchase_date", str(to_date))
    return {"success": True, "data": q.order("purchase_date", desc=True).execute().data}

@router.post("/purchases")
async def create_purchase(pur: PurchaseCreate, current_user: dict = Depends(get_current_user)):
    d = db()
    pur_no = f"PUR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    items_data = []
    sub_total = 0
    for item in pur.items:
        line = item.ordered_qty * item.unit_price
        disc = line * (item.discount_pct/100)
        vat = (line-disc) * (item.vat_pct/100)
        total = line - disc + vat
        sub_total += total
        items_data.append({"item_id": item.item_id, "quantity": item.ordered_qty, "unit_id": item.unit_id, "unit_cost": item.unit_price, "discount_amount": disc, "vat_amount": vat, "total_amount": total})
    
    total_amt = sub_total + pur.other_charges
    header = d.table("purchases").insert({
        "company_id": current_user.get("company_id"), "branch_id": current_user.get("branch_id"),
        "purchase_no": pur_no, "purchase_date": str(pur.purchase_date),
        "invoice_no": pur.invoice_no, "supplier_id": pur.supplier_id, "po_id": pur.po_id,
        "store_room_id": pur.store_room_id, "payment_method_id": pur.payment_method_id,
        "sub_total": sub_total, "other_charges": pur.other_charges, "total_amount": total_amt,
        "due_amount": total_amt, "status": "unpaid", "remarks": pur.remarks,
        "created_by": current_user.get("sub")
    }).execute()
    pur_id = header.data[0]["id"]
    for item in items_data:
        item["purchase_id"] = pur_id
    d.table("purchase_items").insert(items_data).execute()
    
    # Update stock
    for item in items_data:
        d.table("stock_ledger").insert({
            "company_id": current_user.get("company_id"), "branch_id": current_user.get("branch_id"),
            "store_room_id": pur.store_room_id, "item_id": item["item_id"],
            "transaction_date": str(pur.purchase_date), "transaction_type": "purchase",
            "reference_type": "purchase", "reference_id": pur_id, "reference_no": pur_no,
            "in_qty": item["quantity"], "unit_cost": item["unit_cost"], "total_cost": item["total_amount"],
            "created_by": current_user.get("sub")
        }).execute()
    
    return {"success": True, "message": "Purchase created", "purchase_no": pur_no}
