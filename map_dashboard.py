import streamlit as st
import pandas as pd
import pydeck as pdk
from pathlib import Path

# --- Configuration & Paths ---
st.set_page_config(layout="wide", page_title="Ontario Health Analytics")
DATA_DIR = Path("data/processed")

# --- Load Data ---
@st.cache_data
def load_data():
    # Load the LHIN population data you just fetched
    df = pd.read_csv(DATA_DIR / "population_by_age_lhin.csv")
    # Ensure you have 'lat' and 'lon' columns for the map
    # (If your fetcher doesn't add these yet, we can join them from a geo-lookup)
    return df

df = load_data()

# --- Sidebar Filters ---
st.sidebar.title("Filters")
age_group = st.sidebar.selectbox("Select Age Group", df['age_group'].unique())
growth_scenario = st.sidebar.radio("Growth Scenario (Projections)", ["Low", "Medium", "High"])

# --- Main Dashboard ---
st.title("📍 Ontario Health Region Population Map")
st.markdown(f"Displaying data for: **{age_group}**")

# Filter data based on sidebar
filtered_df = df[df['age_group'] == age_group]

# --- Render Map ---
# Pydeck allows for 3D extrusions (showing population height)
st.pydeck_chart(pdk.Deck(
    map_style='mapbox://styles/mapbox/light-v9',
    initial_view_state=pdk.ViewState(
        latitude=43.65, longitude=-79.38, zoom=6, pitch=45
    ),
    layers=[
        pdk.Layer(
            'ColumnLayer',
            data=filtered_df,
            get_position='[lon, lat]',
            get_elevation='population',
            elevation_scale=50,
            radius=5000,
            get_fill_color=[0, 128, 255, 140],
            pickable=True,
            auto_highlight=True,
        ),
    ],
    tooltip={"text": "{lhin_name}\nPopulation: {population}"}
))

# --- Data Table ---
with st.expander("View Raw Data"):
    st.write(filtered_df)
