"""Test warehouse data structure"""
import pandas as pd
from pathlib import Path

warehouse_path = Path("/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/data/warehouse")
df = pd.read_parquet(warehouse_path / "usdclp_daily.parquet")

print("Columns:", df.columns.tolist())
print("Shape:", df.shape)
print("\nFirst 5 rows:")
print(df.head())
print("\nData types:")
print(df.dtypes)