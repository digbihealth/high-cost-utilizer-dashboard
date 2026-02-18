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
    sheet = client.open_by_key("1g9bHdsz-jG6Bp14JT2U2HZcFe6GA3b3nm80aemkGvH0")

    # Load all HCUs (non-enrolled)
    hcu_data = sheet.worksheet("High Cost Utilizer").get_all_records()
    hcu_df = pd.DataFrame(hcu_data)

    # Load enrolled HCUs
    enrolled_data = sheet.worksheet("HCU Enrolled Data").get_all_records()
    enrolled_df = pd.DataFrame(enrolled_data)

    # Parse enrollment date
    enrolled_df['enrollmentDate'] = pd.to_datetime(enrolled_df['enrollmentDate'], errors='coerce', utc=True)

    return hcu_df, enrolled_df

hcu_df, enrolled_df = load_data()

# --- Build summary table ---
def build_summary(hcu_df, enrolled_df):
    # Total HCUs per employer (from High Cost Utilizer tab)
    total = hcu_df.groupby('employerName').agg(
        Total_HCUs=('userId', 'count')
    ).reset_index()

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

    summary = total.merge(jan, on='employerName', how='left')
    summary = summary.merge(feb, on='employerName', how='left')

    summary['Enrolled_Jan_2026'] = summary['Enrolled_Jan_2026'].fillna(0).astype(int)
    summary['Enrolled_Feb_2026'] = summary['Enrolled_Feb_2026'].fillna(0).astype(int)

    summary.columns = ['Employer Name', 'Total HCUs', 'Enrolled Jan 2026', 'Enrolled Feb 2026']
    summary = summary.sort_values('Total HCUs', ascending=False)

    return summary

summary_df = build_summary(hcu_df, enrolled_df)

# --- Metrics ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Employers", f"{len(summary_df):,}")
m2.metric("Total HCUs", f"{summary_df['Total HCUs'].sum():,}")
m3.metric("Enrolled Jan 2026", f"{summary_df['Enrolled Jan 2026'].sum():,}")
m4.metric("Enrolled Feb 2026", f"{summary_df['Enrolled Feb 2026'].sum():,}")

st.markdown("---")

st.dataframe(summary_df, use_container_width=True, hide_index=True)
st.caption(f"Showing {len(summary_df):,} employers")
