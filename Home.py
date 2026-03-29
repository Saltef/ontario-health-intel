import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import get_age_proxy_data

st.set_page_config(page_title="Ontario Health Intelligence", layout="wide")

# Sidebar
st.sidebar.title("Configuration")
df_burden = pd.read_csv("inputData/layer2_current_burden.csv")
condition = st.sidebar.selectbox("Select Health Condition", df_burden['condition'].unique())

# Load Proxy Data
df_mapped = get_age_proxy_data(condition)

# --- UI Layout ---
st.title(f"📍 {condition}: Regional Burden Forecast")
st.caption("Baseline: Layer 2 | Population Proxy: StatCan Table 17-10-0142")

m1, m2 = st.columns([2, 1])

with m1:
    # Bar Chart acting as the Regional Heatmap
    fig = px.bar(
        df_mapped.sort_values('predicted_admissions', ascending=False),
        x='LHIN', 
        y='predicted_admissions',
        color='predicted_cost',
        title=f"Estimated {condition} Admissions by LHIN",
        color_continuous_scale='Turbo'
    )
    st.plotly_chart(fig, use_container_width=True)

with m2:
    st.subheader("Data Insights")
    top_lhin = df_mapped.sort_values('predicted_admissions', ascending=False).iloc[0]
    st.metric("Highest Burden Region", top_lhin['LHIN'])
    st.write(f"This region accounts for {top_lhin['weight']:.1%} of the provincial age-weighted risk.")
    
    st.dataframe(df_mapped[['LHIN', 'predicted_admissions', 'predicted_cost']])
