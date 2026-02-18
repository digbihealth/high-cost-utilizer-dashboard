import streamlit as st
import pandas as pd
import gspread
import numpy as np
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

    hcu_df = pd.DataFrame(sheet.worksheet("High Cost Utilizer").get_all_records())
    enrolled_df = pd.DataFrame(sheet.worksheet("HCU Enrolled Data").get_all_records())

    # Parse enrollmentDateFormatted (format: DD/MM/YY)
    enrolled_df['parsed_date'] = pd.to_datetime(enrolled_df['enrollmentDateFormatted'], format='%d/%m/%y', errors='coerce')

    return hcu_df, enrolled_df

hcu_df, enrolled_df = load_data()

def build_summary(hcu_df, enrolled_df):
    total = hcu_df.groupby('employerName').agg(
        Total_HCUs=('userId', 'count')
    ).reset_index()

    total['2026 HCU Enrollment Target'] = np.ceil(total['Total_HCUs'] * 0.40).astype(int)

    # Total enrolled in 2026
    total_2026 = enrolled_df[
        enrolled_df['parsed_date'].dt.year == 2026
    ].groupby('employerName').size().reset_index(name='Total_Enrolled_2026')

    # Enrolled in Jan 2026
    jan = enrolled_df[
        (enrolled_df['parsed_date'].dt.year == 2026) &
        (enrolled_df['parsed_date'].dt.month == 1)
    ].groupby('employerName').size().reset_index(name='Enrolled_Jan_2026')

    # Enrolled in Feb 2026
    feb = enrolled_df[
        (enrolled_df['parsed_date'].dt.year == 2026) &
        (enrolled_df['parsed_date'].dt.month == 2)
    ].groupby('employerName').size().reset_index(name='Enrolled_Feb_2026')

    summary = total.merge(total_2026, on='employerName', how='left')
    summary = summary.merge(jan, on='employerName', how='left')
    summary = summary.merge(feb, on='employerName', how='left')

    summary['Total_Enrolled_2026'] = summary['Total_Enrolled_2026'].fillna(0).astype(int)
    summary['Enrolled_Jan_2026'] = summary['Enrolled_Jan_2026'].fillna(0).astype(int)
    summary['Enrolled_Feb_2026'] = summary['Enrolled_Feb_2026'].fillna(0).astype(int)

    summary.columns = ['Employer Name', 'Total HCUs', '2026 HCU Enrollment Target',
                       'Total Enrolled 2026', 'Enrolled Jan 2026', 'Enrolled Feb 2026']
    summary = summary.sort_values('Total HCUs', ascending=False).reset_index(drop=True)

    return summary

summary_df = build_summary(hcu_df, enrolled_df)

# --- Metrics ---
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Employers", f"{len(summary_df):,}")
m2.metric("Total HCUs", f"{summary_df['Total HCUs'].sum():,}")
m3.metric("2026 HCU Enrollment Target (40%)", f"{summary_df['2026 HCU Enrollment Target'].sum():,}")
m4.metric("Enrolled Jan 2026", f"{summary_df['Enrolled Jan 2026'].sum():,}")
m5.metric("Enrolled Feb 2026", f"{summary_df['Enrolled Feb 2026'].sum():,}")

st.markdown("---")

# --- Format display with commas ---
display_df = summary_df.copy()
for col in ['Total HCUs', '2026 HCU Enrollment Target', 'Total Enrolled 2026', 'Enrolled Jan 2026', 'Enrolled Feb 2026']:
    display_df[col] = display_df[col].apply(lambda x: f"{x:,}")

# --- Totals row pinned at bottom ---
totals = {
    'Employer Name': 'TOTAL',
    'Total HCUs': f"{summary_df['Total HCUs'].sum():,}",
    '2026 HCU Enrollment Target': f"{summary_df['2026 HCU Enrollment Target'].sum():,}",
    'Total Enrolled 2026': f"{summary_df['Total Enrolled 2026'].sum():,}",
    'Enrolled Jan 2026': f"{summary_df['Enrolled Jan 2026'].sum():,}",
    'Enrolled Feb 2026': f"{summary_df['Enrolled Feb 2026'].sum():,}"
}
display_df = pd.concat([display_df, pd.DataFrame([totals])], ignore_index=True)

st.dataframe(display_df, use_container_width=True, hide_index=True)
st.caption(f"Showing {len(summary_df):,} employers")
