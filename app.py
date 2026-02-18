import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="High Cost Utilizer Dashboard", page_icon="💊", layout="wide")

st.title("💊 High Cost Utilizer Dashboard")

@st.cache_data(ttl=300)
def load_data():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    
    sheet = client.open_by_key("1g9bHdsz-jG6Bp14JT2U2HZcFe6GA3b3nm80aemkGvH0").worksheet("High Cost Utilizer")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Parse signupDate to datetime
    df['signupDate'] = pd.to_datetime(df['signupDate'], errors='coerce', utc=True)
    
    return df

df = load_data()

# --- Build summary table by employer ---
def build_summary(df):
    summary = df.groupby('employerName').agg(
        Total_HCUs=('userId', 'count')
    ).reset_index()
    
    # Enrolled in Jan 2026
    jan_enrolled = df[
        (df['enrollmentStatus'] == 'ENROLLED') &
        (df['signupDate'].dt.year == 2026) &
        (df['signupDate'].dt.month == 1)
    ].groupby('employerName').size().reset_index(name='Enrolled_Jan_2026')
    
    # Enrolled in Feb 2026
    feb_enrolled = df[
        (df['enrollmentStatus'] == 'ENROLLED') &
        (df['signupDate'].dt.year == 2026) &
        (df['signupDate'].dt.month == 2)
    ].groupby('employerName').size().reset_index(name='Enrolled_Feb_2026')
    
    summary = summary.merge(jan_enrolled, on='employerName', how='left')
    summary = summary.merge(feb_enrolled, on='employerName', how='left')
    
    summary['Enrolled_Jan_2026'] = summary['Enrolled_Jan_2026'].fillna(0).astype(int)
    summary['Enrolled_Feb_2026'] = summary['Enrolled_Feb_2026'].fillna(0).astype(int)
    
    summary.columns = ['Employer Name', 'Total HCUs', 'Enrolled Jan 2026', 'Enrolled Feb 2026']
    summary = summary.sort_values('Total HCUs', ascending=False)
    
    return summary

summary_df = build_summary(df)

# --- Metrics ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Employers", f"{len(summary_df):,}")
m2.metric("Total HCUs", f"{summary_df['Total HCUs'].sum():,}")
m3.metric("Enrolled Jan 2026", f"{summary_df['Enrolled Jan 2026'].sum():,}")
m4.metric("Enrolled Feb 2026", f"{summary_df['Enrolled Feb 2026'].sum():,}")

st.markdown("---")

st.dataframe(summary_df, use_container_width=True, hide_index=True)
st.caption(f"Showing {len(summary_df):,} employers")
