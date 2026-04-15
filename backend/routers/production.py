"""SaforaERP - Production Router"""
from fastapi import APIRouter, Depends, Query, Body
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
import sys; sys.path.insert(0, "/home/claude/saforaerp/backend")
from routers.auth import get_current_user
router = APIRouter()
def db():
    from database import get_db_admin
    return get_db_admin()

class BOMItem(BaseModel):
    component_item_id: str
    quantity: float
    unit_id: Optional[str] = None
    waste_percentage: float = 0

class BOMCreate(BaseModel):
    finished_item_id: str
    bom_version: str = "1.0"
    description: Optional[str] = None
    output_qty: float = 1
    unit_id: Optional[str] = None
    effective_from: Optional[date] = None
    items: List[BOMItem]

@router.get("/bom")
async def list_bom(current_user: dict = Depends(get_current_user)):
    result = db().table("bom_headers").select("*, items!bom_headers_finished_item_id_fkey(item_code, name)").eq("company_id", current_user.get("company_id")).execute()
    return {"success": True, "data": result.data}

@router.post("/bom")
async def create_bom(bom: BOMCreate, current_user: dict = Depends(get_current_user)):
    d = db()
    bom_no = f"BOM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    header = d.table("bom_headers").insert({
        "company_id": current_user.get("company_id"),
        "finished_item_id": bom.finished_item_id, "bom_no": bom_no,
        "bom_version": bom.bom_version, "description": bom.description,
        "output_qty": bom.output_qty, "unit_id": bom.unit_id,
        "effective_from": str(bom.effective_from) if bom.effective_from else None,
        "is_current": True, "created_by": current_user.get("sub")
    }).execute()
    bom_id = header.data[0]["id"]
    for item in bom.items:
        d.table("bom_items").insert({**item.dict(), "bom_id": bom_id}).execute()
    return {"success": True, "message": "BOM created", "bom_no": bom_no}

@router.get("/orders")
async def list_production_orders(status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    q = db().table("production_orders").select("*, items!production_orders_finished_item_id_fkey(item_code, name)").eq("company_id", current_user.get("company_id"))
    if status: q = q.eq("status", status)
    return {"success": True, "data": q.order("order_date", desc=True).execute().data}

@router.post("/orders")
async def create_production_order(
    order_date: date = Body(...), finished_item_id: str = Body(...),
    bom_id: str = Body(...), planned_qty: float = Body(...),
    planned_date: Optional[date] = Body(None), remarks: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    order_no = f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    result = db().table("production_orders").insert({
        "company_id": current_user.get("company_id"), "branch_id": current_user.get("branch_id"),
        "order_no": order_no, "order_date": str(order_date),
        "finished_item_id": finished_item_id, "bom_id": bom_id,
        "planned_qty": planned_qty, "planned_date": str(planned_date) if planned_date else None,
        "status": "planned", "remarks": remarks, "created_by": current_user.get("sub")
    }).execute()
    return {"success": True, "message": "Production order created", "order_no": order_no}
