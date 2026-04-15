-- ============================================================
-- SaforaERP - Complete Supabase PostgreSQL Database
-- Run this in: Supabase Dashboard → SQL Editor
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. CORE / SECURITY
-- ============================================================
CREATE TABLE IF NOT EXISTS group_companies (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL,
  name VARCHAR(200) NOT NULL,
  name_bn VARCHAR(200),
  address TEXT, phone VARCHAR(50), email VARCHAR(100),
  logo_url TEXT, is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS companies (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  group_company_id UUID REFERENCES group_companies(id),
  code VARCHAR(20) UNIQUE NOT NULL,
  name VARCHAR(200) NOT NULL,
  name_bn VARCHAR(200),
  trade_license VARCHAR(100), tin VARCHAR(50), bin VARCHAR(50),
  address TEXT, city VARCHAR(100), phone VARCHAR(50), email VARCHAR(100),
  logo_url TEXT, currency_code VARCHAR(10) DEFAULT 'BDT',
  fiscal_year_start VARCHAR(5) DEFAULT '07-01',
  is_active BOOLEAN DEFAULT true, created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS branches (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id) NOT NULL,
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(200) NOT NULL,
  name_bn VARCHAR(200), address TEXT, city VARCHAR(100),
  phone VARCHAR(50), email VARCHAR(100),
  is_head_office BOOLEAN DEFAULT false,
  is_active BOOLEAN DEFAULT true, created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_groups (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  role_level VARCHAR(30) DEFAULT 'general', is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID PRIMARY KEY,
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  user_group_id UUID REFERENCES user_groups(id),
  username VARCHAR(50) UNIQUE NOT NULL,
  full_name VARCHAR(200) NOT NULL,
  email VARCHAR(200), phone VARCHAR(50), avatar_url TEXT,
  role VARCHAR(30) DEFAULT 'general',
  is_active BOOLEAN DEFAULT true, last_login TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_login_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES user_profiles(id),
  login_at TIMESTAMPTZ DEFAULT NOW(), logout_at TIMESTAMPTZ,
  ip_address VARCHAR(50), user_agent TEXT, status VARCHAR(20) DEFAULT 'success'
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES user_profiles(id),
  module VARCHAR(100), action VARCHAR(50), table_name VARCHAR(100),
  record_id UUID, old_values JSONB, new_values JSONB,
  ip_address VARCHAR(50), created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS module_permissions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_group_id UUID REFERENCES user_groups(id),
  module_id VARCHAR(50) NOT NULL,
  can_view BOOLEAN DEFAULT false, can_create BOOLEAN DEFAULT false,
  can_edit BOOLEAN DEFAULT false, can_delete BOOLEAN DEFAULT false,
  can_print BOOLEAN DEFAULT false, can_export BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS menu_permissions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_group_id UUID REFERENCES user_groups(id),
  menu_id VARCHAR(100) NOT NULL, is_allowed BOOLEAN DEFAULT false
);

-- ============================================================
-- 2. GEOGRAPHY
-- ============================================================
CREATE TABLE IF NOT EXISTS countries (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(5) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  name_bn VARCHAR(100), currency_code VARCHAR(10), phone_code VARCHAR(10),
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS divisions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  country_id UUID REFERENCES countries(id),
  code VARCHAR(10) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  name_bn VARCHAR(100), is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS districts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  division_id UUID REFERENCES divisions(id),
  code VARCHAR(10) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  name_bn VARCHAR(100), is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS thanas (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  district_id UUID REFERENCES districts(id),
  code VARCHAR(10) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  name_bn VARCHAR(100), is_active BOOLEAN DEFAULT true
);

-- ============================================================
-- 3. SYSTEM CONFIG
-- ============================================================
CREATE TABLE IF NOT EXISTS currencies (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(10) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  symbol VARCHAR(10), exchange_rate DECIMAL(15,6) DEFAULT 1,
  is_base BOOLEAN DEFAULT false, is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS vat_groups (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  rate DECIMAL(5,2) DEFAULT 0, is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS banks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(200) NOT NULL,
  swift_code VARCHAR(20), is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS bank_branches (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  bank_id UUID REFERENCES banks(id),
  code VARCHAR(20), name VARCHAR(200) NOT NULL,
  routing_number VARCHAR(30), address TEXT, is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS payment_methods (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS payment_terms (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  days INTEGER DEFAULT 0, is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS shipping_methods (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS colors (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(50) NOT NULL,
  hex_code VARCHAR(10), is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS sizes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(50) NOT NULL,
  sort_order INTEGER DEFAULT 0, is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS system_parameters (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  param_key VARCHAR(100) NOT NULL, param_value TEXT,
  param_type VARCHAR(30), description TEXT,
  UNIQUE(company_id, param_key)
);

-- ============================================================
-- 4. FISCAL YEAR
-- ============================================================
CREATE TABLE IF NOT EXISTS fiscal_years (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(100) NOT NULL,
  start_date DATE NOT NULL, end_date DATE NOT NULL,
  is_current BOOLEAN DEFAULT false, is_closed BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS accounting_periods (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  fiscal_year_id UUID REFERENCES fiscal_years(id),
  period_number INTEGER NOT NULL, name VARCHAR(50) NOT NULL,
  start_date DATE NOT NULL, end_date DATE NOT NULL,
  is_current BOOLEAN DEFAULT false, is_closed BOOLEAN DEFAULT false
);

-- ============================================================
-- 5. HR MODULE
-- ============================================================
CREATE TABLE IF NOT EXISTS departments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(200) NOT NULL,
  name_bn VARCHAR(200), parent_id UUID REFERENCES departments(id),
  is_active BOOLEAN DEFAULT true, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS sections (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  department_id UUID REFERENCES departments(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(200) NOT NULL,
  name_bn VARCHAR(200), is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS designations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(200) NOT NULL,
  name_bn VARCHAR(200), rank_order INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS employee_grades (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(100) NOT NULL,
  min_salary DECIMAL(15,2) DEFAULT 0, max_salary DECIMAL(15,2) DEFAULT 0,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS separation_types (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) NOT NULL, name VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS promotion_types (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) NOT NULL, name VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS employees (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  employee_code VARCHAR(30) UNIQUE NOT NULL,
  first_name VARCHAR(100) NOT NULL, last_name VARCHAR(100),
  full_name VARCHAR(200) GENERATED ALWAYS AS (first_name || ' ' || COALESCE(last_name,'')) STORED,
  full_name_bn VARCHAR(200), father_name VARCHAR(200), mother_name VARCHAR(200),
  date_of_birth DATE, gender VARCHAR(20), marital_status VARCHAR(30),
  nationality VARCHAR(50) DEFAULT 'Bangladeshi', religion VARCHAR(50),
  blood_group VARCHAR(10), nid_number VARCHAR(30), passport_number VARCHAR(30),
  tin_number VARCHAR(30), personal_email VARCHAR(100), official_email VARCHAR(100),
  mobile_number VARCHAR(20), emergency_contact_name VARCHAR(200),
  emergency_contact_phone VARCHAR(20),
  perm_address TEXT, perm_district_id UUID REFERENCES districts(id),
  pres_address TEXT, pres_district_id UUID REFERENCES districts(id),
  department_id UUID REFERENCES departments(id),
  section_id UUID REFERENCES sections(id),
  designation_id UUID REFERENCES designations(id),
  grade_id UUID REFERENCES employee_grades(id),
  reporting_to UUID REFERENCES employees(id),
  joining_date DATE, confirmation_date DATE, separation_date DATE,
  employee_status VARCHAR(30) DEFAULT 'active',
  separation_type_id UUID REFERENCES separation_types(id),
  photo_url TEXT, bank_id UUID REFERENCES banks(id),
  bank_account_number VARCHAR(50), bank_account_name VARCHAR(200),
  remarks TEXT, is_active BOOLEAN DEFAULT true,
  created_by UUID, created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS employee_educations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
  degree VARCHAR(100), major VARCHAR(100), institution VARCHAR(200),
  passing_year INTEGER, result VARCHAR(50)
);
CREATE TABLE IF NOT EXISTS employee_experiences (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
  company_name VARCHAR(200), designation VARCHAR(100),
  from_date DATE, to_date DATE, responsibilities TEXT
);
CREATE TABLE IF NOT EXISTS employee_documents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
  document_type VARCHAR(100), document_name VARCHAR(200),
  file_url TEXT, issue_date DATE, expiry_date DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- SHIFTS & ATTENDANCE
CREATE TABLE IF NOT EXISTS shifts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(100) NOT NULL,
  start_time TIME NOT NULL, end_time TIME NOT NULL,
  late_tolerance_minutes INTEGER DEFAULT 0,
  working_hours DECIMAL(4,2), is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS shift_plans (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  employee_id UUID REFERENCES employees(id),
  shift_id UUID REFERENCES shifts(id),
  effective_from DATE NOT NULL, effective_to DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS attendance_records (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  employee_id UUID REFERENCES employees(id),
  attendance_date DATE NOT NULL,
  in_time TIMESTAMPTZ, out_time TIMESTAMPTZ,
  working_hours DECIMAL(5,2), late_minutes INTEGER DEFAULT 0,
  overtime_hours DECIMAL(5,2) DEFAULT 0,
  status VARCHAR(30) DEFAULT 'present',
  remarks TEXT, is_manual BOOLEAN DEFAULT false,
  UNIQUE(employee_id, attendance_date)
);
CREATE TABLE IF NOT EXISTS weekends (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  day_of_week INTEGER NOT NULL, is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS holidays (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  holiday_date DATE NOT NULL, name VARCHAR(200) NOT NULL,
  holiday_type VARCHAR(50), is_active BOOLEAN DEFAULT true
);

-- LEAVE
CREATE TABLE IF NOT EXISTS leave_categories (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS leave_types (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  category_id UUID REFERENCES leave_categories(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(100) NOT NULL,
  days_per_year INTEGER DEFAULT 0, is_paid BOOLEAN DEFAULT true,
  carry_forward BOOLEAN DEFAULT false, is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS leave_quotas (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  employee_id UUID REFERENCES employees(id),
  leave_type_id UUID REFERENCES leave_types(id),
  fiscal_year_id UUID REFERENCES fiscal_years(id),
  allocated_days INTEGER DEFAULT 0, used_days INTEGER DEFAULT 0,
  carried_forward INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS leave_applications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  application_no VARCHAR(30) UNIQUE NOT NULL,
  employee_id UUID REFERENCES employees(id),
  leave_type_id UUID REFERENCES leave_types(id),
  from_date DATE NOT NULL, to_date DATE NOT NULL,
  total_days INTEGER, reason TEXT,
  status VARCHAR(30) DEFAULT 'pending',
  applied_at TIMESTAMPTZ DEFAULT NOW(),
  approved_by UUID REFERENCES user_profiles(id),
  approved_at TIMESTAMPTZ, rejection_reason TEXT
);

-- PAYROLL
CREATE TABLE IF NOT EXISTS salary_grades (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  grade_id UUID REFERENCES employee_grades(id),
  basic_salary DECIMAL(15,2) NOT NULL,
  effective_date DATE NOT NULL, is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS allowance_types (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(100) NOT NULL,
  calculation_type VARCHAR(30), is_taxable BOOLEAN DEFAULT false,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS deduction_types (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(100) NOT NULL,
  calculation_type VARCHAR(30), is_mandatory BOOLEAN DEFAULT false,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS salary_sheets (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  month INTEGER NOT NULL, year INTEGER NOT NULL,
  fiscal_year_id UUID REFERENCES fiscal_years(id),
  status VARCHAR(30) DEFAULT 'draft',
  total_basic DECIMAL(15,2) DEFAULT 0,
  total_allowances DECIMAL(15,2) DEFAULT 0,
  total_deductions DECIMAL(15,2) DEFAULT 0,
  total_net_pay DECIMAL(15,2) DEFAULT 0,
  processed_by UUID REFERENCES user_profiles(id),
  processed_at TIMESTAMPTZ,
  UNIQUE(company_id, branch_id, month, year)
);
CREATE TABLE IF NOT EXISTS salary_details (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  salary_sheet_id UUID REFERENCES salary_sheets(id) ON DELETE CASCADE,
  employee_id UUID REFERENCES employees(id),
  basic_salary DECIMAL(15,2) DEFAULT 0,
  house_rent DECIMAL(15,2) DEFAULT 0,
  medical_allowance DECIMAL(15,2) DEFAULT 0,
  transport_allowance DECIMAL(15,2) DEFAULT 0,
  other_allowances DECIMAL(15,2) DEFAULT 0,
  gross_salary DECIMAL(15,2) DEFAULT 0,
  pf_deduction DECIMAL(15,2) DEFAULT 0,
  tax_deduction DECIMAL(15,2) DEFAULT 0,
  other_deductions DECIMAL(15,2) DEFAULT 0,
  total_deductions DECIMAL(15,2) DEFAULT 0,
  net_pay DECIMAL(15,2) DEFAULT 0,
  present_days INTEGER DEFAULT 0, absent_days INTEGER DEFAULT 0,
  remarks TEXT
);
CREATE TABLE IF NOT EXISTS loan_types (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(100) NOT NULL,
  max_amount DECIMAL(15,2), interest_rate DECIMAL(5,2) DEFAULT 0,
  max_installments INTEGER, is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS employee_loans (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  loan_no VARCHAR(30) UNIQUE NOT NULL,
  employee_id UUID REFERENCES employees(id),
  loan_type_id UUID REFERENCES loan_types(id),
  applied_amount DECIMAL(15,2) NOT NULL,
  approved_amount DECIMAL(15,2), disbursed_amount DECIMAL(15,2) DEFAULT 0,
  interest_rate DECIMAL(5,2) DEFAULT 0,
  total_installments INTEGER, installment_amount DECIMAL(15,2),
  applied_date DATE NOT NULL, approved_date DATE, disbursement_date DATE,
  status VARCHAR(30) DEFAULT 'pending',
  approved_by UUID REFERENCES user_profiles(id), remarks TEXT
);
CREATE TABLE IF NOT EXISTS pf_rules (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  employee_contribution_pct DECIMAL(5,2) DEFAULT 10,
  employer_contribution_pct DECIMAL(5,2) DEFAULT 10,
  effective_date DATE NOT NULL, is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS pf_members (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  employee_id UUID REFERENCES employees(id) UNIQUE,
  membership_date DATE NOT NULL,
  opening_balance DECIMAL(15,2) DEFAULT 0,
  is_active BOOLEAN DEFAULT true
);

-- ============================================================
-- 6. INVENTORY
-- ============================================================
CREATE TABLE IF NOT EXISTS item_types (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS item_groups (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  parent_id UUID REFERENCES item_groups(id), is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS item_categories (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  group_id UUID REFERENCES item_groups(id),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS item_subcategories (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  category_id UUID REFERENCES item_categories(id),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS item_brands (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS item_models (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  brand_id UUID REFERENCES item_brands(id),
  code VARCHAR(30) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS units (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(50) NOT NULL,
  description TEXT, is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS store_rooms (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(100) NOT NULL,
  location TEXT, is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS racks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_room_id UUID REFERENCES store_rooms(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(50) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS bins (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  rack_id UUID REFERENCES racks(id),
  code VARCHAR(20) NOT NULL, name VARCHAR(50) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  item_code VARCHAR(30) UNIQUE NOT NULL,
  barcode VARCHAR(50) UNIQUE,
  name VARCHAR(200) NOT NULL, name_bn VARCHAR(200), description TEXT,
  item_type_id UUID REFERENCES item_types(id),
  group_id UUID REFERENCES item_groups(id),
  category_id UUID REFERENCES item_categories(id),
  subcategory_id UUID REFERENCES item_subcategories(id),
  brand_id UUID REFERENCES item_brands(id),
  model_id UUID REFERENCES item_models(id),
  primary_unit_id UUID REFERENCES units(id),
  secondary_unit_id UUID REFERENCES units(id),
  conversion_factor DECIMAL(10,4) DEFAULT 1,
  purchase_price DECIMAL(15,2) DEFAULT 0,
  selling_price DECIMAL(15,2) DEFAULT 0,
  mrp DECIMAL(15,2) DEFAULT 0,
  vat_group_id UUID REFERENCES vat_groups(id),
  reorder_level DECIMAL(15,4) DEFAULT 0,
  reorder_qty DECIMAL(15,4) DEFAULT 0,
  min_stock DECIMAL(15,4) DEFAULT 0,
  max_stock DECIMAL(15,4) DEFAULT 0,
  color_id UUID REFERENCES colors(id),
  size_id UUID REFERENCES sizes(id),
  default_store_room_id UUID REFERENCES store_rooms(id),
  is_serialized BOOLEAN DEFAULT false,
  is_batched BOOLEAN DEFAULT false,
  has_warranty BOOLEAN DEFAULT false,
  warranty_months INTEGER DEFAULT 0,
  image_url TEXT, is_active BOOLEAN DEFAULT true,
  created_by UUID, created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS stock_ledger (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  store_room_id UUID REFERENCES store_rooms(id),
  item_id UUID REFERENCES items(id),
  transaction_date DATE NOT NULL,
  transaction_type VARCHAR(50) NOT NULL,
  reference_type VARCHAR(50),
  reference_id UUID, reference_no VARCHAR(50),
  in_qty DECIMAL(15,4) DEFAULT 0,
  out_qty DECIMAL(15,4) DEFAULT 0,
  unit_cost DECIMAL(15,4) DEFAULT 0,
  total_cost DECIMAL(15,2) DEFAULT 0,
  balance_qty DECIMAL(15,4),
  remarks TEXT, created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 7. SUPPLIER
-- ============================================================
CREATE TABLE IF NOT EXISTS supplier_groups (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS suppliers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  supplier_code VARCHAR(30) UNIQUE NOT NULL,
  name VARCHAR(200) NOT NULL, name_bn VARCHAR(200),
  group_id UUID REFERENCES supplier_groups(id),
  contact_person VARCHAR(200), phone VARCHAR(50),
  mobile VARCHAR(50), email VARCHAR(100), website VARCHAR(100),
  address TEXT, district_id UUID REFERENCES districts(id),
  trade_license VARCHAR(100), tin VARCHAR(50), bin VARCHAR(50),
  credit_limit DECIMAL(15,2) DEFAULT 0, credit_days INTEGER DEFAULT 0,
  opening_balance DECIMAL(15,2) DEFAULT 0,
  current_balance DECIMAL(15,2) DEFAULT 0,
  bank_id UUID REFERENCES banks(id),
  bank_account_number VARCHAR(50), bank_account_name VARCHAR(200),
  payment_term_id UUID REFERENCES payment_terms(id),
  is_active BOOLEAN DEFAULT true, created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 8. CUSTOMER
-- ============================================================
CREATE TABLE IF NOT EXISTS customer_groups (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  discount_percentage DECIMAL(5,2) DEFAULT 0,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS customers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  customer_code VARCHAR(30) UNIQUE NOT NULL,
  customer_type VARCHAR(30) DEFAULT 'individual',
  name VARCHAR(200) NOT NULL, name_bn VARCHAR(200),
  group_id UUID REFERENCES customer_groups(id),
  contact_person VARCHAR(200), phone VARCHAR(50),
  mobile VARCHAR(50), email VARCHAR(100),
  address TEXT, district_id UUID REFERENCES districts(id),
  trade_license VARCHAR(100), tin VARCHAR(50), nid VARCHAR(30),
  credit_limit DECIMAL(15,2) DEFAULT 0, credit_days INTEGER DEFAULT 0,
  opening_balance DECIMAL(15,2) DEFAULT 0,
  current_balance DECIMAL(15,2) DEFAULT 0,
  loyalty_points INTEGER DEFAULT 0,
  payment_term_id UUID REFERENCES payment_terms(id),
  is_active BOOLEAN DEFAULT true, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS dealers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  customer_id UUID REFERENCES customers(id),
  dealer_code VARCHAR(30) UNIQUE NOT NULL,
  territory TEXT, commission_rate DECIMAL(5,2) DEFAULT 0,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS brokers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  broker_code VARCHAR(30) UNIQUE NOT NULL, name VARCHAR(200) NOT NULL,
  phone VARCHAR(50), commission_rate DECIMAL(5,2) DEFAULT 0,
  is_active BOOLEAN DEFAULT true
);

-- ============================================================
-- 9. PURCHASE
-- ============================================================
CREATE TABLE IF NOT EXISTS purchase_requisitions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  pr_no VARCHAR(30) UNIQUE NOT NULL,
  pr_date DATE NOT NULL, required_date DATE,
  department_id UUID REFERENCES departments(id),
  requested_by UUID REFERENCES employees(id),
  status VARCHAR(30) DEFAULT 'pending',
  remarks TEXT, created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS purchase_requisition_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  pr_id UUID REFERENCES purchase_requisitions(id) ON DELETE CASCADE,
  item_id UUID REFERENCES items(id),
  quantity DECIMAL(15,4) NOT NULL,
  unit_id UUID REFERENCES units(id),
  estimated_price DECIMAL(15,2), remarks TEXT
);
CREATE TABLE IF NOT EXISTS purchase_orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  po_no VARCHAR(30) UNIQUE NOT NULL,
  po_date DATE NOT NULL,
  supplier_id UUID REFERENCES suppliers(id),
  pr_id UUID REFERENCES purchase_requisitions(id),
  expected_delivery DATE,
  payment_term_id UUID REFERENCES payment_terms(id),
  sub_total DECIMAL(15,2) DEFAULT 0,
  discount_amount DECIMAL(15,2) DEFAULT 0,
  vat_amount DECIMAL(15,2) DEFAULT 0,
  total_amount DECIMAL(15,2) DEFAULT 0,
  status VARCHAR(30) DEFAULT 'open',
  remarks TEXT, created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS purchase_order_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  po_id UUID REFERENCES purchase_orders(id) ON DELETE CASCADE,
  item_id UUID REFERENCES items(id),
  ordered_qty DECIMAL(15,4) NOT NULL,
  received_qty DECIMAL(15,4) DEFAULT 0,
  unit_id UUID REFERENCES units(id),
  unit_price DECIMAL(15,4) NOT NULL,
  discount_pct DECIMAL(5,2) DEFAULT 0,
  discount_amount DECIMAL(15,2) DEFAULT 0,
  vat_pct DECIMAL(5,2) DEFAULT 0,
  vat_amount DECIMAL(15,2) DEFAULT 0,
  total_amount DECIMAL(15,2) DEFAULT 0
);
CREATE TABLE IF NOT EXISTS grn_headers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  grn_no VARCHAR(30) UNIQUE NOT NULL,
  grn_date DATE NOT NULL,
  po_id UUID REFERENCES purchase_orders(id),
  supplier_id UUID REFERENCES suppliers(id),
  store_room_id UUID REFERENCES store_rooms(id),
  status VARCHAR(30) DEFAULT 'received',
  remarks TEXT, created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS grn_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  grn_id UUID REFERENCES grn_headers(id) ON DELETE CASCADE,
  item_id UUID REFERENCES items(id),
  received_qty DECIMAL(15,4) NOT NULL,
  accepted_qty DECIMAL(15,4) NOT NULL,
  rejected_qty DECIMAL(15,4) DEFAULT 0,
  unit_id UUID REFERENCES units(id),
  unit_cost DECIMAL(15,4) NOT NULL,
  total_cost DECIMAL(15,2) DEFAULT 0
);
CREATE TABLE IF NOT EXISTS purchases (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  purchase_no VARCHAR(30) UNIQUE NOT NULL,
  purchase_date DATE NOT NULL,
  invoice_no VARCHAR(50), invoice_date DATE,
  supplier_id UUID REFERENCES suppliers(id),
  po_id UUID REFERENCES purchase_orders(id),
  grn_id UUID REFERENCES grn_headers(id),
  store_room_id UUID REFERENCES store_rooms(id),
  payment_method_id UUID REFERENCES payment_methods(id),
  sub_total DECIMAL(15,2) DEFAULT 0,
  discount_amount DECIMAL(15,2) DEFAULT 0,
  vat_amount DECIMAL(15,2) DEFAULT 0,
  other_charges DECIMAL(15,2) DEFAULT 0,
  total_amount DECIMAL(15,2) DEFAULT 0,
  paid_amount DECIMAL(15,2) DEFAULT 0,
  due_amount DECIMAL(15,2) DEFAULT 0,
  status VARCHAR(30) DEFAULT 'unpaid',
  remarks TEXT, created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS purchase_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  purchase_id UUID REFERENCES purchases(id) ON DELETE CASCADE,
  item_id UUID REFERENCES items(id),
  quantity DECIMAL(15,4) NOT NULL,
  unit_id UUID REFERENCES units(id),
  unit_cost DECIMAL(15,4) NOT NULL,
  discount_pct DECIMAL(5,2) DEFAULT 0,
  discount_amount DECIMAL(15,2) DEFAULT 0,
  vat_pct DECIMAL(5,2) DEFAULT 0,
  vat_amount DECIMAL(15,2) DEFAULT 0,
  total_amount DECIMAL(15,2) DEFAULT 0
);

-- ============================================================
-- 10. SALES
-- ============================================================
CREATE TABLE IF NOT EXISTS sales_orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  order_no VARCHAR(30) UNIQUE NOT NULL,
  order_date DATE NOT NULL, delivery_date DATE,
  customer_id UUID REFERENCES customers(id),
  sales_person_id UUID REFERENCES employees(id),
  broker_id UUID REFERENCES brokers(id),
  store_room_id UUID REFERENCES store_rooms(id),
  payment_term_id UUID REFERENCES payment_terms(id),
  sub_total DECIMAL(15,2) DEFAULT 0,
  discount_amount DECIMAL(15,2) DEFAULT 0,
  vat_amount DECIMAL(15,2) DEFAULT 0,
  delivery_charge DECIMAL(15,2) DEFAULT 0,
  total_amount DECIMAL(15,2) DEFAULT 0,
  status VARCHAR(30) DEFAULT 'pending',
  remarks TEXT, created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS sales_order_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  order_id UUID REFERENCES sales_orders(id) ON DELETE CASCADE,
  item_id UUID REFERENCES items(id),
  ordered_qty DECIMAL(15,4) NOT NULL,
  delivered_qty DECIMAL(15,4) DEFAULT 0,
  unit_id UUID REFERENCES units(id),
  unit_price DECIMAL(15,4) NOT NULL,
  discount_pct DECIMAL(5,2) DEFAULT 0,
  discount_amount DECIMAL(15,2) DEFAULT 0,
  vat_pct DECIMAL(5,2) DEFAULT 0,
  vat_amount DECIMAL(15,2) DEFAULT 0,
  total_amount DECIMAL(15,2) DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sales_invoices (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  invoice_no VARCHAR(30) UNIQUE NOT NULL,
  invoice_date DATE NOT NULL,
  customer_id UUID REFERENCES customers(id),
  order_id UUID REFERENCES sales_orders(id),
  sales_person_id UUID REFERENCES employees(id),
  store_room_id UUID REFERENCES store_rooms(id),
  payment_method_id UUID REFERENCES payment_methods(id),
  is_pos BOOLEAN DEFAULT false,
  sub_total DECIMAL(15,2) DEFAULT 0,
  discount_amount DECIMAL(15,2) DEFAULT 0,
  vat_amount DECIMAL(15,2) DEFAULT 0,
  delivery_charge DECIMAL(15,2) DEFAULT 0,
  total_amount DECIMAL(15,2) DEFAULT 0,
  paid_amount DECIMAL(15,2) DEFAULT 0,
  due_amount DECIMAL(15,2) DEFAULT 0,
  status VARCHAR(30) DEFAULT 'unpaid',
  remarks TEXT, created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS sales_invoice_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  invoice_id UUID REFERENCES sales_invoices(id) ON DELETE CASCADE,
  item_id UUID REFERENCES items(id),
  quantity DECIMAL(15,4) NOT NULL,
  unit_id UUID REFERENCES units(id),
  unit_price DECIMAL(15,4) NOT NULL,
  discount_pct DECIMAL(5,2) DEFAULT 0,
  discount_amount DECIMAL(15,2) DEFAULT 0,
  vat_pct DECIMAL(5,2) DEFAULT 0,
  vat_amount DECIMAL(15,2) DEFAULT 0,
  total_amount DECIMAL(15,2) DEFAULT 0,
  cost_price DECIMAL(15,4) DEFAULT 0
);
CREATE TABLE IF NOT EXISTS money_receipts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  receipt_no VARCHAR(30) UNIQUE NOT NULL,
  receipt_date DATE NOT NULL,
  customer_id UUID REFERENCES customers(id),
  amount DECIMAL(15,2) NOT NULL,
  payment_method_id UUID REFERENCES payment_methods(id),
  bank_id UUID REFERENCES banks(id),
  cheque_no VARCHAR(50), cheque_date DATE,
  reference_invoice_id UUID REFERENCES sales_invoices(id),
  remarks TEXT, created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 11. ACCOUNTS
-- ============================================================
CREATE TABLE IF NOT EXISTS gl_categories (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  type VARCHAR(30), is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS chart_of_accounts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  account_code VARCHAR(30) NOT NULL,
  account_name VARCHAR(200) NOT NULL, account_name_bn VARCHAR(200),
  parent_id UUID REFERENCES chart_of_accounts(id),
  gl_category_id UUID REFERENCES gl_categories(id),
  account_type VARCHAR(30),
  is_bank_account BOOLEAN DEFAULT false,
  bank_id UUID REFERENCES banks(id),
  bank_account_number VARCHAR(50),
  opening_balance DECIMAL(15,2) DEFAULT 0,
  balance_type VARCHAR(10) DEFAULT 'debit',
  level_number INTEGER DEFAULT 1,
  is_leaf BOOLEAN DEFAULT true, is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(company_id, account_code)
);
CREATE TABLE IF NOT EXISTS cost_centers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  budget_amount DECIMAL(15,2) DEFAULT 0,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS vouchers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  voucher_no VARCHAR(30) UNIQUE NOT NULL,
  voucher_date DATE NOT NULL,
  voucher_type VARCHAR(30) NOT NULL,
  fiscal_year_id UUID REFERENCES fiscal_years(id),
  period_id UUID REFERENCES accounting_periods(id),
  narration TEXT, reference_no VARCHAR(50),
  total_debit DECIMAL(15,2) DEFAULT 0,
  total_credit DECIMAL(15,2) DEFAULT 0,
  status VARCHAR(30) DEFAULT 'draft',
  posted_by UUID REFERENCES user_profiles(id),
  posted_at TIMESTAMPTZ, created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS voucher_lines (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  voucher_id UUID REFERENCES vouchers(id) ON DELETE CASCADE,
  account_id UUID REFERENCES chart_of_accounts(id),
  debit_amount DECIMAL(15,2) DEFAULT 0,
  credit_amount DECIMAL(15,2) DEFAULT 0,
  narration TEXT, cost_center_id UUID REFERENCES cost_centers(id),
  reference_type VARCHAR(50), reference_id UUID
);

-- ============================================================
-- 12. CREDIT SALES
-- ============================================================
CREATE TABLE IF NOT EXISTS credit_sales (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  credit_sale_no VARCHAR(30) UNIQUE NOT NULL,
  sale_date DATE NOT NULL,
  customer_id UUID REFERENCES customers(id),
  invoice_id UUID REFERENCES sales_invoices(id),
  total_amount DECIMAL(15,2) NOT NULL,
  down_payment DECIMAL(15,2) DEFAULT 0,
  financed_amount DECIMAL(15,2),
  interest_rate DECIMAL(5,2) DEFAULT 0,
  total_installments INTEGER NOT NULL,
  installment_amount DECIMAL(15,2),
  first_installment_date DATE,
  status VARCHAR(30) DEFAULT 'active',
  guarantor_name VARCHAR(200), guarantor_phone VARCHAR(50),
  guarantor_nid VARCHAR(30),
  created_by UUID, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS installment_schedules (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  credit_sale_id UUID REFERENCES credit_sales(id) ON DELETE CASCADE,
  installment_no INTEGER NOT NULL,
  due_date DATE NOT NULL,
  installment_amount DECIMAL(15,2) NOT NULL,
  principal_amount DECIMAL(15,2) DEFAULT 0,
  interest_amount DECIMAL(15,2) DEFAULT 0,
  paid_amount DECIMAL(15,2) DEFAULT 0,
  paid_date DATE, status VARCHAR(30) DEFAULT 'pending',
  delay_charge DECIMAL(15,2) DEFAULT 0
);

-- ============================================================
-- 13. PRODUCTION
-- ============================================================
CREATE TABLE IF NOT EXISTS bom_headers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  finished_item_id UUID REFERENCES items(id),
  bom_no VARCHAR(30) UNIQUE NOT NULL,
  bom_version VARCHAR(10) DEFAULT '1.0',
  description TEXT, output_qty DECIMAL(15,4) DEFAULT 1,
  unit_id UUID REFERENCES units(id),
  is_current BOOLEAN DEFAULT true,
  effective_from DATE, effective_to DATE,
  created_by UUID, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS bom_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  bom_id UUID REFERENCES bom_headers(id) ON DELETE CASCADE,
  component_item_id UUID REFERENCES items(id),
  quantity DECIMAL(15,4) NOT NULL,
  unit_id UUID REFERENCES units(id),
  waste_percentage DECIMAL(5,2) DEFAULT 0,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS production_orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  order_no VARCHAR(30) UNIQUE NOT NULL,
  order_date DATE NOT NULL, planned_date DATE, completed_date DATE,
  finished_item_id UUID REFERENCES items(id),
  bom_id UUID REFERENCES bom_headers(id),
  planned_qty DECIMAL(15,4) NOT NULL,
  produced_qty DECIMAL(15,4) DEFAULT 0,
  status VARCHAR(30) DEFAULT 'planned',
  remarks TEXT, created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 14. SERVICE
-- ============================================================
CREATE TABLE IF NOT EXISTS service_types (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  code VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS job_cards (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  branch_id UUID REFERENCES branches(id),
  job_card_no VARCHAR(30) UNIQUE NOT NULL,
  job_date DATE NOT NULL,
  customer_id UUID REFERENCES customers(id),
  vehicle_model VARCHAR(100), vehicle_reg_no VARCHAR(50),
  chassis_no VARCHAR(100), engine_no VARCHAR(100),
  service_type_id UUID REFERENCES service_types(id),
  complaint TEXT, diagnosis TEXT,
  estimated_amount DECIMAL(15,2), final_amount DECIMAL(15,2),
  status VARCHAR(30) DEFAULT 'received',
  delivery_date DATE, remarks TEXT, created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 15. CRM
-- ============================================================
CREATE TABLE IF NOT EXISTS leads (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  lead_no VARCHAR(30) UNIQUE NOT NULL,
  name VARCHAR(200) NOT NULL,
  phone VARCHAR(50), email VARCHAR(100),
  source VARCHAR(50), product_interest TEXT,
  estimated_value DECIMAL(15,2),
  assigned_to UUID REFERENCES employees(id),
  status VARCHAR(30) DEFAULT 'new',
  notes TEXT, created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 16. LC MANAGEMENT
-- ============================================================
CREATE TABLE IF NOT EXISTS proforma_invoices (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  pi_no VARCHAR(30) UNIQUE NOT NULL,
  pi_date DATE NOT NULL,
  supplier_id UUID REFERENCES suppliers(id),
  country_id UUID REFERENCES countries(id),
  total_amount DECIMAL(15,2) NOT NULL,
  currency_id UUID REFERENCES currencies(id),
  validity_date DATE, payment_terms TEXT,
  status VARCHAR(30) DEFAULT 'draft',
  created_by UUID, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS letters_of_credit (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id),
  lc_no VARCHAR(50) UNIQUE NOT NULL,
  lc_date DATE NOT NULL,
  pi_id UUID REFERENCES proforma_invoices(id),
  supplier_id UUID REFERENCES suppliers(id),
  bank_id UUID REFERENCES banks(id),
  lc_amount DECIMAL(15,2) NOT NULL,
  currency_id UUID REFERENCES currencies(id),
  expiry_date DATE, shipment_deadline DATE,
  status VARCHAR(30) DEFAULT 'opened',
  created_by UUID, created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 17. ROW LEVEL SECURITY (RLS)
-- ============================================================
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE vouchers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "company_isolation" ON employees
  USING (company_id IN (
    SELECT company_id FROM user_profiles WHERE id = auth.uid()
  ));
CREATE POLICY "company_isolation" ON sales_invoices
  USING (company_id IN (
    SELECT company_id FROM user_profiles WHERE id = auth.uid()
  ));
CREATE POLICY "company_isolation" ON purchases
  USING (company_id IN (
    SELECT company_id FROM user_profiles WHERE id = auth.uid()
  ));
CREATE POLICY "company_isolation" ON vouchers
  USING (company_id IN (
    SELECT company_id FROM user_profiles WHERE id = auth.uid()
  ));

-- ============================================================
-- 18. SEED DATA
-- ============================================================
INSERT INTO countries (code, name, name_bn, currency_code, phone_code)
VALUES ('BD','Bangladesh','বাংলাদেশ','BDT','+880'),
       ('US','United States','যুক্তরাষ্ট্র','USD','+1'),
       ('IN','India','ভারত','INR','+91')
ON CONFLICT (code) DO NOTHING;

INSERT INTO currencies (code, name, symbol, is_base)
VALUES ('BDT','Bangladeshi Taka','৳',true),
       ('USD','US Dollar','$',false),
       ('EUR','Euro','€',false)
ON CONFLICT (code) DO NOTHING;

INSERT INTO payment_methods (code, name)
VALUES ('CASH','Cash'),('CHEQUE','Cheque'),('BANK_TRANSFER','Bank Transfer'),
       ('BKASH','bKash'),('NAGAD','Nagad'),('ROCKET','Rocket'),('CARD','Card')
ON CONFLICT (code) DO NOTHING;

INSERT INTO payment_terms (code, name, days)
VALUES ('IMMEDIATE','Immediate',0),('NET15','Net 15 Days',15),
       ('NET30','Net 30 Days',30),('NET60','Net 60 Days',60),
       ('NET90','Net 90 Days',90)
ON CONFLICT (code) DO NOTHING;

INSERT INTO units (code, name)
VALUES ('PCS','Pieces'),('KG','Kilogram'),('LTR','Liter'),
       ('MTR','Meter'),('BOX','Box'),('SET','Set'),('DOZ','Dozen')
ON CONFLICT (code) DO NOTHING;

INSERT INTO vat_groups (code, name, rate)
VALUES ('NO_VAT','No VAT',0),('VAT_15','VAT 15%',15),('VAT_5','VAT 5%',5)
ON CONFLICT (code) DO NOTHING;

-- Default GL Categories
-- (Insert after creating a company)

SELECT 'SaforaERP Database Setup Complete! Tables: ' || count(*)::text || ' created.'
FROM information_schema.tables 
WHERE table_schema = 'public';
