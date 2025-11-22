#!/usr/bin/env python3
"""
Clean Historical Data Script
ACTION 1 - Remove corrupt records and handle null values

Purpose: Remove corrupt data records identified in analysis
Expected impact: Clean data foundation for accurate model training
"""

import pandas as pd
import sys
import os
from datetime import datetime
import shutil

# Paths
DATA_FILE = '/opt/forex-forecast-system/data/raw/yahoo_finance_data.csv'
BACKUP_DIR = '/opt/forex-forecast-system/backups'

def create_backup():
    """Create timestamped backup before cleaning"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f'{BACKUP_DIR}/yahoo_finance_data_pre_clean_{timestamp}.csv'
    
    print(f'📦 Creating backup: {backup_path}')
    shutil.copy2(DATA_FILE, backup_path)
    print(f'✅ Backup created successfully')
    return backup_path

def load_data():
    """Load historical data"""
    print(f'📖 Loading data from: {DATA_FILE}')
    df = pd.read_csv(DATA_FILE)
    print(f'✅ Loaded {len(df)} records')
    return df

def identify_issues(df):
    """Identify corrupt records and null values"""
    print('\n🔍 Identifying data issues...')
    
    # Issue 1: USDCLP < 100 (should be ~500-1000)
    corrupt = df[df['USDCLP'] < 100]
    print(f'\n⚠️  Found {len(corrupt)} records with USDCLP < 100:')
    if len(corrupt) > 0:
        print(corrupt[['Date', 'USDCLP']].to_string(index=False))
    
    # Issue 2: Null values
    null_usdclp = df[df['USDCLP'].isnull()]
    print(f'\n⚠️  Found {len(null_usdclp)} records with null USDCLP:')
    if len(null_usdclp) > 0:
        print(null_usdclp[['Date', 'USDCLP']].to_string(index=False))
    
    total_issues = len(corrupt) + len(null_usdclp)
    print(f'\n📊 Total problematic records: {total_issues}')
    
    return total_issues

def clean_data(df):
    """Remove corrupt records and null values"""
    print('\n🧹 Cleaning data...')
    
    original_count = len(df)
    
    # Remove records with USDCLP < 100
    df_clean = df[df['USDCLP'] >= 100].copy()
    corrupt_removed = original_count - len(df_clean)
    
    # Remove records with null USDCLP
    df_clean = df_clean[df_clean['USDCLP'].notna()].copy()
    null_removed = len(df) - corrupt_removed - len(df_clean)
    
    total_removed = original_count - len(df_clean)
    
    print(f'✅ Removed {corrupt_removed} corrupt records (USDCLP < 100)')
    print(f'✅ Removed {null_removed} null records')
    print(f'✅ Total removed: {total_removed}')
    print(f'✅ Remaining records: {len(df_clean)}')
    
    return df_clean

def validate_data(df):
    """Validate cleaned data"""
    print('\n✔️  Validating cleaned data...')
    
    # Check USDCLP range
    min_val = df['USDCLP'].min()
    max_val = df['USDCLP'].max()
    mean_val = df['USDCLP'].mean()
    
    print(f'USDCLP range: {min_val:.2f} - {max_val:.2f} (mean: {mean_val:.2f})')
    
    # Check for any remaining corrupt records
    corrupt = df[df['USDCLP'] < 100]
    if len(corrupt) > 0:
        print(f'⚠️  WARNING: Still {len(corrupt)} corrupt records!')
        return False
    
    # Check for null values
    null_count = df['USDCLP'].isnull().sum()
    if null_count > 0:
        print(f'⚠️  WARNING: Still {null_count} null values!')
        return False
    
    # Check reasonable range (historical USD/CLP is ~400-1200)
    if min_val < 400 or max_val > 1300:
        print(f'⚠️  WARNING: Values outside expected range (400-1300)')
        return False
    
    print('✅ Data validation passed')
    print(f'✅ No corrupt records (all USDCLP >= 100)')
    print(f'✅ No null values')
    print(f'✅ All values in reasonable range')
    
    return True

def save_cleaned_data(df):
    """Save cleaned data back to original file"""
    print(f'\n💾 Saving cleaned data to: {DATA_FILE}')
    df.to_csv(DATA_FILE, index=False)
    print('✅ Data saved successfully')

def main():
    print('=' * 60)
    print('ACTION 1: Clean Historical Data')
    print('=' * 60)
    
    try:
        # Step 1: Create backup
        backup_path = create_backup()
        
        # Step 2: Load data
        df = load_data()
        
        # Step 3: Identify issues
        total_issues = identify_issues(df)
        
        if total_issues == 0:
            print('\n✅ No issues found - data is already clean!')
            return 0
        
        # Step 4: Clean data
        df_clean = clean_data(df)
        
        # Step 5: Validate cleaned data
        if not validate_data(df_clean):
            print('\n❌ Validation failed - NOT saving changes')
            print(f'Backup available at: {backup_path}')
            return 1
        
        # Step 6: Save cleaned data
        save_cleaned_data(df_clean)
        
        print('\n' + '=' * 60)
        print('✅ ACTION 1 COMPLETED SUCCESSFULLY')
        print('=' * 60)
        print(f'Backup location: {backup_path}')
        print(f'Removed {total_issues} problematic records')
        print(f'Clean data: {len(df_clean)} records')
        print('=' * 60)
        
        return 0
        
    except Exception as e:
        print(f'\n❌ ERROR: {str(e)}')
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
