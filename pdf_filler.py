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
            
            # Always try to fill form fields first
            if form_fields:
                print("\nTrying to fill form fields...")
                success_count = self._fill_form_fields_flexible(pdf_document, data, form_fields)
                print(f"Filled {success_count} form fields")
            
            # Always add text overlay as backup
            print("\nAdding text overlay with all data...")
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
                    
                    if value and str(value).strip():
                        try:
                            # Try to set the field value
                            widget.field_value = str(value)
                            widget.update()
                            success_count += 1
                            print(f"  ✓ Filled '{field_name}' with '{value}'")
                        except Exception as e:
                            print(f"  ✗ Could not fill field '{field_name}': {str(e)}")
        
        return success_count

    def _find_best_match(self, pdf_field_name, data):
        """Find the best matching data for a PDF field"""
        pdf_field_lower = pdf_field_name.lower().strip()
        
        # Strategy 1: Exact match (case-insensitive)
        for data_key, data_value in data.items():
            if data_key.lower() == pdf_field_lower:
                return str(data_value) if data_value else ""
        
        # Strategy 2: Remove special characters and spaces
        pdf_field_clean = re.sub(r'[^a-z0-9]', '', pdf_field_lower)
        for data_key, data_value in data.items():
            data_key_clean = re.sub(r'[^a-z0-9]', '', data_key.lower())
            if pdf_field_clean == data_key_clean:
                return str(data_value) if data_value else ""
        
        # Strategy 3: Contains match
        for data_key, data_value in data.items():
            data_key_lower = data_key.lower()
            if pdf_field_lower in data_key_lower or data_key_lower in pdf_field_lower:
                return str(data_value) if data_value else ""
        
        # Strategy 4: Word-based matching
        pdf_words = set(pdf_field_lower.replace('_', ' ').split())
        for data_key, data_value in data.items():
            data_words = set(data_key.lower().replace('_', ' ').split())
            if pdf_words & data_words:  # If they share any words
                return str(data_value) if data_value else ""
        
        return ""

    def _overlay_text_simple(self, pdf_document, data):
        """Simple text overlay using insert_text method - most reliable"""
        print("Creating text overlay with all data...")
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Start position (top-left corner)
            y_position = 40
            x_position = 40
            
            # Create a background rectangle for the data box
            rect_width = 500
            rect_height = min(30 + (len(data) * 16), 300)
            
            # Draw background rectangle
            page.draw_rect(
                fitz.Rect(x_position - 5, y_position - 10, 
                         x_position + rect_width + 5, y_position + rect_height),
                color=(1, 1, 0.9),  # Light yellow
                fill=(1, 1, 0.9),
                width=0
            )
            
            # Draw border
            page.draw_rect(
                fitz.Rect(x_position - 5, y_position - 10, 
                         x_position + rect_width + 5, y_position + rect_height),
                color=(0, 0, 0),
                fill=None,
                width=1
            )
            
            # Add title
            page.insert_text(
                (x_position, y_position),
                "=== FILLED DATA FROM EXCEL ===",
                fontsize=12,
                color=(0, 0, 1)  # Blue
            )
            
            y_position += 25
            
            # Add a separator line
            page.draw_line(
                (x_position, y_position - 5),
                (x_position + rect_width, y_position - 5),
                color=(0.7, 0.7, 0.7),
                width=0.5
            )
            
            y_position += 10
            
            # Add each data field
            field_count = 0
            for key, value in data.items():
                if key not in ['RECORD_ID', 'EXCEL_ROW', 'DISPLAY_NAME'] and value and str(value).strip():
                    # Truncate long values for display
                    display_value = str(value)
                    if len(display_value) > 50:
                        display_value = display_value[:47] + "..."
                    
                    # Add key in bold (using larger font)
                    page.insert_text(
                        (x_position, y_position),
                        f"{key}:",
                        fontsize=10,
                        color=(0, 0, 0)
                    )
                    
                    # Add value
                    page.insert_text(
                        (x_position + 120, y_position),
                        display_value,
                        fontsize=10,
                        color=(0.3, 0.3, 0.3)  # Dark gray
                    )
                    
                    y_position += 16
                    field_count += 1
                    
                    # If we're running out of space, start a new column
                    if y_position > 300 and x_position < 200:
                        y_position = 65
                        x_position += 250
                        rect_width = 250
            
            print(f"  Page {page_num + 1}: Added {field_count} data fields")

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