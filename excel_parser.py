import pandas as pd
from datetime import datetime
import os
import re


class ExcelParser:
    def __init__(self):
        pass  # No hardcoded field mappings

    def parse_multiple(self, file_path):
        """Parse Excel file and extract ALL data as-is"""
        try:
            print(f"Parsing file: {file_path}")
            
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            print(f"Found {len(df)} rows and {len(df.columns)} columns")
            print(f"Columns: {list(df.columns)}")
            
            # Clean column names
            df.columns = [str(col).strip().upper().replace(' ', '_') for col in df.columns]
            print(f"Cleaned columns: {list(df.columns)}")
            
            records = []
            for idx, row in df.iterrows():
                record = {}
                
                # Add ALL columns from the Excel file
                for col in df.columns:
                    value = row[col]
                    if pd.isna(value):
                        record[col] = ""
                    else:
                        # Convert to string and clean
                        record[col] = str(value).strip()
                
                # Add metadata
                record['RECORD_ID'] = idx + 1
                record['EXCEL_ROW'] = idx + 2
                
                # Create display name
                record['DISPLAY_NAME'] = self._generate_display_name(record)
                
                records.append(record)
            
            print(f"Successfully parsed {len(records)} records")
            return records
            
        except Exception as e:
            print(f"Error parsing Excel file: {e}")
            raise

    def _generate_display_name(self, record):
        """Try to create a display name from available fields"""
        # Try common name fields
        name_fields = ['NAME', 'FULL_NAME', 'EMPLOYEE_NAME', 'FIRST_NAME', 'LAST_NAME', 'SURNAME', 'FULLNAME']
        
        for field in name_fields:
            if field in record and record[field]:
                return str(record[field])
        
        # Try combination of first and last name
        if 'FIRST_NAME' in record and record['FIRST_NAME'] and 'LAST_NAME' in record and record['LAST_NAME']:
            return f"{record['FIRST_NAME']} {record['LAST_NAME']}"
        
        # If no name field found, use ID or record number
        for id_field in ['ID', 'ID_NUMBER', 'EMPLOYEE_ID', 'STUDENT_ID']:
            if id_field in record and record[id_field]:
                return f"Record {record[id_field]}"
        
        return f"Record {record['RECORD_ID']}"
    
    def get_field_names(self, file_path):
        """Get all field names from Excel file"""
        try:
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            return [str(col).strip() for col in df.columns]
        except Exception as e:
            print(f"Error getting field names: {e}")
            return []