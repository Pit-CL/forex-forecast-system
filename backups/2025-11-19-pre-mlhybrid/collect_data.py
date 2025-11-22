#!/usr/bin/env python3
"""
Data Collection Script - Phase 1
Collects USD/CLP data from Yahoo Finance and Mindicador.cl
"""

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import os

# Project paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, 'data', 'raw')

os.makedirs(RAW_DATA_DIR, exist_ok=True)

print("=" * 80)
print("DATA COLLECTION - Phase 1")
print("=" * 80)

# 1. Yahoo Finance Data Collection
print("\n📊 Collecting Yahoo Finance data...")

tickers = {
    'USDCLP': 'CLP=X',
    'Copper': 'HG=F',
    'Oil': 'CL=F',
    'DXY': 'DX-Y.NYB',
    'SP500': '^GSPC',
    'VIX': '^VIX'
}

end_date = datetime.now()
# Get maximum historical data available (Yahoo Finance has ~20 years)
# Using 15 years to ensure data quality
start_date = end_date - timedelta(days=5475)  # 15 years of data

yahoo_data = {}

for name, ticker in tickers.items():
    try:
        print(f"  Fetching {name} ({ticker})...")
        df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
        if not df.empty:
            if 'Close' in df.columns:
                yahoo_data[name] = df['Close']
            else:
                yahoo_data[name] = df.iloc[:, 0]
            print(f"    ✅ {name}: {len(df)} days")
        else:
            print(f"    ❌ {name}: No data")
    except Exception as e:
        print(f"    ❌ {name}: {e}")

# Combine Yahoo data
if yahoo_data:
    yahoo_df = pd.concat(yahoo_data, axis=1)
    yahoo_df.columns = list(yahoo_data.keys())
    yahoo_df.index.name = 'Date'

    # Save to CSV
    yahoo_path = os.path.join(RAW_DATA_DIR, 'yahoo_finance_data.csv')
    yahoo_df.to_csv(yahoo_path)
    print(f"\n✅ Yahoo Finance data saved: {yahoo_path}")
    print(f"   Shape: {yahoo_df.shape}")

# 2. Mindicador.cl Data Collection
print("\n📊 Collecting Mindicador.cl data...")

indicators = ['dolar', 'uf', 'euro']
mindicador_data = {}

for indicator in indicators:
    try:
        print(f"  Fetching {indicator}...")
        url = f"https://mindicador.cl/api/{indicator}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'serie' in data:
                df = pd.DataFrame(data['serie'])
                df['fecha'] = pd.to_datetime(df['fecha'])
                df = df.set_index('fecha').sort_index()
                mindicador_data[indicator] = df['valor']
                print(f"    ✅ {indicator}: {len(df)} days")
        else:
            print(f"    ❌ {indicator}: HTTP {response.status_code}")
    except Exception as e:
        print(f"    ❌ {indicator}: {e}")

# Combine Mindicador data
if mindicador_data:
    mindicador_df = pd.DataFrame(mindicador_data)
    mindicador_df.columns = ['usdclp', 'uf', 'eurclp']
    mindicador_df.index.name = 'date'

    # Save to CSV
    mindicador_path = os.path.join(RAW_DATA_DIR, 'mindicador_data.csv')
    mindicador_df.to_csv(mindicador_path)
    print(f"\n✅ Mindicador data saved: {mindicador_path}")
    print(f"   Shape: {mindicador_df.shape}")

print("\n" + "=" * 80)
print("✅ DATA COLLECTION COMPLETE")
print("=" * 80)
