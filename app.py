import streamlit as st
import pandas as pd
import gspread
import numpy as np
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

    hcu_df = pd.DataFrame(sheet.worksheet("High Cost Utilizer").get_all_records())
    enrolled_df = pd.DataFrame(sheet.worksheet("HCU Enrolled Data").get_all_records())

    # Parse enrollmentDateFormatted directly (e.g. "28 March 2025", "7 February 2024")
    enrolled_df['parsed_date'] = pd.to_datetime(enrolled_df['enrollmentDateFormatted'], errors='coerce')

    def parse_total_cost(val):
        try:
            d = json.loads(str(val).replace("'", '"'))
            return float(d.get('2024', 0) or 0) + float(d.get('2025', 0) or 0)
        except:
            return 0.0

    hcu_df['total_claim_cost'] = hcu_df['claim_cost'].apply(parse_total_cost)
    enrolled_df['total_claim_cost'] = enrolled_df['claim_cost'].apply(parse_total_cost)

    return hcu_df, enrolled_df

hcu_df, enrolled_df = load_data()

def build_summary(hcu_df, enrolled_df):
    total = hcu_df.groupby('employerName').agg(
        Total_HCUs=('userId', 'count'),
        Total_Claim_Cost=('total_claim_cost', 'sum')
    ).reset_index()

    total['2026 HCU Enrollment Target'] = np.ceil(total['Total_HCUs'] * 0.30).astype(int)

    enrolled_2026 = enrolled_df[enrolled_df['parsed_date'].dt.year == 2026]

    total_2026 = enrolled_2026.groupby('employerName').agg(
        Total_Enrolled_2026=('userId', 'count'),
        Enrolled_Claim_Cost=('total_claim_cost', 'sum')
    ).reset_index()

    summary = total.merge(total_2026, on='employerName', how='left')

    summary['Total_Enrolled_2026'] = summary['Total_Enrolled_2026'].fillna(0).astype(int)
    summary['Enrolled_Claim_Cost'] = summary['Enrolled_Claim_Cost'].fillna(0)
    summary['Enrolled_Pct'] = (summary['Total_Enrolled_2026'] / summary['Total_HCUs'] * 100).round(1)
    summary['Enrolled_Claim_Cost_Pct'] = (summary['Enrolled_Claim_Cost'] / summary['Total_Claim_Cost'] * 100).round(1)

    summary = summary[[
        'employerName', 'Total_HCUs', '2026 HCU Enrollment Target',
        'Total_Enrolled_2026', 'Enrolled_Pct',
        'Total_Claim_Cost', 'Enrolled_Claim_Cost', 'Enrolled_Claim_Cost_Pct'
    ]]

    summary.columns = [
        'Employer Name', 'Total HCUs', '2026 HCU Enrollment Target',
        'Total Enrolled 2026', 'Total Enrolled 2026 %',
        'Total Claim Cost', 'Enrolled Claim Cost', 'Enrolled Claim Cost %'
    ]
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
m3.metric("2026 HCU Enrollment Target (30%)", f"{summary_df['2026 HCU Enrollment Target'].sum():,}")
m4.metric("HCUs Enrolled 2026", f"{total_enrolled_sum:,}")
m5.metric("HCUs Enrolled 2026 %", f"{enrolled_pct}%")

st.markdown("---")

# --- Format display ---
display_df = summary_df.copy()
for col in ['Total HCUs', '2026 HCU Enrollment Target', 'Total Enrolled 2026']:
    display_df[col] = display_df[col].apply(lambda x: f"{x:,}")
display_df['Total Enrolled 2026 %'] = summary_df['Total Enrolled 2026 %'].apply(lambda x: f"{x}%")
display_df['Total Claim Cost'] = summary_df['Total Claim Cost'].apply(lambda x: f"${x:,.0f}")
display_df['Enrolled Claim Cost'] = summary_df['Enrolled Claim Cost'].apply(lambda x: f"${x:,.0f}")
display_df['Enrolled Claim Cost %'] = summary_df['Enrolled Claim Cost %'].apply(lambda x: f"{x}%")

# --- Totals row ---
total_hcus = summary_df['Total HCUs'].sum()
total_enrolled = summary_df['Total Enrolled 2026'].sum()
total_claim = summary_df['Total Claim Cost'].sum()
enrolled_claim = summary_df['Enrolled Claim Cost'].sum()
totals = {
    'Employer Name': 'TOTAL',
    'Total HCUs': f"{total_hcus:,}",
    '2026 HCU Enrollment Target': f"{summary_df['2026 HCU Enrollment Target'].sum():,}",
    'Total Enrolled 2026': f"{total_enrolled:,}",
    'Total Enrolled 2026 %': f"{round(total_enrolled / total_hcus * 100, 1)}%",
    'Total Claim Cost': f"${total_claim:,.0f}",
    'Enrolled Claim Cost': f"${enrolled_claim:,.0f}",
    'Enrolled Claim Cost %': f"{round(enrolled_claim / total_claim * 100, 1)}%"
}
display_df = pd.concat([display_df, pd.DataFrame([totals])], ignore_index=True)

st.dataframe(display_df, use_container_width=True, hide_index=True)
st.caption(f"Showing {len(summary_df):,} employers")
