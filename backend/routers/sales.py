"""SaforaERP - Sales Router"""
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

class SalesOrderItem(BaseModel):
    item_id: str
    quantity: float
    unit_id: Optional[str] = None
    unit_price: float
    discount_pct: float = 0
    vat_pct: float = 0

class SalesOrderCreate(BaseModel):
    order_date: date
    delivery_date: Optional[date] = None
    customer_id: str
    sales_person_id: Optional[str] = None
    store_room_id: Optional[str] = None
    payment_term_id: Optional[str] = None
    remarks: Optional[str] = None
    items: List[SalesOrderItem]

class SalesInvoiceCreate(BaseModel):
    invoice_date: date
    customer_id: str
    order_id: Optional[str] = None
    sales_person_id: Optional[str] = None
    store_room_id: Optional[str] = None
    payment_method_id: Optional[str] = None
    is_pos: bool = False
    discount_amount: float = 0
    delivery_charge: float = 0
    remarks: Optional[str] = None
    items: List[SalesOrderItem]

def calculate_item_totals(items):
    sub_total, vat_total = 0, 0
    processed = []
    for item in items:
        line_total = item.quantity * item.unit_price
        disc_amt = line_total * (item.discount_pct / 100)
        after_disc = line_total - disc_amt
        vat_amt = after_disc * (item.vat_pct / 100)
        total = after_disc + vat_amt
        sub_total += line_total - disc_amt
        vat_total += vat_amt
        processed.append({**item.dict(), "discount_amount": disc_amt, "vat_amount": vat_amt, "total_amount": total})
    return processed, sub_total, vat_total

