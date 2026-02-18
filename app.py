import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="High Cost Utilizer Dashboard", page_icon="💊", layout="wide")

st.title("💊 High Cost Utilizer Dashboard")

# --- Load Data ---
@st.cache_data(ttl=300)
def load_data():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    
    sheet = client.open("Enrollment campaigns tracking").worksheet("High Cost Utilizer")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Parse claim_cost JSON into separate columns
    def parse_cost(val, year):
        try:
            d = json.loads(str(val).replace("'", '"'))
            return float(d.get(str(year), 0))
        except:
            return 0.0
    
    df['Claim Cost 2024'] = df['claim_cost'].apply(lambda x: parse_cost(x, 2024))
    df['Claim Cost 2025'] = df['claim_cost'].apply(lambda x: parse_cost(x, 2025))
    df['Total Claim Cost'] = df['Claim Cost 2024'] + df['Claim Cost 2025']
    
    return df

df = load_data()

# --- Filters ---
col1, col2, col3 = st.columns(3)

with col1:
    employers = ['All'] + sorted(df['employerName'].dropna().unique().tolist())
    selected_employer = st.selectbox('Filter by Employer', employers)

with col2:
    statuses = ['All'] + sorted(df['enrollmentStatus'].dropna().unique().tolist())
    selected_status = st.selectbox('Filter by Enrollment Status', statuses)

with col3:
    search = st.text_input('Search by Name or Email')

# Sort
sort_by = st.selectbox('Sort by', ['Total Claim Cost', 'Claim Cost 2025', 'Claim Cost 2024'])

# --- Apply Filters ---
filtered = df.copy()

if selected_employer != 'All':
    filtered = filtered[filtered['employerName'] == selected_employer]

if selected_status != 'All':
    filtered = filtered[filtered['enrollmentStatus'] == selected_status]

if search:
    search_lower = search.lower()
    filtered = filtered[
        filtered['email'].str.lower().str.contains(search_lower, na=False) |
        filtered['firstName'].str.lower().str.contains(search_lower, na=False) |
        filtered['lastName'].str.lower().str.contains(search_lower, na=False)
    ]

filtered = filtered.sort_values(sort_by, ascending=False)

# --- Summary Metrics ---
st.markdown("---")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Users", f"{len(filtered):,}")
m2.metric("Avg Claim Cost 2024", f"${filtered['Claim Cost 2024'].mean():,.0f}")
m3.metric("Avg Claim Cost 2025", f"${filtered['Claim Cost 2025'].mean():,.0f}")
m4.metric("Avg Total Claim Cost", f"${filtered['Total Claim Cost'].mean():,.0f}")

# --- Table ---
st.markdown("---")
display_cols = ['userId', 'email', 'firstName', 'lastName', 'employerName', 
                'companyName', 'enrollmentStatus', 'Claim Cost 2024', 
                'Claim Cost 2025', 'Total Claim Cost']

display_df = filtered[display_cols].copy()
display_df['Claim Cost 2024'] = display_df['Claim Cost 2024'].apply(lambda x: f"${x:,.2f}" if x > 0 else '-')
display_df['Claim Cost 2025'] = display_df['Claim Cost 2025'].apply(lambda x: f"${x:,.2f}" if x > 0 else '-')
display_df['Total Claim Cost'] = display_df['Total Claim Cost'].apply(lambda x: f"${x:,.2f}")

st.dataframe(display_df, use_container_width=True, hide_index=True)
st.caption(f"Showing {len(filtered):,} of {len(df):,} users")
```

And the `requirements.txt`:
```
streamlit
pandas
gspread
google-auth
