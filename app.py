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

    # Try parsing from Unix ms first, fall back to formatted string
    enrolled_df['parsed_date'] = pd.to_datetime(enrolled_df['enrollmentDate'], unit='ms', errors='coerce')

    mask = enrolled_df['parsed_date'].isna()
    if mask.any() and 'enrollmentDateFormatted' in enrolled_df.columns:
        enrolled_df.loc[mask, 'parsed_date'] = pd.to_datetime(
            enrolled_df.loc[mask, 'enrollmentDateFormatted'], format='%d/%m/%y', errors='coerce'
        )

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

    # Percentage column
    summary['Enrolled_Pct'] = (summary['Total_Enrolled_2026'] / summary['Total_HCUs'] * 100).round(1)

    summary.columns = ['Employer Name', 'Total HCUs', '2026 HCU Enrollment Target',
                       'Total Enrolled 2026', 'Enrolled Jan 2026', 'Enrolled Feb 2026',
                       'Total Enrolled 2026 %']
    summary = summary.sort_values('Total HCUs', ascending=False).reset_index(drop=True)

    return summary

summary_df = build_summary(hcu_df, enrolled_df)

# --- Metrics ---
total_hcus_sum = summary_df['Total HCUs'].sum()
total_enrolled_sum = summary_df['Total Enrolled 2026'].sum()
enrolled_pct = round(total_enrolled_sum / total_hcus_sum * 100, 1) if total_hcus_sum > 0 else 0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Employers", f"{len(summary_df):,}")
m2.metric("Total HCUs", f"{total_hcus_sum:,}")
m3.metric("2026 HCU Enrollment Target (40%)", f"{summary_df['2026 HCU Enrollment Target'].sum():,}")
m4.metric("HCUs Enrolled 2026", f"{total_enrolled_sum:,}")
m5.metric("HCUs Enrolled 2026 %", f"{enrolled_pct}%")

st.markdown("---")

# --- Format display ---
display_df = summary_df.copy()
for col in ['Total HCUs', '2026 HCU Enrollment Target', 'Total Enrolled 2026', 'Enrolled Jan 2026', 'Enrolled Feb 2026']:
    display_df[col] = display_df[col].apply(lambda x: f"{x:,}")
display_df['Total Enrolled 2026 %'] = display_df['Total Enrolled 2026 %'].apply(lambda x: f"{x}%")

# --- Totals row ---
total_hcus = summary_df['Total HCUs'].sum()
total_enrolled = summary_df['Total Enrolled 2026'].sum()
totals = {
    'Employer Name': 'TOTAL',
    'Total HCUs': f"{total_hcus:,}",
    '2026 HCU Enrollment Target': f"{summary_df['2026 HCU Enrollment Target'].sum():,}",
    'Total Enrolled 2026': f"{total_enrolled:,}",
    'Enrolled Jan 2026': f"{summary_df['Enrolled Jan 2026'].sum():,}",
    'Enrolled Feb 2026': f"{summary_df['Enrolled Feb 2026'].sum():,}",
    'Total Enrolled 2026 %': f"{round(total_enrolled / total_hcus * 100, 1)}%"
}
display_df = pd.concat([display_df, pd.DataFrame([totals])], ignore_index=True)

st.dataframe(display_df, use_container_width=True, hide_index=True)
st.caption(f"Showing {len(summary_df):,} employers")
