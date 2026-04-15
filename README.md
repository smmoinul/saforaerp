# SaforaERP — Enterprise Resource Planning System

## Project Structure
```
SaforaERP_Project/
├── frontend/
│   └── index.html          ← Complete ERP Frontend (Single file)
├── backend/
│   ├── main.py             ← Complete FastAPI Backend (Single file, all endpoints)
│   ├── config.py           ← App configuration
│   ├── database.py         ← Supabase client
│   ├── requirements.txt    ← Python dependencies
│   ├── .env.example        ← Environment variables template
│   └── routers/            ← Modular API routers (alternative to main.py)
│       ├── auth.py
│       ├── hr.py
│       ├── inventory.py
│       ├── sales.py
│       ├── purchase.py
│       ├── accounts.py
│       ├── crm.py
│       ├── production.py
│       ├── service.py
│       ├── credit_sales.py
│       ├── lc.py
│       ├── supplier.py
│       ├── customer.py
│       ├── admin_mgmt.py
│       └── erp_overview.py
└── database/
    └── saforaerp_database.sql  ← Complete PostgreSQL schema (99 tables)
```

## Modules Covered
| Module | Forms | Reports | Status |
|--------|-------|---------|--------|
| Security & User Management | ✅ | ✅ | Complete |
| Human Resource Management | ✅ | ✅ | Complete |
| Admin Management | ✅ | ✅ | Complete |
| CRM | ✅ | ✅ | Complete |
| Inventory Management | ✅ | ✅ | Complete |
| Supplier Management | ✅ | ✅ | Complete |
| LC Management | ✅ | ✅ | Complete |
| Purchase Management | ✅ | ✅ | Complete |
| Customer Management | ✅ | ✅ | Complete |
| Production Management | ✅ | ✅ | Complete |
| Marketing Management | ✅ | ✅ | Complete |
| Sales Management | ✅ | ✅ | Complete |
| Credit Sales | ✅ | ✅ | Complete |
| Service Management | ✅ | ✅ | Complete |
| Accounts Management | ✅ | ✅ | Complete |
| ERP Overview Dashboard | ✅ | ✅ | Complete |

## Logo
The SaforaERP logo is embedded directly in the HTML (base64) and also available at `frontend/assets/logo.webp`.

## Quick Start

### Step 1: Database Setup
1. Go to [Supabase](https://supabase.com) → Create a new project
2. Go to **SQL Editor** → Paste and run `database/saforaerp_database.sql`
3. Go to **Authentication** → **Settings** → Enable Email provider

### Step 2: Create First User
In Supabase Dashboard → **Authentication** → **Users** → **Add User**
- Email: `admin@yourcompany.com`  
- Password: `Admin@123`

Then run in SQL Editor:
```sql
-- Create your company
INSERT INTO companies (code, name, is_active) 
VALUES ('MYCO', 'My Company Ltd', true);

-- Create admin profile (replace email if different)
INSERT INTO user_profiles (id, username, full_name, email, role, company_id, is_active)
SELECT 
    au.id, 'admin', 'System Administrator', au.email,
    'administrator',
    (SELECT id FROM companies WHERE code = 'MYCO'),
    true
FROM auth.users au 
WHERE au.email = 'admin@yourcompany.com';
```

### Step 3: Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase credentials

# Run server
python main.py
# API available at: http://localhost:8000
# API Docs at: http://localhost:8000/api/docs
```

### Step 4: Frontend Setup
1. Open `frontend/index.html` in your browser
2. Open browser Developer Console (F12)
3. Run:
```javascript
localStorage.setItem('erp_api_base', 'http://localhost:8000/api');
location.reload();
```
4. Login with your credentials

## API Endpoints (79 total)
- `POST /api/auth/login` — Login
- `GET  /api/auth/me` — Current user
- `GET  /api/hr/employees` — List employees
- `POST /api/hr/employees` — Create employee
- `GET  /api/sales/orders` — Sales orders
- `POST /api/sales/invoices` — Create invoice
- `GET  /api/inventory/items` — Item list
- ... and 72 more endpoints

Full API documentation: http://localhost:8000/api/docs

## Frontend Stats
- **108 Form implementations** — Each menu item has proper, context-specific form fields
- **174 Report pages** — With filters, print & CSV export
- **4 Dashboard views** — Live API data
- **53 async functions** — Full API integration
- **Bilingual** — English / বাংলা toggle

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla HTML/CSS/JS (zero dependencies) |
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL via Supabase |
| Auth | JWT + Supabase Auth |
| Storage | Supabase Storage |

## Production Deployment

### Backend
```bash
# Install production server
pip install gunicorn

# Run with multiple workers
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# Or with Docker
docker build -t saforaerp-api .
docker run -p 8000:8000 --env-file .env saforaerp-api
```

### Frontend
Upload `frontend/index.html` to any static hosting:
- GitHub Pages
- Netlify / Vercel
- Any web server (Apache/Nginx)

### Update API URL for production
```javascript
// In browser console on production site:
localStorage.setItem('erp_api_base', 'https://api.yourcompany.com/api');
```

## License
Proprietary — SaforaERP © 2025
