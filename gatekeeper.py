import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import hashlib

# Rate limiting configuration
MAX_ATTEMPTS = 5
LOCKOUT_DURATION = 15  # minutes
login_attempts = {}

def check_rate_limit(email: str) -> tuple[bool, str]:
    """Check if user is rate limited"""
    now = datetime.now()
    if email in login_attempts:
        attempts, lockout_time = login_attempts[email]
        if lockout_time and now < lockout_time:
            return False, f"Account locked for {LOCKOUT_DURATION} minutes"
        if now - attempts[0] < timedelta(minutes=LOCKOUT_DURATION):
            if len(attempts) >= MAX_ATTEMPTS:
                lockout_time = now + timedelta(minutes=LOCKOUT_DURATION)
                login_attempts[email] = (attempts, lockout_time)
                return False, f"Too many attempts. Account locked for {LOCKOUT_DURATION} minutes"
    return True, "OK"

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password meets security requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least 1 uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least 1 lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least 1 number"
    return True, "Password acceptable"

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def is_membership_expired(expiry_date):
    """Check if membership has expired"""
    if expiry_date == "Pending Admin" or pd.isna(expiry_date):
        return False
    try:
        exp = datetime.strptime(str(expiry_date), "%Y-%m-%d")
        return datetime.now() > exp
    except:
        return False

def show_login(conn):
    st.title("📟 JDL Intelligence System")
    t1, t2, t3 = st.tabs(["Member Login", "Request Access", "Admin Portal"])
    
    with t1:
        st.subheader("Member Access")
        email = st.text_input("Email").strip().lower()
        pwd = st.text_input("Password", type="password") 
        if st.button("Access Terminal"):
            try:
                df = conn.read(worksheet="Sheet1", ttl=0)
                df['Email'] = df['Email'].str.strip().str.lower()
                
                if email in df['Email'].values:
                    # Get user data
                    idx = df[df['Email'] == email].index[0]
                    user = df.iloc[idx]
                    
                    # Check if membership expired
                    if is_membership_expired(user.get('Expiry')):
                        st.error("❌ Your membership has expired. Please request renewal.")
                    # Validate Status and Password
                    elif str(user['Status']) == "Approved" and hash_password(pwd) == str(user['Password']):
                        # --- 1. UPDATE STATUS TO ONLINE ---
                        df.at[idx, 'Session'] = "Online"
                        df.at[idx, 'Last Login'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        conn.update(worksheet="Sheet1", data=df)
                        
                        # --- 2. SET SESSION STATE ---
                        st.session_state.user_verified = True
                        st.session_state.user_name = user['Name']
                        st.session_state.user_email = email
                        
                        # --- 3. SET QUERY PARAMS ---
                        st.query_params["u"] = email
                        
                        # --- 4. REDIRECT TO USER DASHBOARD ---
                        st.rerun()
                    elif str(user['Status']) != "Approved":
                        st.error(f"Access Denied: Status is '{user['Status']}'")
                    else:
                        st.error("Incorrect Password.")
                else:
                    st.error("Email not found.")
            except Exception as e:
                st.error(f"Login Error: {e}")

    with t2:
        st.subheader("Request Terminal Access")
        with st.form("req_form", clear_on_submit=True):
            n = st.text_input("Full Name")
            e = st.text_input("Email Address").strip().lower()
            p = st.text_input("Create Private Password", type="password")
            
            st.markdown("**Requested Membership Duration:**")
            duration = st.selectbox(
                "How long would you like access?",
                options=[
                    ("30 Days (1 Month)", 30),
                    ("60 Days (2 Months)", 60),
                    ("90 Days (3 Months)", 90),
                    ("180 Days (6 Months)", 180),
                    ("365 Days (1 Year)", 365),
                ],
                format_func=lambda x: x[0],
                label_visibility="collapsed"
            )
            
            if st.form_submit_button("Submit Request"):
                if n and e and p:
                    try:
                        df = conn.read(worksheet="Sheet1", ttl=0)
                        new_data = pd.DataFrame([{
                            "Name": n, 
                            "Email": e, 
                            "Password": hash_password(p),
                            "Date": datetime.now().strftime("%Y-%m-%d"), 
                            "Status": "Pending", 
                            "Requested Duration": f"{duration[1]} days",
                            "Expiry": "Pending Admin",
                            "Last Login": "Never", 
                            "Session": "Offline"
                        }])
                        # Append and update
                        updated_df = pd.concat([df, new_data], ignore_index=True)
                        conn.update(worksheet="Sheet1", data=updated_df)
                        st.success(f"✅ Request sent to Admin. You requested {duration[1]} days of access.")
                    except Exception as e:
                        st.error(f"Request Error: {e}")
                else:
                    st.warning("All fields are required.")

    with t3:
        st.subheader("System Administration")
        admin_key = st.text_input("Master Key", type="password")
        if st.button("Unlock Admin"):
            if admin_key == st.secrets.get("MASTER_KEY"):
                st.session_state.admin_verified = True
                st.rerun()
            else:
                st.error("Invalid Master Key.")
