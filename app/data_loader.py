import pandas as pd
import geopandas as gpd
import streamlit as st

@st.cache_data
def load_and_clean_data():
    # Load Ministry of Finance Projections
    # Dataset: https://data.ontario.ca/dataset/population-projections
    df = pd.read_csv("data/projections/mof_projections.csv")
    
    # Melt years into a single column for the slider
    id_cols = ['CSDUID', 'CDNAME', 'Age_Group']
    year_cols = [str(year) for year in range(2024, 2052)]
    df_melted = df.melt(id_vars=id_cols, value_vars=year_cols, 
                        var_name='Year', value_name='Population')
    
    # Standardize types
    df_melted['Year'] = df_melted['Year'].astype(int)
    return df_melted

def calculate_service_pressure(df, selected_year):
    # Filter by year and apply medical intensity weights
    year_data = df[df['Year'] == selected_year]
    
    # Weights: Average annual GP visits per age group (CIHI derived)
    weights = {'0-14': 2.1, '15-64': 3.4, '65-74': 6.8, '75+': 11.2}
    
    # Pivot and calculate 'Weighted Demand'
    pivot = year_data.pivot_table(index='CSDUID', columns='Age_Group', values='Population')
    pivot['Demand_Score'] = sum(pivot[age] * weights.get(age, 1) for age in pivot.columns)
    
    return pivot.reset_index()
