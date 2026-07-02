import os
import json
import glob
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load database credentials
load_dotenv()
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "medical_warehouse")

def load_data_to_pg():
    # 1. Create database connection
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    # 2. Ensure the 'raw' schema exists
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
        conn.commit()

    # 3. Read all JSON files from the data lake
    # Adjust this path if your data lake structure is different
    json_files = glob.glob('data/raw/telegram_messages/**/*.json', recursive=True)
    
    all_messages = []
    for file in json_files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_messages.extend(data)
            
    if not all_messages:
        print("No data found to load.")
        return

    # 4. Convert to DataFrame and load to PostgreSQL
    df = pd.DataFrame(all_messages)
    
    # Ensure date is parsed correctly
    df['message_date'] = pd.to_datetime(df['message_date'])
    
    print(f"Loading {len(df)} rows into raw.telegram_messages...")
    
    # Write to SQL
    df.to_sql('telegram_messages', 
              engine, 
              schema='raw', 
              if_exists='replace', # Use 'append' for incremental loads later
              index=False)
              
    print("Data successfully loaded to PostgreSQL!")

if __name__ == "__main__":
    load_data_to_pg()