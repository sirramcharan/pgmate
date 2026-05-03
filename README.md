# 🏠 LayZ — Smart PG & Hostel Management

A production-ready **multi-page Streamlit SaaS app** built for Indian PG and hostel owners.
Manage buildings, rooms, beds, tenants, rent collection, expenses, and analytics — all backed by **Google Sheets** as the database.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🏢 Buildings | Add/edit/delete buildings with occupancy overview |
| 🚪 Rooms & Beds | Multi-bed rooms, per-bed occupancy tracking |
| 👤 Tenants | Full tenant profiles with rent history |
| 💰 Rent Collection | Month-wise tracking, mark paid, partial payments |
| ⚡ Just Paid | Quick-action page for instant payment marking |
| 💸 Expenses | Category-wise expense tracker with CSV export |
| 📊 Analytics | Plotly charts: trends, occupancy, revenue, expenses |
| 📲 WhatsApp | wa.me reminder links for each pending tenant |
| 🔐 Auth | bcrypt-hashed passwords, role-based access |
| 💳 Billing | Razorpay subscription gating, trial + active plans |
| 🌱 Demo Mode | One-click seed with 2 buildings, 10 tenants |
| 📋 Google Sheets | Full CRUD on Google Sheets; auto-creates missing sheets |

---

## 📁 File Structure

```
LayZ/
├── app.py                    # Main entry — login + routing
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   ├── config.toml           # Dark theme config
│   └── secrets.toml.example  # Template (copy → secrets.toml)
├── utils/
│   ├── auth.py               # Login, register, bcrypt, session
│   ├── billing.py            # Subscription gate + Razorpay stub
│   ├── sheets.py             # Google Sheets CRUD helpers
│   ├── helpers.py            # Business logic (buildings→rent)
│   ├── analytics.py          # Chart data aggregations
│   ├── styles.py             # CSS injection + badge/card helpers
│   └── seed.py               # Demo data seeder
└── pages/
    ├── 1_Dashboard.py
    ├── 2_Buildings.py
    ├── 3_Rooms.py
    ├── 4_Tenants.py
    ├── 5_Add_Tenant.py
    ├── 6_Rent_Collection.py
    ├── 7_Just_Paid.py
    ├── 8_Expenses.py
    ├── 9_Analytics.py
    ├── 10_Settings.py
    └── 11_Billing.py
```

---

## 🗄️ Google Sheets Setup

### Step 1 — Create the Spreadsheet

