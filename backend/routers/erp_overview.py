"""SaforaERP - ERP Overview / Dashboard Router"""
from fastapi import APIRouter, Depends
from datetime import date, datetime
import sys; sys.path.insert(0, "/home/claude/saforaerp/backend")
from routers.auth import get_current_user
router = APIRouter()
def db():
    from database import get_db_admin
    return get_db_admin()

@router.get("/dashboard")
async def management_dashboard(current_user: dict = Depends(get_current_user)):
    d = db()
    cid = current_user.get("company_id")
    today = str(date.today())
    
    # Sales today
    today_sales = d.table("sales_invoices").select("total_amount").eq("company_id", cid).eq("invoice_date", today).execute()
    total_today_sales = sum(float(r.get("total_amount",0)) for r in (today_sales.data or []))
    
    # Active employees
    emp_count = d.table("employees").select("id", count="exact").eq("company_id", cid).eq("employee_status", "active").execute()
    
    # Outstanding dues
    outstanding = d.table("sales_invoices").select("due_amount").eq("company_id", cid).neq("status", "paid").execute()
    total_outstanding = sum(float(r.get("due_amount",0)) for r in (outstanding.data or []))
    
    # Pending orders
    pending_so = d.table("sales_orders").select("id", count="exact").eq("company_id", cid).eq("status", "pending").execute()
    pending_po = d.table("purchase_orders").select("id", count="exact").eq("company_id", cid).eq("status", "open").execute()
    
    # Leave pending
    leave_pending = d.table("leave_applications").select("id", count="exact").eq("status", "pending").execute()
    
    return {
        "success": True,
        "data": {
            "today_sales": total_today_sales,
            "total_employees": emp_count.count or 0,
            "outstanding_dues": total_outstanding,
            "pending_sales_orders": pending_so.count or 0,
            "pending_purchase_orders": pending_po.count or 0,
            "pending_leave_applications": leave_pending.count or 0,
            "as_of": datetime.now().isoformat(),
        }
    }

@router.get("/pending-overview")
async def pending_overview(current_user: dict = Depends(get_current_user)):
    d = db()
    cid = current_user.get("company_id")
    return {
        "success": True,
        "data": {
            "pending_requisitions": d.table("purchase_requisitions").select("id", count="exact").eq("company_id", cid).eq("status", "pending").execute().count or 0,
            "open_pos": d.table("purchase_orders").select("id", count="exact").eq("company_id", cid).eq("status", "open").execute().count or 0,
            "unpaid_invoices": d.table("sales_invoices").select("id", count="exact").eq("company_id", cid).eq("status", "unpaid").execute().count or 0,
            "pending_leaves": d.table("leave_applications").select("id", count="exact").eq("status", "pending").execute().count or 0,
            "active_job_cards": d.table("job_cards").select("id", count="exact").eq("company_id", cid).neq("status", "delivered").execute().count or 0,
        }
    }
