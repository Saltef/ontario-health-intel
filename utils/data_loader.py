import pandas as pd
from pathlib import Path

# Update paths to match your fetcher's output
ROOT = Path(__file__).parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
INPUT_DIR = ROOT / "inputData"

def get_age_proxy_data(condition_name):
    # 1. Load the Burdens (Provincial Baseline)
    df_burden = pd.read_csv(INPUT_DIR / "layer2_current_burden.csv")
    cond_stats = df_burden[df_burden['condition'] == condition_name].iloc[0]
    
    # 2. Load the StatCan Processed Data
    # Created by fetch_population_by_lhin()
    df_pop = pd.read_csv(PROCESSED_DIR / "population_by_age_lhin.csv")
    
    # Filter for the most recent year in the dataset
    latest_year = df_pop['year'].max()
    df_latest = df_pop[df_pop['year'] == latest_year].copy()
    
    # 3. Create Senior (65+) and Total buckets for weighting
    # Your fetcher uses: '0–14', '15–24', '25–44', '45–64', '65–74', '75–84', '85+'
    senior_groups = ['65–74', '75–84', '85+']
    
    # Pivot age groups to columns for easier regional math
    regional_summary = df_latest.pivot_table(
        index='LHIN', 
        columns='age_group', 
        values='population', 
        agg_index=False
    ).reset_index()
    
    regional_summary['pop_65_plus'] = regional_summary[senior_groups].sum(axis=1)
    regional_summary['pop_total'] = regional_summary.iloc[:, 1:].sum(axis=1)

    # 4. Apply Proxy Weighting
    senior_weighted = ['COPD', 'Stroke', 'Heart Failure', 'Chronic Kidney Disease', 'Pneumonia']
    
    if condition_name in senior_weighted:
        # Weight by regional share of the provincial senior population
        total_seniors = regional_summary['pop_65_plus'].sum()
        regional_summary['weight'] = regional_summary['pop_65_plus'] / total_seniors
    else:
        # Weight by total population share
        regional_summary['weight'] = regional_summary['pop_total'] / regional_summary['pop_total'].sum()
    
    # 5. Project Volumes
    regional_summary['predicted_admissions'] = regional_summary['weight'] * cond_stats['admissions']
    regional_summary['predicted_cost'] = regional_summary['weight'] * cond_stats['total_cost']
    
    return regional_summary
