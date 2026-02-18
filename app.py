import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="High Cost Utilizer Dashboard", page_icon="💊", layout="wide")

st.title("💊 High Cost Utilizer Dashboard")

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=300)
def load_data():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1g9bHdsz-jG6Bp14JT2U2HZcFe6GA3b3nm80aemkGvH0")

    # Load all HCUs
    hcu_df = pd.DataFrame(sheet.worksheet("High Cost Utilizer").get_all_records())

    # Load enrolled HCUs
    enrolled_df = pd.DataFrame(sheet.worksheet("HCU Enrolled Data").get_all_records())

    # Log raw enrollment dates for debugging
    if not enrolled_df.empty:
        st.write("Sample enrollment dates:", enrolled_df['enrollmentDate'].head(5).tolist())

    # Try parsing enrollment date flexibly
    enrolled_df['enrollmentDate'] = pd.to_datetime(enrolled_df['enrollmentDate'], errors='coerce', dayfirst=True)

    return hcu_df, enrolled_df

hcu_df, enrolled_df = load_data()

def build_summary(hcu_df, enrolled_df):
    # Total HCUs per employer
    total = hcu_df.groupby('employerName').agg(
        Total_HCUs=('userId', 'count')
    ).reset_index()

    total['HCU Enrollment Target'] = (total['Total_HCUs'] * 0.05).ceil().astype(int)

    # Enrolled in Jan 2026
    jan = enrolled_df[
        (enrolled_df['enrollmentDate'].dt.year == 2026) &
        (enrolled_df['enrollmentDate'].dt.month == 1)
    ].groupby('employerName').size().reset_index(name='Enrolled_Jan_2026')

    # Enrolled in Feb 2026
    feb = enrolled_df[
        (enrolled_df['enrollmentDate'].dt.year == 2026) &
        (enrolled_df['enrollmentDate'].dt.month == 2)
    ].groupby('employerName').size().reset_index(name='Enrolled_Feb_2026')

    # Total enrolled in 2026
    total_2026 = enrolled_df[
        enrolled_df['enrollmentDate'].dt.year == 2026
    ].groupby('employerName').size().reset_index(name='Total_Enrolled_2026')

    summary = total.merge(jan, on='employerName', how='left')
    summary = summary.merge(feb, on='employerName', how='left')
    summary = summary.merge(total_2026, on='employerName', how='left')

    summary['Enrolled_Jan_2026'] = summary['Enrolled_Jan_2026'].fillna(0).astype(int)
    summary['Enrolled_Feb_2026'] = summary['Enrolled_Feb_2026'].fillna(0).astype(int)
    summary['Total_Enrolled_2026'] = summary['Total_Enrolled_2026'].fillna(0).astype(int)

    summary.columns = ['Employer Name', 'Total HCUs', 'HCU Enrollment Target', 
                       'Enrolled Jan 2026', 'Enrolled Feb 2026', 'Total Enrolled 2026']
    summary = summary.sort_values('Total HCUs', ascending=False)

    return summary

summary_df = build_summary(hcu_df, enrolled_df)

# --- Metrics ---
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Employers", f"{len(summary_df):,}")
m2.metric("Total HCUs", f"{summary_df['Total HCUs'].sum():,}")
m3.metric("HCU Enrollment Target", f"{summary_df['HCU Enrollment Target'].sum():,}")
m4.metric("Enrolled Jan 2026", f"{summary_df['Enrolled Jan 2026'].sum():,}")
m5.metric("Enrolled Feb 2026", f"{summary_df['Enrolled Feb 2026'].sum():,}")

st.markdown("---")

st.dataframe(summary_df, use_container_width=True, hide_index=True)
st.caption(f"Showing {len(summary_df):,} employers")
