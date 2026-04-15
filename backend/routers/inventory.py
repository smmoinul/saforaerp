"""SaforaERP - Inventory Router"""
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

class ItemCreate(BaseModel):
    item_code: str
    barcode: Optional[str] = None
    name: str
    name_bn: Optional[str] = None
    description: Optional[str] = None
    item_type_id: Optional[str] = None
    group_id: Optional[str] = None
    category_id: Optional[str] = None
    subcategory_id: Optional[str] = None
    brand_id: Optional[str] = None
    model_id: Optional[str] = None
    primary_unit_id: Optional[str] = None
    purchase_price: float = 0
    selling_price: float = 0
    mrp: float = 0
    vat_group_id: Optional[str] = None
    reorder_level: float = 0
    reorder_qty: float = 0
    min_stock: float = 0
    max_stock: float = 0
    color_id: Optional[str] = None
    size_id: Optional[str] = None
    is_serialized: bool = False
    has_warranty: bool = False
    warranty_months: int = 0
    image_url: Optional[str] = None

@router.get("/items")
async def list_items(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
    search: Optional[str] = None, group_id: Optional[str] = None,
    category_id: Optional[str] = None, brand_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    q = db().table("items").select("*, item_groups(name), item_categories(name), item_brands(name), item_models(name), units!items_primary_unit_id_fkey(name)").eq("company_id", current_user.get("company_id")).eq("is_active", True)
    if search:
        q = q.or_(f"name.ilike.%{search}%,item_code.ilike.%{search}%,barcode.ilike.%{search}%")
    if group_id: q = q.eq("group_id", group_id)
    if category_id: q = q.eq("category_id", category_id)
    if brand_id: q = q.eq("brand_id", brand_id)
    result = q.order("item_code").execute()
    data = result.data or []
    total = len(data)
    offset = (page-1)*page_size
    return {"success": True, "data": data[offset:offset+page_size], "total": total}

@router.get("/items/{item_id}")
async def get_item(item_id: str, current_user: dict = Depends(get_current_user)):
    result = db().table("items").select("*, item_groups(name), item_categories(name), item_brands(name), item_models(name)").eq("id", item_id).single().execute()
    if not result.data: raise HTTPException(404, "Item not found")
    return {"success": True, "data": result.data}

@router.post("/items")
async def create_item(item: ItemCreate, current_user: dict = Depends(get_current_user)):
    data = item.dict(exclude_none=True)
    data["company_id"] = current_user.get("company_id")
    data["created_by"] = current_user.get("sub")
    result = db().table("items").insert(data).execute()
    return {"success": True, "message": "Item created", "data": result.data}

@router.put("/items/{item_id}")
async def update_item(item_id: str, item: ItemCreate, current_user: dict = Depends(get_current_user)):
    data = item.dict(exclude_none=True)
    data["updated_at"] = datetime.utcnow().isoformat()
    db().table("items").update(data).eq("id", item_id).execute()
    return {"success": True, "message": "Item updated"}

@router.get("/stock")
async def get_current_stock(
    search: Optional[str] = None, store_room_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    q = db().table("stock_ledger").select("item_id, store_room_id, sum(in_qty) as in_qty, sum(out_qty) as out_qty").eq("company_id", current_user.get("company_id"))
    if store_room_id: q = q.eq("store_room_id", store_room_id)
    result = q.execute()
    return {"success": True, "data": result.data}

@router.get("/stock/enquiry")
async def item_enquiry(item_id: str, current_user: dict = Depends(get_current_user)):
    d = db()
    item = d.table("items").select("*").eq("id", item_id).single().execute()
    ledger = d.table("stock_ledger").select("*").eq("item_id", item_id).order("transaction_date", desc=True).limit(50).execute()
    return {"success": True, "data": {"item": item.data, "ledger": ledger.data}}

@router.get("/item-groups")
async def list_item_groups(current_user: dict = Depends(get_current_user)):
    return {"success": True, "data": db().table("item_groups").select("*").eq("is_active", True).order("name").execute().data}

@router.get("/item-categories")
async def list_item_categories(group_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    q = db().table("item_categories").select("*, item_groups(name)").eq("is_active", True)
    if group_id: q = q.eq("group_id", group_id)
    return {"success": True, "data": q.order("name").execute().data}

@router.get("/item-brands")
async def list_item_brands(current_user: dict = Depends(get_current_user)):
    return {"success": True, "data": db().table("item_brands").select("*").eq("is_active", True).order("name").execute().data}

@router.get("/units")
async def list_units(current_user: dict = Depends(get_current_user)):
    return {"success": True, "data": db().table("units").select("*").eq("is_active", True).order("name").execute().data}

@router.get("/store-rooms")
async def list_store_rooms(current_user: dict = Depends(get_current_user)):
    return {"success": True, "data": db().table("store_rooms").select("*").eq("company_id", current_user.get("company_id")).execute().data}

@router.get("/reports/inventory-balance")
async def inventory_balance_report(current_user: dict = Depends(get_current_user)):
    d = db()
    items = d.table("items").select("id, item_code, name, selling_price").eq("company_id", current_user.get("company_id")).eq("is_active", True).execute()
    report = []
    for item in (items.data or []):
        stock = d.table("stock_ledger").select("in_qty, out_qty, unit_cost").eq("item_id", item["id"]).execute()
        qty = sum(r.get("in_qty",0) - r.get("out_qty",0) for r in (stock.data or []))
        value = qty * item.get("selling_price", 0)
        report.append({"item_code": item["item_code"], "name": item["name"], "quantity": qty, "value": value})
    return {"success": True, "data": report}
