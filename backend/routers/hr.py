"""SaforaERP - HR Router - All HR endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID
import sys
sys.path.insert(0, "/home/claude/saforaerp/backend")
from routers.auth import get_current_user

router = APIRouter()

# ─── Helper ──────────────────────────────────────────────
def db():
    from database import get_db_admin
    return get_db_admin()

def paginate(table, query_builder, page=1, page_size=25):
    offset = (page - 1) * page_size
    count_resp = query_builder.execute()
    total = len(count_resp.data or [])
    return count_resp.data[offset:offset+page_size], total

# ─── EMPLOYEE PROFILE ─────────────────────────────────────

class EmployeeCreate(BaseModel):
    employee_code: str
    first_name: str
    last_name: Optional[str] = None
    full_name_bn: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: str = "Bangladeshi"
    religion: Optional[str] = None
    blood_group: Optional[str] = None
    nid_number: Optional[str] = None
    passport_number: Optional[str] = None
    tin_number: Optional[str] = None
    personal_email: Optional[str] = None
    official_email: Optional[str] = None
    mobile_number: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    perm_address: Optional[str] = None
    perm_district_id: Optional[str] = None
    pres_address: Optional[str] = None
    pres_district_id: Optional[str] = None
    department_id: Optional[str] = None
    section_id: Optional[str] = None
    designation_id: Optional[str] = None
    grade_id: Optional[str] = None
    nature_id: Optional[str] = None
    reporting_to: Optional[str] = None
    joining_date: Optional[date] = None
    confirmation_date: Optional[date] = None
    bank_account_number: Optional[str] = None
    bank_account_name: Optional[str] = None
    bank_id: Optional[str] = None
    branch_id: Optional[str] = None
    remarks: Optional[str] = None

@router.get("/employees")
async def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    search: Optional[str] = None,
    department_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    d = db()
    q = d.table("employees").select(
        "*, departments(name), designations(name), employee_grades(name), sections(name)"
    ).eq("company_id", current_user.get("company_id"))
    if search:
        q = q.ilike("full_name", f"%{search}%")
    if department_id:
        q = q.eq("department_id", department_id)
    if status:
        q = q.eq("employee_status", status)
    q = q.order("employee_code")
    result = q.execute()
    data = result.data or []
    total = len(data)
    offset = (page-1)*page_size
    return {"success": True, "data": data[offset:offset+page_size], "total": total, "page": page, "page_size": page_size}

@router.get("/employees/{employee_id}")
async def get_employee(employee_id: str, current_user: dict = Depends(get_current_user)):
    d = db()
    result = d.table("employees").select("*, departments(*), designations(*), employee_grades(*), sections(*)").eq("id", employee_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Employee not found")
    emp = result.data
    educations = d.table("employee_educations").select("*").eq("employee_id", employee_id).execute()
    experiences = d.table("employee_experiences").select("*").eq("employee_id", employee_id).execute()
    docs = d.table("employee_documents").select("*").eq("employee_id", employee_id).execute()
    emp["educations"] = educations.data or []
    emp["experiences"] = experiences.data or []
    emp["documents"] = docs.data or []
    return {"success": True, "data": emp}

@router.post("/employees")
async def create_employee(emp: EmployeeCreate, current_user: dict = Depends(get_current_user)):
    d = db()
    data = emp.dict(exclude_none=True)
    data["company_id"] = current_user.get("company_id")
    data["created_by"] = current_user.get("sub")
    result = d.table("employees").insert(data).execute()
    return {"success": True, "message": "Employee created", "data": result.data}

@router.put("/employees/{employee_id}")
async def update_employee(employee_id: str, emp: EmployeeCreate, current_user: dict = Depends(get_current_user)):
    d = db()
    data = emp.dict(exclude_none=True)
    data["updated_at"] = datetime.utcnow().isoformat()
    result = d.table("employees").update(data).eq("id", employee_id).execute()
    return {"success": True, "message": "Employee updated", "data": result.data}

@router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["administrator","super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    db().table("employees").update({"is_active": False}).eq("id", employee_id).execute()
    return {"success": True, "message": "Employee deactivated"}

# ─── DEPARTMENTS ──────────────────────────────────────────

@router.get("/departments")
async def list_departments(current_user: dict = Depends(get_current_user)):
    result = db().table("departments").select("*").eq("company_id", current_user.get("company_id")).eq("is_active", True).order("name").execute()
    return {"success": True, "data": result.data}

@router.post("/departments")
async def create_department(
    code: str = Body(...), name: str = Body(...), name_bn: Optional[str] = Body(None),
    parent_id: Optional[str] = Body(None), current_user: dict = Depends(get_current_user)
):
    result = db().table("departments").insert({
        "company_id": current_user.get("company_id"), "code": code, "name": name,
        "name_bn": name_bn, "parent_id": parent_id
    }).execute()
    return {"success": True, "data": result.data}

@router.put("/departments/{dept_id}")
async def update_department(dept_id: str, code: str = Body(None), name: str = Body(None), name_bn: str = Body(None), current_user: dict = Depends(get_current_user)):
    data = {k: v for k,v in {"code":code,"name":name,"name_bn":name_bn}.items() if v is not None}
    db().table("departments").update(data).eq("id", dept_id).execute()
    return {"success": True, "message": "Updated"}

# ─── DESIGNATIONS ─────────────────────────────────────────

@router.get("/designations")
async def list_designations(current_user: dict = Depends(get_current_user)):
    result = db().table("designations").select("*").eq("company_id", current_user.get("company_id")).eq("is_active", True).order("rank_order").execute()
    return {"success": True, "data": result.data}

@router.post("/designations")
async def create_designation(code: str = Body(...), name: str = Body(...), rank_order: int = Body(0), current_user: dict = Depends(get_current_user)):
    result = db().table("designations").insert({"company_id": current_user.get("company_id"), "code": code, "name": name, "rank_order": rank_order}).execute()
    return {"success": True, "data": result.data}

# ─── ATTENDANCE ────────────────────────────────────────────

class AttendanceEntry(BaseModel):
    employee_id: str
    attendance_date: date
    in_time: Optional[datetime] = None
    out_time: Optional[datetime] = None
    status: str = "present"
    remarks: Optional[str] = None

@router.get("/attendance")
async def get_attendance(
    employee_id: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    d = db()
    q = d.table("attendance_records").select("*, employees(employee_code, first_name, last_name)")
    if employee_id:
        q = q.eq("employee_id", employee_id)
    if from_date:
        q = q.gte("attendance_date", str(from_date))
    if to_date:
        q = q.lte("attendance_date", str(to_date))
    if month and year:
        from_d = f"{year}-{month:02d}-01"
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        to_d = f"{year}-{month:02d}-{last_day}"
        q = q.gte("attendance_date", from_d).lte("attendance_date", to_d)
    result = q.order("attendance_date", desc=True).execute()
    return {"success": True, "data": result.data}

@router.post("/attendance")
async def save_attendance(att: AttendanceEntry, current_user: dict = Depends(get_current_user)):
    d = db()
    data = att.dict(exclude_none=True)
    data["attendance_date"] = str(data["attendance_date"])
    if data.get("in_time"):
        data["in_time"] = data["in_time"].isoformat()
    if data.get("out_time"):
        data["out_time"] = data["out_time"].isoformat()
    result = d.table("attendance_records").upsert(data, on_conflict="employee_id,attendance_date").execute()
    return {"success": True, "data": result.data}

# ─── LEAVE ────────────────────────────────────────────────

@router.get("/leave/types")
async def get_leave_types(current_user: dict = Depends(get_current_user)):
    result = db().table("leave_types").select("*, leave_categories(name)").eq("company_id", current_user.get("company_id")).eq("is_active", True).execute()
    return {"success": True, "data": result.data}

@router.get("/leave/applications")
async def get_leave_applications(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    d = db()
    q = d.table("leave_applications").select("*, employees(employee_code, first_name, last_name), leave_types(name)")
    if status:
        q = q.eq("status", status)
    if employee_id:
        q = q.eq("employee_id", employee_id)
    result = q.order("applied_at", desc=True).execute()
    return {"success": True, "data": result.data}

@router.post("/leave/apply")
async def apply_leave(
    employee_id: str = Body(...),
    leave_type_id: str = Body(...),
    from_date: date = Body(...),
    to_date: date = Body(...),
    reason: str = Body(...),
    current_user: dict = Depends(get_current_user)
):
    from datetime import timedelta
    total_days = (to_date - from_date).days + 1
    app_no = f"LA-{datetime.now().strftime(\'%Y%m%d%H%M%S\')}"
    result = db().table("leave_applications").insert({
        "application_no": app_no, "employee_id": employee_id,
        "leave_type_id": leave_type_id, "from_date": str(from_date),
        "to_date": str(to_date), "total_days": total_days, "reason": reason, "status": "pending"
    }).execute()
    return {"success": True, "message": "Leave applied", "data": result.data}

@router.put("/leave/applications/{app_id}/approve")
async def approve_leave(app_id: str, current_user: dict = Depends(get_current_user)):
    db().table("leave_applications").update({
        "status": "approved", "approved_by": current_user.get("sub"),
        "approved_at": datetime.utcnow().isoformat()
    }).eq("id", app_id).execute()
    return {"success": True, "message": "Leave approved"}

@router.put("/leave/applications/{app_id}/reject")
async def reject_leave(app_id: str, rejection_reason: str = Body(...), current_user: dict = Depends(get_current_user)):
    db().table("leave_applications").update({
        "status": "rejected", "rejection_reason": rejection_reason
    }).eq("id", app_id).execute()
    return {"success": True, "message": "Leave rejected"}

# ─── PAYROLL ──────────────────────────────────────────────

@router.get("/payroll/salary-sheets")
async def get_salary_sheets(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    q = db().table("salary_sheets").select("*").eq("company_id", current_user.get("company_id"))
    if year:
        q = q.eq("year", year)
    if month:
        q = q.eq("month", month)
    result = q.order("year", desc=True).order("month", desc=True).execute()
    return {"success": True, "data": result.data}

@router.post("/payroll/prepare")
async def prepare_salary(
    month: int = Body(...),
    year: int = Body(...),
    branch_id: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    """Prepare salary sheet for a month"""
    d = db()
    company_id = current_user.get("company_id")
    
    # Get all active employees
    emps = d.table("employees").select(
        "*, employee_grades(id)"
    ).eq("company_id", company_id).eq("employee_status", "active").execute()
    
    # Create salary sheet header
    sheet = d.table("salary_sheets").upsert({
        "company_id": company_id, "branch_id": branch_id,
        "month": month, "year": year, "status": "draft",
        "processed_by": current_user.get("sub"),
        "processed_at": datetime.utcnow().isoformat()
    }, on_conflict="company_id,branch_id,month,year").execute()
    
    sheet_id = sheet.data[0]["id"] if sheet.data else None
    
    # Get salary grades
    grades = d.table("salary_grades").select("*").eq("is_active", True).execute()
    grade_map = {g["grade_id"]: g for g in (grades.data or [])}
    
    total_net = 0
    for emp in (emps.data or []):
        grade = grade_map.get(emp.get("grade_id"), {})
        basic = float(grade.get("basic_salary", 0))
        house_rent = basic * 0.5
        medical = basic * 0.1
        transport = basic * 0.1
        gross = basic + house_rent + medical + transport
        pf = basic * 0.1
        net = gross - pf
        total_net += net
        
        d.table("salary_details").upsert({
            "salary_sheet_id": sheet_id,
            "employee_id": emp["id"],
            "basic_salary": basic,
            "house_rent": house_rent,
            "medical_allowance": medical,
            "transport_allowance": transport,
            "gross_salary": gross,
            "pf_deduction": pf,
            "net_pay": net,
            "present_days": 26,
        }, on_conflict="salary_sheet_id,employee_id").execute()
    
    d.table("salary_sheets").update({
        "total_net_pay": total_net, "status": "processed"
    }).eq("id", sheet_id).execute()
    
    return {"success": True, "message": f"Salary prepared for {month}/{year}", "total_employees": len(emps.data or []), "total_net_pay": total_net}

@router.get("/payroll/salary-details/{sheet_id}")
async def get_salary_details(sheet_id: str, current_user: dict = Depends(get_current_user)):
    result = db().table("salary_details").select("*, employees(employee_code, first_name, last_name, designations(name))").eq("salary_sheet_id", sheet_id).execute()
    return {"success": True, "data": result.data}

# ─── SHIFTS ──────────────────────────────────────────────

@router.get("/shifts")
async def list_shifts(current_user: dict = Depends(get_current_user)):
    result = db().table("shifts").select("*").eq("company_id", current_user.get("company_id")).execute()
    return {"success": True, "data": result.data}

@router.post("/shifts")
async def create_shift(
    code: str = Body(...), name: str = Body(...),
    start_time: str = Body(...), end_time: str = Body(...),
    late_tolerance_minutes: int = Body(0),
    current_user: dict = Depends(get_current_user)
):
    result = db().table("shifts").insert({
        "company_id": current_user.get("company_id"),
        "code": code, "name": name,
        "start_time": start_time, "end_time": end_time,
        "late_tolerance_minutes": late_tolerance_minutes
    }).execute()
    return {"success": True, "data": result.data}

# ─── SETUP LOOKUPS ────────────────────────────────────────

@router.get("/grades")
async def list_grades(current_user: dict = Depends(get_current_user)):
    return {"success": True, "data": db().table("employee_grades").select("*").eq("company_id", current_user.get("company_id")).execute().data}

@router.get("/sections")
async def list_sections(department_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    q = db().table("sections").select("*, departments(name)")
    if department_id:
        q = q.eq("department_id", department_id)
    return {"success": True, "data": q.execute().data}

@router.get("/leave/holidays")
async def list_holidays(year: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    q = db().table("holidays").select("*").eq("company_id", current_user.get("company_id"))
    if year:
        q = q.gte("holiday_date", f"{year}-01-01").lte("holiday_date", f"{year}-12-31")
    return {"success": True, "data": q.execute().data}

@router.post("/leave/holidays")
async def create_holiday(
    holiday_date: date = Body(...), name: str = Body(...),
    holiday_type: str = Body("public"),
    current_user: dict = Depends(get_current_user)
):
    result = db().table("holidays").insert({
        "company_id": current_user.get("company_id"),
        "holiday_date": str(holiday_date), "name": name, "holiday_type": holiday_type
    }).execute()
    return {"success": True, "data": result.data}

# ─── LOANS ───────────────────────────────────────────────

@router.post("/loans/apply")
async def apply_loan(
    employee_id: str = Body(...),
    loan_type_id: str = Body(...),
    applied_amount: float = Body(...),
    total_installments: int = Body(...),
    remarks: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    loan_no = f"LN-{datetime.now().strftime(\'%Y%m%d%H%M%S\')}"
    result = db().table("employee_loans").insert({
        "loan_no": loan_no, "employee_id": employee_id,
        "loan_type_id": loan_type_id, "applied_amount": applied_amount,
        "total_installments": total_installments,
        "applied_date": str(date.today()),
        "status": "pending", "remarks": remarks
    }).execute()
    return {"success": True, "message": "Loan application submitted", "data": result.data}

@router.get("/loans")
async def list_loans(employee_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    q = db().table("employee_loans").select("*, employees(employee_code,first_name,last_name), loan_types(name)")
    if employee_id:
        q = q.eq("employee_id", employee_id)
    return {"success": True, "data": q.order("applied_date", desc=True).execute().data}

# ─── REPORTS ─────────────────────────────────────────────

@router.get("/reports/employee-list")
async def employee_list_report(
    department_id: Optional[str] = None,
    status: str = "active",
    current_user: dict = Depends(get_current_user)
):
    q = db().table("employees").select(
        "employee_code, first_name, last_name, mobile_number, official_email, joining_date, employee_status, departments(name), designations(name), employee_grades(name)"
    ).eq("company_id", current_user.get("company_id")).eq("is_active", True)
    if department_id:
        q = q.eq("department_id", department_id)
    if status:
        q = q.eq("employee_status", status)
    result = q.order("employee_code").execute()
    return {"success": True, "data": result.data, "total": len(result.data or [])}

@router.get("/reports/attendance-summary")
async def attendance_summary_report(
    month: int, year: int,
    department_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    from_d = f"{year}-{month:02d}-01"
    to_d = f"{year}-{month:02d}-{last_day}"
    
    att = db().table("attendance_records").select(
        "employee_id, status, employees(employee_code, first_name, last_name, department_id)"
    ).gte("attendance_date", from_d).lte("attendance_date", to_d).execute()
    
    summary = {}
    for r in (att.data or []):
        eid = r["employee_id"]
        if eid not in summary:
            summary[eid] = {"employee": r.get("employees", {}), "present": 0, "absent": 0, "late": 0, "leave": 0, "total": 0}
        summary[eid]["total"] += 1
        s = r.get("status","")
        if s == "present": summary[eid]["present"] += 1
        elif s == "absent": summary[eid]["absent"] += 1
        elif s == "late": summary[eid]["late"] += 1
        elif s == "on_leave": summary[eid]["leave"] += 1
    
    return {"success": True, "data": list(summary.values()), "month": month, "year": year}
