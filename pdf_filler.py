import pymupdf as fitz
from datetime import datetime
import re
import os


class PDFFiller:
    def __init__(self):
        pass  # No predefined patterns

    def fill_pdf(self, template_path, data, output_path):
        """Fill PDF form fields with data using flexible matching"""
        try:
            print(f"\n=== Starting PDF Fill ===")
            print(f"Template: {template_path}")
            print(f"Output: {output_path}")
            print(f"Data fields available: {list(data.keys())}")
            
            pdf_document = fitz.open(template_path)
            
            # Get all form field names from PDF
            form_fields = self._get_form_field_names(pdf_document)
            print(f"Found {len(form_fields)} form fields in PDF")
            
            if form_fields:
                print("\nTrying to fill form fields...")
                success = self._fill_form_fields_flexible(pdf_document, data, form_fields)
                if not success:
                    print("Form field filling had issues, adding text overlay")
                    self._overlay_text_simple(pdf_document, data)
            else:
                print("\nNo interactive form fields found, using text overlay")
                self._overlay_text_simple(pdf_document, data)
            
            # Save the filled PDF
            pdf_document.save(output_path)
            pdf_document.close()
            
            print(f"\n✅ PDF saved successfully: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"\n❌ Error in fill_pdf: {str(e)}")
            raise Exception(f"Error filling PDF: {str(e)}")

    def _get_form_field_names(self, pdf_document):
        """Extract all form field names from PDF"""
        field_names = []
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            widgets = page.widgets()
            
            if widgets:
                for widget in widgets:
                    if widget.field_name:
                        field_names.append(widget.field_name)
        
        return field_names

    def _fill_form_fields_flexible(self, pdf_document, data, form_fields):
        """Flexible form field filling - tries multiple matching strategies"""
        success_count = 0
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            widgets = page.widgets()
            
            if widgets:
                for widget in widgets:
                    if not widget.field_name:
                        continue
                    
                    field_name = widget.field_name
                    value = self._find_best_match(field_name, data)
                    
                    if value:
                        try:
                            # Try to set the field value
                            widget.field_value = str(value)
                            widget.update()
                            success_count += 1
                            print(f"  ✓ Filled '{field_name}' with '{value}'")
                        except Exception as e:
                            print(f"  ✗ Could not fill field '{field_name}': {str(e)}")
        
        print(f"\nFilled {success_count} out of {len(form_fields)} fields")
        return success_count > 0

    def _find_best_match(self, pdf_field_name, data):
        """Find the best matching data for a PDF field"""
        pdf_field_lower = pdf_field_name.lower().strip()
        
        print(f"\nLooking for match for PDF field: '{pdf_field_name}'")
        
        # Strategy 1: Exact match (case-insensitive)
        for data_key, data_value in data.items():
            if data_key.lower() == pdf_field_lower:
                print(f"  Found exact match: {data_key}")
                return str(data_value) if data_value else ""
        
        # Strategy 2: Remove special characters and spaces
        pdf_field_clean = re.sub(r'[^a-z0-9]', '', pdf_field_lower)
        for data_key, data_value in data.items():
            data_key_clean = re.sub(r'[^a-z0-9]', '', data_key.lower())
            if pdf_field_clean == data_key_clean:
                print(f"  Found clean match: {data_key}")
                return str(data_value) if data_value else ""
        
        # Strategy 3: Contains match
        for data_key, data_value in data.items():
            data_key_lower = data_key.lower()
            if pdf_field_lower in data_key_lower or data_key_lower in pdf_field_lower:
                print(f"  Found contains match: {data_key}")
                return str(data_value) if data_value else ""
        
        # Strategy 4: Word-based matching
        pdf_words = set(pdf_field_lower.replace('_', ' ').split())
        for data_key, data_value in data.items():
            data_words = set(data_key.lower().replace('_', ' ').split())
            if pdf_words & data_words:  # If they share any words
                print(f"  Found word match: {data_key}")
                return str(data_value) if data_value else ""
        
        print(f"  No match found for '{pdf_field_name}'")
        return ""

    def _overlay_text_simple(self, pdf_document, data):
        """Simple text overlay - shows all data at the top of the PDF"""
        print("\nAdding text overlay with all data:")
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Create a text block with all data
            y_position = 50
            x_position = 50
            
            # Add title
            title = "=== FILLED DATA FROM EXCEL ==="
            rect = fitz.Rect(x_position, y_position, x_position + 400, y_position + 20)
            annot = page.add_freetext_annot(rect, title)
            annot.set_border(width=0)
            annot.set_fontsize(12)
            
            y_position += 30
            
            # Add each data field
            for key, value in data.items():
                if key not in ['RECORD_ID', 'EXCEL_ROW', 'DISPLAY_NAME'] and value:
                    text = f"{key}: {value}"
                    print(f"  Adding: {text}")
                    
                    if y_position > 700:  # Start new column
                        y_position = 50
                        x_position += 250
                    
                    rect = fitz.Rect(x_position, y_position, x_position + 400, y_position + 20)
                    annot = page.add_freetext_annot(rect, text)
                    annot.set_border(width=0)
                    annot.set_fontsize(10)
                    
                    y_position += 25

    def extract_form_fields(self, pdf_path):
        """Extract all form field names from PDF"""
        try:
            pdf_document = fitz.open(pdf_path)
            fields = []
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                widgets = page.widgets()
                
                if widgets:
                    for widget in widgets:
                        if widget.field_name:
                            fields.append({
                                'name': widget.field_name,
                                'type': widget.field_type if hasattr(widget, 'field_type') else 'unknown',
                                'value': widget.field_value if hasattr(widget, 'field_value') else ''
                            })
            
            pdf_document.close()
            return fields
        except Exception as e:
            print(f"Error extracting PDF fields: {e}")
            return []