@router.get("/orders")
async def list_orders(
    page: int = Query(1), page_size: int = Query(25),
    customer_id: Optional[str] = None, status: Optional[str] = None,
    from_date: Optional[date] = None, to_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    q = db().table("sales_orders").select("*, customers(name, customer_code), employees(first_name, last_name)").eq("company_id", current_user.get("company_id"))
    if customer_id: q = q.eq("customer_id", customer_id)
    if status: q = q.eq("status", status)
    if from_date: q = q.gte("order_date", str(from_date))
    if to_date: q = q.lte("order_date", str(to_date))
    result = q.order("order_date", desc=True).execute()
    data = result.data or []
    offset = (page-1)*page_size
    return {"success": True, "data": data[offset:offset+page_size], "total": len(data)}

@router.post("/orders")
async def create_order(order: SalesOrderCreate, current_user: dict = Depends(get_current_user)):
    d = db()
    items, sub_total, vat = calculate_item_totals(order.items)
    order_no = f"SO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    total = sub_total + vat
    header = d.table("sales_orders").insert({
        "company_id": current_user.get("company_id"),
        "branch_id": current_user.get("branch_id"),
        "order_no": order_no, "order_date": str(order.order_date),
        "customer_id": order.customer_id, "sales_person_id": order.sales_person_id,
        "store_room_id": order.store_room_id, "payment_term_id": order.payment_term_id,
        "sub_total": sub_total, "vat_amount": vat, "total_amount": total,
        "status": "pending", "remarks": order.remarks,
        "created_by": current_user.get("sub")
    }).execute()
    order_id = header.data[0]["id"]
    for item in items:
        item["order_id"] = order_id
        item.pop("discount_pct", None); item.pop("vat_pct", None)
    d.table("sales_order_items").insert(items).execute()
    return {"success": True, "message": "Sales order created", "order_no": order_no, "data": header.data}

@router.get("/invoices")
async def list_invoices(
    page: int = Query(1), page_size: int = Query(25),
    customer_id: Optional[str] = None, from_date: Optional[date] = None,
    to_date: Optional[date] = None, current_user: dict = Depends(get_current_user)
):
    q = db().table("sales_invoices").select("*, customers(name, customer_code)").eq("company_id", current_user.get("company_id"))
    if customer_id: q = q.eq("customer_id", customer_id)
    if from_date: q = q.gte("invoice_date", str(from_date))
    if to_date: q = q.lte("invoice_date", str(to_date))
    result = q.order("invoice_date", desc=True).execute()
    data = result.data or []
    offset = (page-1)*page_size
    return {"success": True, "data": data[offset:offset+page_size], "total": len(data)}

@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    d = db()
    inv = d.table("sales_invoices").select("*, customers(*)").eq("id", invoice_id).single().execute()
    if not inv.data: raise HTTPException(404, "Invoice not found")
    items = d.table("sales_invoice_items").select("*, items(item_code, name)").eq("invoice_id", invoice_id).execute()
    return {"success": True, "data": {**inv.data, "items": items.data or []}}

@router.post("/invoices")
async def create_invoice(inv: SalesInvoiceCreate, current_user: dict = Depends(get_current_user)):
    d = db()
    items, sub_total, vat = calculate_item_totals(inv.items)
    invoice_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    total = sub_total + vat + inv.delivery_charge - inv.discount_amount
    header = d.table("sales_invoices").insert({
        "company_id": current_user.get("company_id"),
        "branch_id": current_user.get("branch_id"),
        "invoice_no": invoice_no, "invoice_date": str(inv.invoice_date),
        "customer_id": inv.customer_id, "order_id": inv.order_id,
        "payment_method_id": inv.payment_method_id, "is_pos": inv.is_pos,
        "sub_total": sub_total, "discount_amount": inv.discount_amount,
        "vat_amount": vat, "delivery_charge": inv.delivery_charge,
        "total_amount": total, "due_amount": total,
        "status": "unpaid", "remarks": inv.remarks,
        "created_by": current_user.get("sub")
    }).execute()
    invoice_id = header.data[0]["id"]
    for item in items:
        item["invoice_id"] = invoice_id
        item.pop("discount_pct", None); item.pop("vat_pct", None)
    d.table("sales_invoice_items").insert(items).execute()
    
    # Update stock ledger
    for item in items:
        d.table("stock_ledger").insert({
            "company_id": current_user.get("company_id"),
            "branch_id": current_user.get("branch_id"),
            "item_id": item["item_id"], "transaction_date": str(inv.invoice_date),
            "transaction_type": "sales", "reference_type": "invoice",
            "reference_id": invoice_id, "reference_no": invoice_no,
            "out_qty": item["quantity"], "unit_cost": item["unit_price"],
            "total_cost": item["total_amount"],
            "created_by": current_user.get("sub")
        }).execute()
    
    return {"success": True, "message": "Invoice created", "invoice_no": invoice_no, "data": header.data}

@router.post("/receipts")
async def create_money_receipt(
    customer_id: str = Body(...), amount: float = Body(...),
    payment_method_id: str = Body(...), invoice_id: Optional[str] = Body(None),
    cheque_no: Optional[str] = Body(None), cheque_date: Optional[date] = Body(None),
    remarks: Optional[str] = Body(None), current_user: dict = Depends(get_current_user)
):
    d = db()
    receipt_no = f"MR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    result = d.table("money_receipts").insert({
        "company_id": current_user.get("company_id"),
        "branch_id": current_user.get("branch_id"),
        "receipt_no": receipt_no, "receipt_date": str(date.today()),
        "customer_id": customer_id, "amount": amount,
        "payment_method_id": payment_method_id,
        "cheque_no": cheque_no, "cheque_date": str(cheque_date) if cheque_date else None,
        "reference_invoice_id": invoice_id, "remarks": remarks,
        "created_by": current_user.get("sub")
    }).execute()
    
    if invoice_id:
        inv = d.table("sales_invoices").select("due_amount").eq("id", invoice_id).single().execute()
        if inv.data:
            new_due = max(0, inv.data.get("due_amount", 0) - amount)
            status = "paid" if new_due == 0 else "partial"
            d.table("sales_invoices").update({"due_amount": new_due, "paid_amount": amount, "status": status}).eq("id", invoice_id).execute()
    
    return {"success": True, "message": "Receipt created", "receipt_no": receipt_no, "data": result.data}

@router.get("/reports/daily-summary")
async def daily_sales_summary(
    from_date: date, to_date: date, current_user: dict = Depends(get_current_user)
):
    invs = db().table("sales_invoices").select("invoice_date, total_amount, paid_amount, due_amount, status").eq("company_id", current_user.get("company_id")).gte("invoice_date", str(from_date)).lte("invoice_date", str(to_date)).execute()
    by_date = {}
    for inv in (invs.data or []):
        d = inv["invoice_date"][:10]
        if d not in by_date:
            by_date[d] = {"date": d, "invoices": 0, "total": 0, "collected": 0, "due": 0}
        by_date[d]["invoices"] += 1
        by_date[d]["total"] += float(inv.get("total_amount", 0))
        by_date[d]["collected"] += float(inv.get("paid_amount", 0))
        by_date[d]["due"] += float(inv.get("due_amount", 0))
    return {"success": True, "data": sorted(by_date.values(), key=lambda x: x["date"])}
