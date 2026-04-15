"""
SaforaERP - Complete FastAPI Backend
Single-file version for easy setup
Run: uvicorn saforaerp_backend_main:app --reload --port 8000
"""

from fastapi import FastAPI, Depends, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Optional, List
from datetime import date, datetime, timedelta
from uuid import UUID
import os
import jwt

# ── CONFIG ────────────────────────────────────────────────────
class Settings(BaseSettings):
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "your-anon-key")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "your-service-key")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "saforaerp-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5500", "*"]
    class Config:
        env_file = ".env"

settings = Settings()

# ── DATABASE ──────────────────────────────────────────────────
_sb_client = None
def get_db():
    global _sb_client
    if _sb_client is None:
        from supabase import create_client
        _sb_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return _sb_client

# ── AUTH HELPERS ──────────────────────────────────────────────
security = HTTPBearer(auto_error=False)

def create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + expires_delta
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except:
        raise HTTPException(401, "Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(401, "Not authenticated")
    return verify_token(credentials.credentials)

# ── APP ───────────────────────────────────────────────────────
app = FastAPI(title="SaforaERP API", version="2.0.0", docs_url="/api/docs")
app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health(): return {"status": "ok", "app": "SaforaERP", "version": "2.0.0"}

# ══════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.post("/api/auth/login")
async def login(email: str = Body(...), password: str = Body(...)):
    db = get_db()
    try:
        res = db.auth.sign_in_with_password({"email": email, "password": password})
    except:
        raise HTTPException(401, "Invalid email or password")
    uid = str(res.user.id)
    profile = db.table("user_profiles").select("*, companies(*), branches(*)").eq("id", uid).single().execute()
    if not profile.data or not profile.data.get("is_active"):
        raise HTTPException(403, "Account inactive or not found")
    p = profile.data
    token_data = {"sub": uid, "email": email, "role": p.get("role","general"),
                  "company_id": str(p.get("company_id","")),
                  "branch_id": str(p.get("branch_id",""))}
    db.table("user_profiles").update({"last_login": datetime.utcnow().isoformat()}).eq("id", uid).execute()
    db.table("user_login_history").insert({"user_id": uid, "status": "success"}).execute()
    return {
        "access_token": create_token(token_data, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)),
        "refresh_token": create_token({"sub": uid, "type": "refresh"}, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {"id": uid, "email": email, "full_name": p.get("full_name"),
                 "role": p.get("role"), "company": p.get("companies"), "branch": p.get("branches")}
    }

@app.get("/api/auth/me")
async def me(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("user_profiles").select("*, companies(*), branches(*), user_groups(*)").eq("id", u["sub"]).single().execute()
    return {"success": True, "data": r.data}

@app.post("/api/auth/logout")
async def logout(u = Depends(get_current_user)):
    db = get_db()
    db.table("user_login_history").update({"logout_at": datetime.utcnow().isoformat()}).eq("user_id", u["sub"]).is_("logout_at", "null").execute()
    return {"success": True, "message": "Logged out"}

@app.get("/api/auth/login-history")
async def login_history(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("user_login_history").select("*, user_profiles(full_name, email)").order("login_at", desc=True).limit(100).execute()
    return {"success": True, "data": r.data}

# ══════════════════════════════════════════════════════════════
# HR ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.get("/api/hr/employees")
async def list_employees(page: int = 1, page_size: int = 25, search: Optional[str] = None,
    department_id: Optional[str] = None, status: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("employees").select("*, departments(name), designations(name), employee_grades(name)").eq("company_id", u["company_id"])
    if search: q = q.ilike("full_name", f"%{search}%")
    if department_id: q = q.eq("department_id", department_id)
    if status: q = q.eq("employee_status", status)
    r = q.order("employee_code").execute()
    data = r.data or []
    offset = (page-1)*page_size
    return {"success": True, "data": data[offset:offset+page_size], "total": len(data)}

@app.get("/api/hr/employees/{eid}")
async def get_employee(eid: str, u = Depends(get_current_user)):
    db = get_db()
    r = db.table("employees").select("*, departments(*), designations(*), employee_grades(*)").eq("id", eid).single().execute()
    if not r.data: raise HTTPException(404, "Not found")
    emp = r.data
    emp["educations"] = db.table("employee_educations").select("*").eq("employee_id", eid).execute().data or []
    emp["experiences"] = db.table("employee_experiences").select("*").eq("employee_id", eid).execute().data or []
    return {"success": True, "data": emp}

@app.post("/api/hr/employees")
async def create_employee(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["company_id"] = u["company_id"]
    data["created_by"] = u["sub"]
    if "date_of_birth" in data and data["date_of_birth"]: data["date_of_birth"] = str(data["date_of_birth"])
    if "joining_date" in data and data["joining_date"]: data["joining_date"] = str(data["joining_date"])
    r = db.table("employees").insert(data).execute()
    return {"success": True, "message": "Employee created", "data": r.data}

@app.put("/api/hr/employees/{eid}")
async def update_employee(eid: str, data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["updated_at"] = datetime.utcnow().isoformat()
    db.table("employees").update(data).eq("id", eid).execute()
    return {"success": True, "message": "Updated"}

@app.get("/api/hr/departments")
async def list_departments(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("departments").select("*").eq("company_id", u["company_id"]).eq("is_active", True).order("name").execute()
    return {"success": True, "data": r.data}

@app.post("/api/hr/departments")
async def create_department(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["company_id"] = u["company_id"]
    r = db.table("departments").insert(data).execute()
    return {"success": True, "data": r.data}

@app.get("/api/hr/designations")
async def list_designations(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("designations").select("*").eq("company_id", u["company_id"]).eq("is_active", True).execute()
    return {"success": True, "data": r.data}

@app.post("/api/hr/designations")
async def create_designation(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["company_id"] = u["company_id"]
    r = db.table("designations").insert(data).execute()
    return {"success": True, "data": r.data}

@app.get("/api/hr/grades")
async def list_grades(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("employee_grades").select("*").eq("company_id", u["company_id"]).execute()
    return {"success": True, "data": r.data}

@app.get("/api/hr/attendance")
async def get_attendance(employee_id: Optional[str] = None, from_date: Optional[str] = None,
    to_date: Optional[str] = None, month: Optional[int] = None, year: Optional[int] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("attendance_records").select("*, employees(employee_code, first_name, last_name)")
    if employee_id: q = q.eq("employee_id", employee_id)
    if from_date: q = q.gte("attendance_date", from_date)
    if to_date: q = q.lte("attendance_date", to_date)
    if month and year:
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        q = q.gte("attendance_date", f"{year}-{month:02d}-01").lte("attendance_date", f"{year}-{month:02d}-{last_day}")
    r = q.order("attendance_date", desc=True).execute()
    return {"success": True, "data": r.data}

@app.post("/api/hr/attendance")
async def save_attendance(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    for f in ["attendance_date", "in_time", "out_time"]:
        if f in data and data[f]: data[f] = str(data[f])
    r = db.table("attendance_records").upsert(data, on_conflict="employee_id,attendance_date").execute()
    return {"success": True, "data": r.data}

@app.get("/api/hr/leave/types")
async def leave_types(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("leave_types").select("*, leave_categories(name)").eq("company_id", u["company_id"]).eq("is_active", True).execute()
    return {"success": True, "data": r.data}

@app.get("/api/hr/leave/applications")
async def leave_applications(status: Optional[str] = None, employee_id: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("leave_applications").select("*, employees(employee_code, first_name, last_name), leave_types(name)")
    if status: q = q.eq("status", status)
    if employee_id: q = q.eq("employee_id", employee_id)
    r = q.order("applied_at", desc=True).execute()
    return {"success": True, "data": r.data}

@app.post("/api/hr/leave/apply")
async def apply_leave(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    from_d = datetime.strptime(str(data["from_date"]), "%Y-%m-%d")
    to_d = datetime.strptime(str(data["to_date"]), "%Y-%m-%d")
    total_days = (to_d - from_d).days + 1
    app_no = f"LA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    r = db.table("leave_applications").insert({
        "application_no": app_no, "employee_id": data["employee_id"],
        "leave_type_id": data["leave_type_id"], "from_date": str(data["from_date"]),
        "to_date": str(data["to_date"]), "total_days": total_days,
        "reason": data.get("reason",""), "status": "pending"
    }).execute()
    return {"success": True, "message": "Leave applied", "data": r.data}

@app.put("/api/hr/leave/applications/{app_id}/approve")
async def approve_leave(app_id: str, u = Depends(get_current_user)):
    db = get_db()
    db.table("leave_applications").update({"status": "approved", "approved_by": u["sub"], "approved_at": datetime.utcnow().isoformat()}).eq("id", app_id).execute()
    return {"success": True, "message": "Approved"}

@app.put("/api/hr/leave/applications/{app_id}/reject")
async def reject_leave(app_id: str, rejection_reason: str = Body(...), u = Depends(get_current_user)):
    db = get_db()
    db.table("leave_applications").update({"status": "rejected", "rejection_reason": rejection_reason}).eq("id", app_id).execute()
    return {"success": True, "message": "Rejected"}

@app.get("/api/hr/payroll/salary-sheets")
async def salary_sheets(month: Optional[int] = None, year: Optional[int] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("salary_sheets").select("*").eq("company_id", u["company_id"])
    if month: q = q.eq("month", month)
    if year: q = q.eq("year", year)
    r = q.order("year", desc=True).order("month", desc=True).execute()
    return {"success": True, "data": r.data}

@app.post("/api/hr/payroll/prepare")
async def prepare_salary(month: int = Body(...), year: int = Body(...), branch_id: Optional[str] = Body(None), u = Depends(get_current_user)):
    db = get_db()
    cid = u["company_id"]
    emps = db.table("employees").select("*, employee_grades(id)").eq("company_id", cid).eq("employee_status", "active").execute()
    sheet = db.table("salary_sheets").upsert({"company_id": cid, "branch_id": branch_id, "month": month, "year": year, "status": "draft", "processed_by": u["sub"], "processed_at": datetime.utcnow().isoformat()}, on_conflict="company_id,branch_id,month,year").execute()
    sid = sheet.data[0]["id"] if sheet.data else None
    grades = db.table("salary_grades").select("*").eq("is_active", True).execute()
    gmap = {g["grade_id"]: g for g in (grades.data or [])}
    total_net = 0
    for emp in (emps.data or []):
        grade = gmap.get(emp.get("grade_id"), {})
        basic = float(grade.get("basic_salary", 0))
        house = basic * 0.5; medical = basic * 0.1; transport = basic * 0.1
        gross = basic + house + medical + transport
        pf = basic * 0.1; net = gross - pf; total_net += net
        db.table("salary_details").upsert({"salary_sheet_id": sid, "employee_id": emp["id"],
            "basic_salary": basic, "house_rent": house, "medical_allowance": medical,
            "transport_allowance": transport, "gross_salary": gross, "pf_deduction": pf,
            "net_pay": net, "present_days": 26}, on_conflict="salary_sheet_id,employee_id").execute()
    db.table("salary_sheets").update({"total_net_pay": total_net, "status": "processed"}).eq("id", sid).execute()
    return {"success": True, "message": f"Salary prepared", "total_employees": len(emps.data or []), "total_net_pay": total_net}

@app.get("/api/hr/payroll/salary-details/{sheet_id}")
async def salary_details(sheet_id: str, u = Depends(get_current_user)):
    db = get_db()
    r = db.table("salary_details").select("*, employees(employee_code, first_name, last_name, designations(name))").eq("salary_sheet_id", sheet_id).execute()
    return {"success": True, "data": r.data}

@app.get("/api/hr/reports/employee-list")
async def emp_list_report(department_id: Optional[str] = None, status: str = "active", u = Depends(get_current_user)):
    db = get_db()
    q = db.table("employees").select("employee_code, first_name, last_name, mobile_number, official_email, joining_date, employee_status, departments(name), designations(name)").eq("company_id", u["company_id"]).eq("is_active", True)
    if department_id: q = q.eq("department_id", department_id)
    if status: q = q.eq("employee_status", status)
    r = q.order("employee_code").execute()
    return {"success": True, "data": r.data, "total": len(r.data or [])}

@app.get("/api/hr/reports/attendance-summary")
async def att_summary(month: int, year: int, u = Depends(get_current_user)):
    db = get_db()
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    att = db.table("attendance_records").select("employee_id, status, employees(employee_code, first_name, last_name)").gte("attendance_date", f"{year}-{month:02d}-01").lte("attendance_date", f"{year}-{month:02d}-{last_day}").execute()
    summary = {}
    for rec in (att.data or []):
        eid = rec["employee_id"]
        if eid not in summary:
            summary[eid] = {"employee": rec.get("employees",{}), "present": 0, "absent": 0, "late": 0, "leave": 0, "total": 0}
        summary[eid]["total"] += 1
        s = rec.get("status","")
        if s == "present": summary[eid]["present"] += 1
        elif s == "absent": summary[eid]["absent"] += 1
        elif s == "late": summary[eid]["late"] += 1
        elif s == "on_leave": summary[eid]["leave"] += 1
    return {"success": True, "data": list(summary.values()), "month": month, "year": year}

@app.get("/api/hr/loans")
async def list_loans(employee_id: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("employee_loans").select("*, employees(employee_code, first_name, last_name), loan_types(name)")
    if employee_id: q = q.eq("employee_id", employee_id)
    r = q.order("applied_date", desc=True).execute()
    return {"success": True, "data": r.data}

@app.post("/api/hr/loans")
async def create_loan(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["loan_no"] = f"LN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["applied_date"] = str(date.today())
    data["status"] = "pending"
    r = db.table("employee_loans").insert(data).execute()
    return {"success": True, "data": r.data}

# ══════════════════════════════════════════════════════════════
# INVENTORY ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.get("/api/inventory/items")
async def list_items(page: int = 1, page_size: int = 25, search: Optional[str] = None,
    group_id: Optional[str] = None, brand_id: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("items").select("*, item_groups(name), item_categories(name), item_brands(name), units!items_primary_unit_id_fkey(name)").eq("company_id", u["company_id"]).eq("is_active", True)
    if search: q = q.or_(f"name.ilike.%{search}%,item_code.ilike.%{search}%,barcode.ilike.%{search}%")
    if group_id: q = q.eq("group_id", group_id)
    if brand_id: q = q.eq("brand_id", brand_id)
    r = q.order("item_code").execute()
    data = r.data or []
    offset = (page-1)*page_size
    return {"success": True, "data": data[offset:offset+page_size], "total": len(data)}

@app.post("/api/inventory/items")
async def create_item(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["company_id"] = u["company_id"]
    data["created_by"] = u["sub"]
    r = db.table("items").insert(data).execute()
    return {"success": True, "data": r.data}

@app.get("/api/inventory/stock")
async def get_stock(store_room_id: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("stock_ledger").select("item_id, in_qty, out_qty, unit_cost").eq("company_id", u["company_id"])
    if store_room_id: q = q.eq("store_room_id", store_room_id)
    r = q.execute()
    stock = {}
    for row in (r.data or []):
        iid = row["item_id"]
        if iid not in stock: stock[iid] = {"item_id": iid, "quantity": 0, "value": 0}
        stock[iid]["quantity"] += float(row.get("in_qty",0)) - float(row.get("out_qty",0))
    return {"success": True, "data": list(stock.values())}

@app.get("/api/inventory/item-groups")
async def item_groups(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("item_groups").select("*").eq("is_active", True).order("name").execute()
    return {"success": True, "data": r.data}

@app.get("/api/inventory/item-categories")
async def item_categories(group_id: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("item_categories").select("*, item_groups(name)").eq("is_active", True)
    if group_id: q = q.eq("group_id", group_id)
    r = q.order("name").execute()
    return {"success": True, "data": r.data}

@app.get("/api/inventory/item-brands")
async def item_brands(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("item_brands").select("*").eq("is_active", True).order("name").execute()
    return {"success": True, "data": r.data}

@app.get("/api/inventory/units")
async def list_units(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("units").select("*").eq("is_active", True).order("name").execute()
    return {"success": True, "data": r.data}

@app.get("/api/inventory/store-rooms")
async def store_rooms(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("store_rooms").select("*").eq("company_id", u["company_id"]).execute()
    return {"success": True, "data": r.data}

@app.get("/api/inventory/reports/inventory-balance")
async def inv_balance_report(u = Depends(get_current_user)):
    db = get_db()
    items = db.table("items").select("id, item_code, name, selling_price").eq("company_id", u["company_id"]).eq("is_active", True).execute()
    result = []
    for item in (items.data or []):
        stock = db.table("stock_ledger").select("in_qty, out_qty").eq("item_id", item["id"]).execute()
        qty = sum(float(r.get("in_qty",0)) - float(r.get("out_qty",0)) for r in (stock.data or []))
        value = qty * float(item.get("selling_price", 0))
        result.append({"item_code": item["item_code"], "name": item["name"], "quantity": qty, "value": value})
    return {"success": True, "data": result}

# ══════════════════════════════════════════════════════════════
# CUSTOMER ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.get("/api/customer/")
async def list_customers(page: int = 1, page_size: int = 25, search: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("customers").select("*, customer_groups(name)").eq("company_id", u["company_id"]).eq("is_active", True)
    if search: q = q.or_(f"name.ilike.%{search}%,customer_code.ilike.%{search}%,mobile.ilike.%{search}%")
    r = q.order("name").execute()
    data = r.data or []
    offset = (page-1)*page_size
    return {"success": True, "data": data[offset:offset+page_size], "total": len(data)}

@app.post("/api/customer/")
async def create_customer(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["company_id"] = u["company_id"]
    if not data.get("customer_code"):
        data["customer_code"] = f"CUST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    r = db.table("customers").insert(data).execute()
    return {"success": True, "data": r.data}

@app.put("/api/customer/{cid}")
async def update_customer(cid: str, data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    db.table("customers").update(data).eq("id", cid).execute()
    return {"success": True, "message": "Updated"}

@app.get("/api/customer/{cid}/ledger")
async def customer_ledger(cid: str, u = Depends(get_current_user)):
    db = get_db()
    cust = db.table("customers").select("name, opening_balance").eq("id", cid).single().execute()
    invs = db.table("sales_invoices").select("invoice_date, invoice_no, total_amount, paid_amount, due_amount").eq("customer_id", cid).execute()
    rcpts = db.table("money_receipts").select("receipt_date, receipt_no, amount").eq("customer_id", cid).execute()
    balance = float(cust.data.get("opening_balance", 0)) if cust.data else 0
    entries = []
    for inv in (invs.data or []):
        balance += float(inv.get("total_amount",0))
        entries.append({"date": inv["invoice_date"], "ref": inv["invoice_no"], "debit": inv["total_amount"], "credit": 0, "balance": balance, "type": "invoice"})
    for rct in (rcpts.data or []):
        balance -= float(rct.get("amount",0))
        entries.append({"date": rct["receipt_date"], "ref": rct["receipt_no"], "debit": 0, "credit": rct["amount"], "balance": balance, "type": "receipt"})
    entries.sort(key=lambda x: x["date"])
    return {"success": True, "data": {"customer": cust.data, "entries": entries, "closing_balance": balance}}

# ══════════════════════════════════════════════════════════════
# SUPPLIER ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.get("/api/supplier/")
async def list_suppliers(page: int = 1, page_size: int = 25, search: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("suppliers").select("*, supplier_groups(name)").eq("company_id", u["company_id"]).eq("is_active", True)
    if search: q = q.or_(f"name.ilike.%{search}%,supplier_code.ilike.%{search}%")
    r = q.order("name").execute()
    data = r.data or []
    offset = (page-1)*page_size
    return {"success": True, "data": data[offset:offset+page_size], "total": len(data)}

@app.post("/api/supplier/")
async def create_supplier(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["company_id"] = u["company_id"]
    if not data.get("supplier_code"):
        data["supplier_code"] = f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    r = db.table("suppliers").insert(data).execute()
    return {"success": True, "data": r.data}

@app.put("/api/supplier/{sid}")
async def update_supplier(sid: str, data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    db.table("suppliers").update(data).eq("id", sid).execute()
    return {"success": True, "message": "Updated"}

# ══════════════════════════════════════════════════════════════
# PURCHASE ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.get("/api/purchase/requisitions")
async def list_pr(status: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("purchase_requisitions").select("*, departments(name)").eq("company_id", u["company_id"])
    if status: q = q.eq("status", status)
    r = q.order("pr_date", desc=True).execute()
    return {"success": True, "data": r.data}

@app.post("/api/purchase/requisitions")
async def create_pr(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    items = data.pop("items", [])
    data["company_id"] = u["company_id"]
    data["branch_id"] = u.get("branch_id")
    data["pr_no"] = f"PR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["pr_date"] = str(date.today())
    data["status"] = "pending"
    data["created_by"] = u["sub"]
    pr = db.table("purchase_requisitions").insert(data).execute()
    pr_id = pr.data[0]["id"]
    for item in items:
        item["pr_id"] = pr_id
        db.table("purchase_requisition_items").insert(item).execute()
    return {"success": True, "message": "PR created", "pr_no": data["pr_no"]}

@app.get("/api/purchase/orders")
async def list_po(supplier_id: Optional[str] = None, status: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("purchase_orders").select("*, suppliers(name)").eq("company_id", u["company_id"])
    if supplier_id: q = q.eq("supplier_id", supplier_id)
    if status: q = q.eq("status", status)
    r = q.order("po_date", desc=True).execute()
    return {"success": True, "data": r.data}

@app.post("/api/purchase/orders")
async def create_po(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    items = data.pop("items", [])
    data["company_id"] = u["company_id"]
    data["branch_id"] = u.get("branch_id")
    data["po_no"] = f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["po_date"] = str(data.get("po_date", date.today()))
    data["status"] = "open"
    data["created_by"] = u["sub"]
    total = sum(i.get("ordered_qty",0)*i.get("unit_price",0) for i in items)
    data["total_amount"] = total
    po = db.table("purchase_orders").insert(data).execute()
    po_id = po.data[0]["id"]
    for item in items:
        item["po_id"] = po_id
        item.setdefault("total_amount", item.get("ordered_qty",0)*item.get("unit_price",0))
        db.table("purchase_order_items").insert(item).execute()
    return {"success": True, "po_no": data["po_no"], "data": po.data}

@app.get("/api/purchase/purchases")
async def list_purchases(from_date: Optional[str] = None, to_date: Optional[str] = None, supplier_id: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("purchases").select("*, suppliers(name)").eq("company_id", u["company_id"])
    if supplier_id: q = q.eq("supplier_id", supplier_id)
    if from_date: q = q.gte("purchase_date", from_date)
    if to_date: q = q.lte("purchase_date", to_date)
    r = q.order("purchase_date", desc=True).execute()
    return {"success": True, "data": r.data}

@app.post("/api/purchase/purchases")
async def create_purchase(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    items = data.pop("items", [])
    data["company_id"] = u["company_id"]
    data["branch_id"] = u.get("branch_id")
    data["purchase_no"] = f"PUR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["purchase_date"] = str(data.get("purchase_date", date.today()))
    data["status"] = "unpaid"
    data["created_by"] = u["sub"]
    total = sum(i.get("quantity",0)*i.get("unit_cost",0) for i in items)
    data["total_amount"] = total + float(data.get("other_charges",0))
    data["due_amount"] = data["total_amount"]
    pur = db.table("purchases").insert(data).execute()
    pur_id = pur.data[0]["id"]
    for item in items:
        item["purchase_id"] = pur_id
        db.table("purchase_items").insert(item).execute()
        # Update stock
        db.table("stock_ledger").insert({"company_id": u["company_id"], "branch_id": u.get("branch_id"),
            "store_room_id": data.get("store_room_id"), "item_id": item["item_id"],
            "transaction_date": data["purchase_date"], "transaction_type": "purchase",
            "reference_type": "purchase", "reference_id": pur_id, "reference_no": data["purchase_no"],
            "in_qty": item.get("quantity",0), "unit_cost": item.get("unit_cost",0),
            "total_cost": item.get("quantity",0)*item.get("unit_cost",0), "created_by": u["sub"]}).execute()
    return {"success": True, "purchase_no": data["purchase_no"]}

# ══════════════════════════════════════════════════════════════
# SALES ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.get("/api/sales/orders")
async def list_so(page: int = 1, page_size: int = 25, customer_id: Optional[str] = None,
    status: Optional[str] = None, from_date: Optional[str] = None, to_date: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("sales_orders").select("*, customers(name, customer_code)").eq("company_id", u["company_id"])
    if customer_id: q = q.eq("customer_id", customer_id)
    if status: q = q.eq("status", status)
    if from_date: q = q.gte("order_date", from_date)
    if to_date: q = q.lte("order_date", to_date)
    r = q.order("order_date", desc=True).execute()
    data = r.data or []
    offset = (page-1)*page_size
    return {"success": True, "data": data[offset:offset+page_size], "total": len(data)}

@app.post("/api/sales/orders")
async def create_so(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    items = data.pop("items", [])
    data["company_id"] = u["company_id"]
    data["branch_id"] = u.get("branch_id")
    data["order_no"] = f"SO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["order_date"] = str(data.get("order_date", date.today()))
    data["status"] = "pending"
    data["created_by"] = u["sub"]
    total = sum(i.get("quantity",i.get("ordered_qty",0))*i.get("unit_price",0) for i in items)
    data["total_amount"] = total
    so = db.table("sales_orders").insert(data).execute()
    so_id = so.data[0]["id"]
    for item in items:
        item["order_id"] = so_id
        item.setdefault("ordered_qty", item.get("quantity",0))
        item.setdefault("total_amount", item.get("ordered_qty",0)*item.get("unit_price",0))
        db.table("sales_order_items").insert(item).execute()
    return {"success": True, "order_no": data["order_no"], "data": so.data}

@app.get("/api/sales/invoices")
async def list_invoices(page: int = 1, page_size: int = 25, customer_id: Optional[str] = None,
    from_date: Optional[str] = None, to_date: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("sales_invoices").select("*, customers(name, customer_code)").eq("company_id", u["company_id"])
    if customer_id: q = q.eq("customer_id", customer_id)
    if from_date: q = q.gte("invoice_date", from_date)
    if to_date: q = q.lte("invoice_date", to_date)
    r = q.order("invoice_date", desc=True).execute()
    data = r.data or []
    offset = (page-1)*page_size
    return {"success": True, "data": data[offset:offset+page_size], "total": len(data)}

@app.post("/api/sales/invoices")
async def create_invoice(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    items = data.pop("items", [])
    data["company_id"] = u["company_id"]
    data["branch_id"] = u.get("branch_id")
    data["invoice_no"] = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["invoice_date"] = str(data.get("invoice_date", date.today()))
    data["status"] = "unpaid"
    data["created_by"] = u["sub"]
    total = sum(i.get("quantity",0)*i.get("unit_price",0) for i in items)
    total = total - float(data.get("discount_amount",0)) + float(data.get("delivery_charge",0))
    data["total_amount"] = total
    data["due_amount"] = total
    inv = db.table("sales_invoices").insert(data).execute()
    inv_id = inv.data[0]["id"]
    for item in items:
        item["invoice_id"] = inv_id
        item.setdefault("total_amount", item.get("quantity",0)*item.get("unit_price",0))
        db.table("sales_invoice_items").insert(item).execute()
        db.table("stock_ledger").insert({"company_id": u["company_id"], "branch_id": u.get("branch_id"),
            "item_id": item["item_id"], "transaction_date": data["invoice_date"],
            "transaction_type": "sales", "reference_type": "invoice", "reference_id": inv_id,
            "reference_no": data["invoice_no"], "out_qty": item.get("quantity",0),
            "unit_cost": item.get("unit_price",0), "total_cost": item.get("total_amount",0),
            "created_by": u["sub"]}).execute()
    return {"success": True, "invoice_no": data["invoice_no"], "data": inv.data}

@app.post("/api/sales/receipts")
async def create_receipt(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["company_id"] = u["company_id"]
    data["branch_id"] = u.get("branch_id")
    data["receipt_no"] = f"MR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["receipt_date"] = str(data.get("receipt_date", date.today()))
    data["created_by"] = u["sub"]
    inv_id = data.get("invoice_id") or data.get("reference_invoice_id")
    r = db.table("money_receipts").insert(data).execute()
    if inv_id:
        inv = db.table("sales_invoices").select("due_amount, paid_amount").eq("id", inv_id).single().execute()
        if inv.data:
            paid = float(inv.data.get("paid_amount",0)) + float(data.get("amount",0))
            due = max(0, float(inv.data.get("due_amount",0)) - float(data.get("amount",0)))
            status = "paid" if due == 0 else "partial"
            db.table("sales_invoices").update({"paid_amount": paid, "due_amount": due, "status": status}).eq("id", inv_id).execute()
    return {"success": True, "receipt_no": data["receipt_no"], "data": r.data}

# ══════════════════════════════════════════════════════════════
# ACCOUNTS ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.get("/api/accounts/chart-of-accounts")
async def list_coa(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("chart_of_accounts").select("*").eq("company_id", u["company_id"]).eq("is_active", True).order("account_code").execute()
    return {"success": True, "data": r.data}

@app.post("/api/accounts/chart-of-accounts")
async def create_coa(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["company_id"] = u["company_id"]
    r = db.table("chart_of_accounts").insert(data).execute()
    return {"success": True, "data": r.data}

@app.get("/api/accounts/vouchers")
async def list_vouchers(voucher_type: Optional[str] = None, from_date: Optional[str] = None, to_date: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("vouchers").select("*").eq("company_id", u["company_id"])
    if voucher_type: q = q.eq("voucher_type", voucher_type)
    if from_date: q = q.gte("voucher_date", from_date)
    if to_date: q = q.lte("voucher_date", to_date)
    r = q.order("voucher_date", desc=True).execute()
    return {"success": True, "data": r.data}

@app.post("/api/accounts/vouchers")
async def create_voucher(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    lines = data.pop("lines", [])
    total_dr = sum(float(l.get("debit_amount",0)) for l in lines)
    total_cr = sum(float(l.get("credit_amount",0)) for l in lines)
    if abs(total_dr - total_cr) > 0.01: raise HTTPException(400, "Debit and credit must balance")
    data["company_id"] = u["company_id"]
    data["branch_id"] = u.get("branch_id")
    data["voucher_no"] = f"V-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["voucher_date"] = str(data.get("voucher_date", date.today()))
    data["total_debit"] = total_dr
    data["total_credit"] = total_cr
    data["status"] = "posted"
    data["created_by"] = u["sub"]
    v = db.table("vouchers").insert(data).execute()
    vid = v.data[0]["id"]
    for line in lines:
        line["voucher_id"] = vid
        db.table("voucher_lines").insert(line).execute()
    return {"success": True, "voucher_no": data["voucher_no"]}

@app.get("/api/accounts/reports/trial-balance")
async def trial_balance(u = Depends(get_current_user)):
    db = get_db()
    accs = db.table("chart_of_accounts").select("id, account_code, account_name, account_type, balance_type, opening_balance").eq("company_id", u["company_id"]).eq("is_leaf", True).execute()
    result = []
    for acc in (accs.data or []):
        lines = db.table("voucher_lines").select("debit_amount, credit_amount").eq("account_id", acc["id"]).execute()
        dr = sum(float(l.get("debit_amount",0)) for l in (lines.data or []))
        cr = sum(float(l.get("credit_amount",0)) for l in (lines.data or []))
        ob = float(acc.get("opening_balance", 0))
        balance = ob + dr - cr if acc.get("balance_type") == "debit" else ob + cr - dr
        result.append({**acc, "total_debit": dr, "total_credit": cr, "balance": balance})
    return {"success": True, "data": result}

# ══════════════════════════════════════════════════════════════
# SERVICE ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.get("/api/service/job-cards")
async def list_job_cards(status: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("job_cards").select("*, customers(name, phone), service_types(name)").eq("company_id", u["company_id"])
    if status: q = q.eq("status", status)
    r = q.order("job_date", desc=True).execute()
    return {"success": True, "data": r.data}

@app.post("/api/service/job-cards")
async def create_job_card(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["company_id"] = u["company_id"]
    data["branch_id"] = u.get("branch_id")
    data["job_card_no"] = f"JC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["job_date"] = str(data.get("job_date", date.today()))
    data["status"] = "received"
    data["created_by"] = u["sub"]
    r = db.table("job_cards").insert(data).execute()
    return {"success": True, "job_card_no": data["job_card_no"], "data": r.data}

@app.get("/api/service/setup/types")
async def service_types(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("service_types").select("*").eq("company_id", u["company_id"]).execute()
    return {"success": True, "data": r.data}

# ══════════════════════════════════════════════════════════════
# CRM ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.get("/api/crm/leads")
async def list_leads(status: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("leads").select("*").eq("company_id", u["company_id"])
    if status: q = q.eq("status", status)
    r = q.order("created_at", desc=True).execute()
    return {"success": True, "data": r.data}

@app.post("/api/crm/leads")
async def create_lead(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["company_id"] = u["company_id"]
    data["lead_no"] = f"LEAD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["status"] = "new"
    r = db.table("leads").insert(data).execute()
    return {"success": True, "data": r.data}

@app.get("/api/crm/dashboard")
async def crm_dashboard(u = Depends(get_current_user)):
    db = get_db()
    cid = u["company_id"]
    total = db.table("leads").select("id", count="exact").eq("company_id", cid).execute()
    won = db.table("leads").select("id", count="exact").eq("company_id", cid).eq("status", "converted").execute()
    return {"success": True, "data": {"total_leads": total.count or 0, "won": won.count or 0}}

# ══════════════════════════════════════════════════════════════
# CREDIT SALES ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.get("/api/credit-sales/")
async def list_credit_sales(status: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("credit_sales").select("*, customers(name, phone)").eq("company_id", u["company_id"])
    if status: q = q.eq("status", status)
    r = q.order("sale_date", desc=True).execute()
    return {"success": True, "data": r.data}

@app.post("/api/credit-sales/")
async def create_credit_sale(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    from dateutil.relativedelta import relativedelta
    first_date = datetime.strptime(str(data["first_installment_date"]), "%Y-%m-%d").date()
    financed = float(data["total_amount"]) - float(data.get("down_payment",0))
    n = int(data["total_installments"])
    rate = float(data.get("interest_rate",0))
    interest = financed * (rate/100) * (n/12)
    installment_amt = (financed + interest) / n if n > 0 else 0
    data["company_id"] = u["company_id"]
    data["branch_id"] = u.get("branch_id")
    data["credit_sale_no"] = f"CS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["sale_date"] = str(data.get("sale_date", date.today()))
    data["first_installment_date"] = str(first_date)
    data["financed_amount"] = financed
    data["installment_amount"] = installment_amt
    data["status"] = "active"
    data["created_by"] = u["sub"]
    cs = db.table("credit_sales").insert(data).execute()
    cs_id = cs.data[0]["id"]
    for i in range(n):
        due = first_date + relativedelta(months=i)
        db.table("installment_schedules").insert({"credit_sale_id": cs_id, "installment_no": i+1,
            "due_date": str(due), "installment_amount": installment_amt,
            "principal_amount": financed/n, "interest_amount": interest/n if n else 0,
            "status": "pending"}).execute()
    return {"success": True, "credit_sale_no": data["credit_sale_no"], "installment_amount": installment_amt}

@app.get("/api/credit-sales/{csid}/schedule")
async def credit_schedule(csid: str, u = Depends(get_current_user)):
    db = get_db()
    r = db.table("installment_schedules").select("*").eq("credit_sale_id", csid).order("installment_no").execute()
    return {"success": True, "data": r.data}

# ══════════════════════════════════════════════════════════════
# LC ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.get("/api/lc/proforma-invoices")
async def list_pi(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("proforma_invoices").select("*, suppliers(name)").eq("company_id", u["company_id"]).execute()
    return {"success": True, "data": r.data}

@app.post("/api/lc/proforma-invoices")
async def create_pi(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["company_id"] = u["company_id"]
    data["pi_no"] = f"PI-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["pi_date"] = str(data.get("pi_date", date.today()))
    data["status"] = "draft"
    data["created_by"] = u["sub"]
    r = db.table("proforma_invoices").insert(data).execute()
    return {"success": True, "pi_no": data["pi_no"]}

@app.get("/api/lc/")
async def list_lc(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("letters_of_credit").select("*, suppliers(name), banks(name)").eq("company_id", u["company_id"]).execute()
    return {"success": True, "data": r.data}

@app.post("/api/lc/")
async def create_lc(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["company_id"] = u["company_id"]
    data["lc_no"] = f"LC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["lc_date"] = str(data.get("lc_date", date.today()))
    data["status"] = "opened"
    data["created_by"] = u["sub"]
    r = db.table("letters_of_credit").insert(data).execute()
    return {"success": True, "lc_no": data["lc_no"]}

# ══════════════════════════════════════════════════════════════
# PRODUCTION ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.get("/api/production/bom")
async def list_bom(u = Depends(get_current_user)):
    db = get_db()
    r = db.table("bom_headers").select("*, items!bom_headers_finished_item_id_fkey(item_code, name)").eq("company_id", u["company_id"]).execute()
    return {"success": True, "data": r.data}

@app.post("/api/production/bom")
async def create_bom(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    items = data.pop("items", [])
    data["company_id"] = u["company_id"]
    data["bom_no"] = f"BOM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["is_current"] = True
    data["created_by"] = u["sub"]
    bom = db.table("bom_headers").insert(data).execute()
    bom_id = bom.data[0]["id"]
    for item in items:
        item["bom_id"] = bom_id
        db.table("bom_items").insert(item).execute()
    return {"success": True, "bom_no": data["bom_no"]}

@app.get("/api/production/orders")
async def list_prod_orders(status: Optional[str] = None, u = Depends(get_current_user)):
    db = get_db()
    q = db.table("production_orders").select("*, items!production_orders_finished_item_id_fkey(item_code, name)").eq("company_id", u["company_id"])
    if status: q = q.eq("status", status)
    r = q.order("order_date", desc=True).execute()
    return {"success": True, "data": r.data}

@app.post("/api/production/orders")
async def create_prod_order(data: dict = Body(...), u = Depends(get_current_user)):
    db = get_db()
    data["company_id"] = u["company_id"]
    data["branch_id"] = u.get("branch_id")
    data["order_no"] = f"PRD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data["order_date"] = str(data.get("order_date", date.today()))
    data["status"] = "planned"
    data["created_by"] = u["sub"]
    r = db.table("production_orders").insert(data).execute()
    return {"success": True, "order_no": data["order_no"]}

# ══════════════════════════════════════════════════════════════
# ERP OVERVIEW / DASHBOARD
# ══════════════════════════════════════════════════════════════
@app.get("/api/erp/dashboard")
async def erp_dashboard(u = Depends(get_current_user)):
    db = get_db()
    cid = u["company_id"]
    td = str(date.today())
    today_sales = db.table("sales_invoices").select("total_amount").eq("company_id", cid).eq("invoice_date", td).execute()
    total_today = sum(float(r.get("total_amount",0)) for r in (today_sales.data or []))
    emp_count = db.table("employees").select("id", count="exact").eq("company_id", cid).eq("employee_status", "active").execute()
    outstanding = db.table("sales_invoices").select("due_amount").eq("company_id", cid).neq("status", "paid").execute()
    total_due = sum(float(r.get("due_amount",0)) for r in (outstanding.data or []))
    pending_so = db.table("sales_orders").select("id", count="exact").eq("company_id", cid).eq("status", "pending").execute()
    pending_po = db.table("purchase_orders").select("id", count="exact").eq("company_id", cid).eq("status", "open").execute()
    pending_leave = db.table("leave_applications").select("id", count="exact").eq("status", "pending").execute()
    return {"success": True, "data": {
        "today_sales": total_today, "total_employees": emp_count.count or 0,
        "outstanding_dues": total_due, "pending_sales_orders": pending_so.count or 0,
        "pending_purchase_orders": pending_po.count or 0,
        "pending_leave_applications": pending_leave.count or 0,
        "as_of": datetime.now().isoformat()
    }}

@app.get("/api/erp/pending-overview")
async def pending_overview(u = Depends(get_current_user)):
    db = get_db()
    cid = u["company_id"]
    return {"success": True, "data": {
        "pending_requisitions": db.table("purchase_requisitions").select("id", count="exact").eq("company_id", cid).eq("status", "pending").execute().count or 0,
        "open_pos": db.table("purchase_orders").select("id", count="exact").eq("company_id", cid).eq("status", "open").execute().count or 0,
        "unpaid_invoices": db.table("sales_invoices").select("id", count="exact").eq("company_id", cid).eq("status", "unpaid").execute().count or 0,
        "pending_leaves": db.table("leave_applications").select("id", count="exact").eq("status", "pending").execute().count or 0,
    }}

# ── RUN ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("saforaerp_backend_main:app", host="0.0.0.0", port=8000, reload=True)
