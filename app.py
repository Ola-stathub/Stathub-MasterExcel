import streamlit as st
import pandas as pd
import gspread
import re
from datetime import datetime
from google.oauth2.service_account import Credentials

MEET_LINK = "https://meet.google.com/yfi-asbp-hog"
MAX_JOINS = 10
ADMIN_PASSWORD = "AdeolaJane"
GOOGLE_SHEET_NAME = "StatHub Event Database"

# Set up page configurations
st.set_page_config(page_title="StatHub Event Access", page_icon="🎓", layout="centered")

# --- CENTRALIZED CUSTOM THEME INJECTION ---
st.markdown("""
    <style>
        [data-testid="stSidebar"], section[data-testid="stSidebarNav"], 
        header, footer {
            display: none !important;
        }
        .block-container {
            padding-top: 3rem !important;
        }
        .attendee-card {
            background: #ffffff;
            border: 1px solid #009DD9;
            padding: 3rem 2.5rem;
            border-radius: 16px;
            box-shadow: 0 8px 32px 0 rgba(0, 180, 216, 0.2);
            margin-bottom: 25px;
            text-align: center;
        }
        .attendee-title {
            color: #0567FA;
            font-family: 'Inter', sans-serif;
            font-weight: 800;
            font-size: 3.0rem;
            margin-bottom: 0.5rem;
            letter-spacing: -0.5px;
        }
        .attendee-subtitle {
            color: #0567FA;
            font-size: 1rem;
            margin-bottom: 2rem;
            opacity: 0.8;
        }
        .admin-card {
            background-color: #141419;
            border: 1px solid #2d2d38;
            padding: 2.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            margin-bottom: 20px;
        }
        .admin-title {
            color: #ffffff;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: 1.8rem;
            margin-bottom: 1.5rem;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def connect_sheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Dynamically pull the credentials dict from the Streamlit Cloud secure secrets vault
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=scope
    )
    client = gspread.authorize(creds)
    return client.open(GOOGLE_SHEET_NAME).sheet1

sheet = connect_sheet()

def load_data():
    return pd.DataFrame(sheet.get_all_records())

def normalize_phone(phone):
    phone = str(phone).strip()
    phone = re.sub(r"[^\d+]", "", phone)

    if phone.startswith("+234"):
        return "0" + phone[4:]
    if phone.startswith("234"):
        return "0" + phone[3:]
    if phone.startswith("+"):
        return phone

    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        return "0" + digits
    return digits

# Load fresh data
df = load_data()

if not df.empty:
    df["phone"] = df["phone"].astype(str).apply(normalize_phone)

# --- DETECT PAGE ROUTE VIA QUERY PARAMS ---
query_params = st.query_params
current_page = query_params.get("nav", "attendee")

# --- ATTENDEE PORTAL (ROYAL/SKY BLUE STYLE) ---
if current_page != "admin":
    st.markdown("""
        <div class="attendee-card">
            <div class="attendee-title">StatHub Datametrics</div>
            <div class="attendee-subtitle">Event Access Verification Portal</div>
        </div>
    """, unsafe_allow_html=True)
    
    phone = st.text_input("Phone Number", placeholder="e.g. 08012345678")
    code = st.text_input("Access Code", type="password", placeholder="••••••••")
    
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Verify Access", use_container_width=True):
        if not phone or not code:
            st.warning("Please fill in both fields.")
        else:
            phone = normalize_phone(phone)
            match = df[
                (df["phone"] == phone) &
                (df["access_code"] == str(code))
            ]

            if len(match) == 0:
                st.error("Invalid phone number or access code.")
            else:
                idx = match.index[0]
                joins = int(df.loc[idx, "join_count"])

                if joins >= MAX_JOINS:
                    st.error("Maximum number of joins reached.")
                else:
                    joins += 1
                    sheet.update_cell(idx + 2, 3, joins)
                    sheet.update_cell(idx + 2, 4, str(datetime.now()))
                    st.success("Verification Successful!")
                    st.link_button("🎥 JOIN EVENT", MEET_LINK, use_container_width=True)

# --- ADMIN PORTAL ---
else:
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        st.markdown('<div class="admin-card"><div class="admin-title">🔒 System Administrator Access</div>', unsafe_allow_html=True)
        password_input = st.text_input("Enter Admin Password Credentials", type="password")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if password_input == ADMIN_PASSWORD:
            st.session_state.admin_authenticated = True
            st.rerun()
        elif password_input:
            st.error("Access Denied: Incorrect Admin Password Credentials.")

    if st.session_state.admin_authenticated:
        st.title("🛡️ Admin Dashboard")
        st.markdown("---")
        
        total_registered = len(df)
        total_logged_in = len(df[df["join_count"] > 0]) if not df.empty else 0
        total_clicks_count = int(df["join_count"].sum()) if not df.empty else 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="👥 Registered Attendees", value=total_registered)
        with col2:
            st.metric(label="✅ Unique Attendees Logged In", value=total_logged_in)
        with col3:
            st.metric(label="📈 Total Event Joins (Clicks)", value=total_clicks_count)
            
        st.markdown("### 📊 Live Google Sheets Database Sync")
        st.dataframe(df, use_container_width=True)
        
        if st.button("Log Out of Admin"):
            st.session_state.admin_authenticated = False
            st.rerun()