1. Go to [Google Sheets](https://sheets.google.com).
2. Create a new spreadsheet named exactly: **`LayZ_DB`**
3. The app will auto-create all required sheets (tabs) on first run.

### Step 2 — Required Sheets & Columns

Each sheet is auto-created by the app if missing. For reference:

#### `Users`
`user_id | name | email | phone | password_hash | role | pg_name | subscription_status | plan_name | trial_start_date | expiry_date | razorpay_customer_id | razorpay_subscription_id | payment_link | is_active | created_at`

#### `Settings`
`setting_id | owner_email | default_rent_due_day | grace_period_days | auto_reminder_enabled | late_fee_enabled | late_fee_amount | created_at | updated_at`

#### `Buildings`
`building_id | owner_email | building_name | address | city | state | pincode | is_active | created_at | updated_at`

#### `Rooms`
`room_id | owner_email | building_id | room_label | room_number | floor | sharing_type | capacity_beds | status | notes | created_at | updated_at`

#### `Beds`
`bed_id | owner_email | building_id | room_id | bed_label | status | tenant_id | monthly_rent | move_in_date | created_at | updated_at`

#### `Tenants`
`tenant_id | owner_email | building_id | room_id | bed_id | tenant_name | phone | email | move_in_date | move_out_date | tenant_status | id_proof_url | id_proof_type | monthly_rent | security_deposit | deposit_paid | emergency_contact_name | emergency_contact_phone | company_or_college | hometown | notes | created_at | updated_at`

#### `RentMonths`
`rent_id | owner_email | tenant_id | building_id | room_id | bed_id | month_year | rent_month_date | amount | due_date | paid_on | payment_method | transaction_ref | status | notes | reminder_sent | reminder_sent_at | created_at | updated_at`

#### `Expenses`
`expense_id | owner_email | building_id | expense_title | category | amount | expense_date | vendor_payee | receipt_url | notes | created_at | updated_at`

#### `ActivityLog`
`log_id | owner_email | actor_email | action_type | entity_type | entity_id | action_details | created_at`

#### `Notifications`
`notification_id | owner_email | tenant_id | phone | channel | message | status | sent_at | created_at`

---

## ☁️ Google Cloud Service Account Setup

### Step 1 — Create a GCP Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (e.g. `layz-app`)

### Step 2 — Enable APIs
Enable both of these APIs in your project:
- **Google Sheets API** → `APIs & Services > Library > Google Sheets API > Enable`
- **Google Drive API** → `APIs & Services > Library > Google Drive API > Enable`

> ⚠️ Both APIs are required. gspread uses Drive API to open spreadsheets by name.

### Step 3 — Create Service Account
1. Go to `APIs & Services > Credentials > Create Credentials > Service Account`
2. Name it (e.g. `layz-service`)
3. Skip optional steps, click Done
4. Click the service account → `Keys` tab → `Add Key > Create new key > JSON`
5. Download the JSON file

### Step 4 — Share Spreadsheet with Service Account
1. Open your `LayZ_DB` spreadsheet in Google Sheets
2. Click `Share`
3. Paste the service account email (e.g. `layz-service@your-project.iam.gserviceaccount.com`)
4. Give it **Editor** access
5. Click Send

---

## 🔐 Secrets Configuration

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in values from your downloaded JSON key file:

```toml
[google_service_account]
type = "service_account"
project_id = "your-gcp-project-id"
private_key_id = "abc123..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "layz-service@your-project.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."

[app]
spreadsheet_name = "LayZ_DB"
demo_mode = true
app_password_salt = "change-this-random-string"

[razorpay]
payment_link = "https://rzp.io/your-payment-link"
plan_name = "LayZ Pro"
monthly_price = "499"
```

> ⚠️ The `private_key` value must keep the `\n` newline characters exactly as in the JSON file.

---

## 🖥️ Local Development

```bash
# 1. Clone the repo
git clone https://github.com/your-username/layz.git
cd layz

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your real credentials

# 5. Run the app
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### Demo Login (after seeding)
```
Email:    demo@layz.in
Password: demo1234
```

To seed demo data: go to **Settings → Demo Data → Seed Demo Data**.

---

## 🚀 Deploy on Streamlit Community Cloud

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial LayZ app"
   git remote add origin https://github.com/your-username/layz.git
   git push -u origin main
   ```

2. **Connect on Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click `New app`
   - Select your GitHub repository
   - Set **Main file path** to: `app.py`
   - Click **Deploy**

3. **Add Secrets**
   - In your deployed app → `⋮ Menu > Settings > Secrets`
   - Paste the full contents of your `secrets.toml`
   - Save and reboot the app

4. **Done!** Your app is live at `https://your-app.streamlit.app`

---

## 💳 Razorpay Integration

### Creating a Payment Link
1. Log in to [Razorpay Dashboard](https://dashboard.razorpay.com)
2. Go to `Payment Links > Create Payment Link`
3. Set amount to ₹499 (or your price), add description "LayZ Pro Subscription"
4. Copy the generated link (e.g. `https://rzp.io/l/your-link`)
5. Paste in `secrets.toml` under `[razorpay] payment_link`

### Subscription Plans (Advanced)
For recurring subscriptions:
1. Go to `Subscriptions > Plans > Create Plan`
2. Set interval to monthly, amount to ₹499
3. Note the `plan_id`
4. Use Razorpay Subscription API to create subscriptions per user

### Webhook Setup (Future)
The `utils/billing.py` file contains a `handle_razorpay_webhook()` stub. To activate:
1. Deploy a FastAPI/Flask endpoint that receives Razorpay webhook events
2. Events to handle: `subscription.activated`, `subscription.charged`, `subscription.cancelled`
3. Update the `Users` sheet `subscription_status` and `expiry_date` accordingly
4. Configure webhook URL in Razorpay Dashboard → `Settings > Webhooks`

---

## ⚠️ Known Limitations

- **Google Sheets is not a relational DB.** Joins are done in pandas. For large datasets (1000+ tenants), consider migrating to Firebase or Supabase.
- **No real-time updates.** Sheets are read fresh on each page load. Use Streamlit's `@st.cache_data` carefully.
- **No file uploads.** ID proof and receipt URLs are stored as text links only (e.g. Google Drive share links).
- **WhatsApp API not integrated.** Reminder links use `wa.me` (manual click). For automation, integrate Twilio or Interakt.
- **Razorpay webhook** requires a separate hosted endpoint — not possible on Streamlit Community Cloud alone. Use Render, Railway, or Vercel for the webhook handler.
- **Concurrent writes** may cause race conditions on Google Sheets if multiple owners write simultaneously. Acceptable for small-scale SaaS.

---

## 🔄 Updating the App

```bash
# Make changes locally, then:
git add .
git commit -m "Your update description"
git push
# Streamlit Cloud auto-redeploys on push
```

---

## 📬 Support

Built for Indian PG owners. For issues, feature requests, or custom deployments:
- Email: support@layz.in
- GitHub Issues: open an issue in this repo
