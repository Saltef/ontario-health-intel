import io, json, zipfile, logging, requests
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Table 17-10-0157 is the newest (2026 release) for 2023 health boundaries
TABLE_ID = "17100157"

# Standard LHIN/Health Region Mapping
LHIN_MAP = {
    "3540": "Erie St. Clair", "3530": "South West", "3520": "Waterloo Wellington",
    "3510": "HNHB", "3560": "Central West", "3550": "Mississauga Halton",
    "3595": "Toronto Central", "3570": "Central", "3580": "Central East",
    "3500": "South East", "3615": "Champlain", "3575": "North Simcoe Muskoka",
    "3590": "North East", "3610": "North West"
}

# Target age groups for your healthcare burden models
AGE_MAP = {
    "0 to 4 years": "0–14", "5 to 9 years": "0–14", "10 to 14 years": "0–14",
    "15 to 19 years": "15–24", "20 to 24 years": "15–24",
    "65 to 69 years": "65–74", "70 to 74 years": "65–74",
    "75 to 79 years": "75–84", "80 to 84 years": "75–84",
    "85 years and over": "85+"
}

def fetch_lhin_data():
    log.info(f"Downloading latest estimates from Table {TABLE_ID}...")
    api_url = f"https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/{TABLE_ID}/en"
    
    try:
        # 1. API Call & Unzip
        download_url = requests.get(api_url).json()['object']
        r = requests.get(download_url)
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            csv_name = [f for f in z.namelist() if f.endswith('.csv') and 'MetaData' not in f][0]
            df = pd.read_csv(z.open(csv_name), low_memory=False)
        
        # 2. Force headers to uppercase for consistency
        df.columns = [c.strip().upper() for c in df.columns]
        
        # 3. Dynamic Column Detection
        # Identify Age column by checking unique values rather than header string
        age_col = None
        for col in df.columns:
            if df[col].astype(str).str.contains('year', case=False).any():
                age_col = col
                break
        
        if not age_col:
            raise ValueError("Could not find a column containing age strings (e.g., 'years').")

        # 4. Processing
        df['year'] = pd.to_numeric(df['REF_DATE'].astype(str).str[:4])
        df['HR_CODE'] = df['DGUID'].astype(str).str[-4:]
        df['LHIN'] = df['HR_CODE'].map(LHIN_MAP)
        df['mapped_age'] = df[age_col].map(AGE_MAP)
        
        # Filter for only relevant LHINs and Age Groups
        df = df[df['LHIN'].notna() & df['mapped_age'].notna()]
        
        # Aggregate across Sex/Gender (Value is typically the 'VALUE' column)
        final = df.groupby(['LHIN', 'year', 'mapped_age'], as_index=False)['VALUE'].sum()
        final.columns = ['LHIN', 'year', 'age_group', 'population']
        
        # 5. Export
        save_path = OUT_DIR / "population_by_age_lhin.csv"
        final.to_csv(save_path, index=False)
        log.info(f"✅ SUCCESS: {len(final)} records saved to {save_path}")

    except Exception as e:
        log.error(f"Fetch Failed: {str(e)}")

if __name__ == "__main__":
    fetch_lhin_data()
