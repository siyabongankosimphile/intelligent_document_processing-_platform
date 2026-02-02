import sys
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import uuid
from datetime import datetime
import pandas as pd
from werkzeug.utils import secure_filename
import json
import tempfile
from excel_parser import ExcelParser
from pdf_filler import PDFFiller

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMPLATES_FOLDER'] = 'templates'
app.config['FILLED_PDFS_FOLDER'] = 'filled_pdfs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXCEL_EXTENSIONS'] = {'xlsx', 'xls', 'csv'}
app.config['ALLOWED_PDF_EXTENSIONS'] = {'pdf'}

# Create directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMPLATES_FOLDER'], exist_ok=True)
os.makedirs(app.config['FILLED_PDFS_FOLDER'], exist_ok=True)

def allowed_excel_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXCEL_EXTENSIONS']

def allowed_pdf_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_PDF_EXTENSIONS']

class ContractProcessor:
    def __init__(self):
        self.excel_parser = ExcelParser()
        self.pdf_filler = PDFFiller()
    
    def process_excel_file(self, file_path):
        """Process Excel file and extract data for multiple records"""
        try:
            records = self.excel_parser.parse_multiple(file_path)
            return {
                'success': True,
                'records': records,
                'count': len(records),
                'message': f'Successfully extracted {len(records)} records'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process Excel file'
            }
    
    def fill_pdf_template(self, template_path, record_data, output_filename=None):
        """Fill PDF template with record data"""
        try:
            if output_filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_name = record_data.get('FULL_NAME', 'unknown').replace(' ', '_')
                output_filename = f"filled_{safe_name}_{timestamp}.pdf"
            
            output_path = os.path.join(app.config['FILLED_PDFS_FOLDER'], output_filename)
            
            pdf_path = self.pdf_filler.fill_pdf(template_path, record_data, output_path)
            
            return {
                'success': True,
                'pdf_path': pdf_path,
                'filename': os.path.basename(pdf_path),
                'message': 'PDF filled successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to fill PDF'
            }

contract_processor = ContractProcessor()

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/upload-excel', methods=['POST'])
def upload_excel():
    """Handle Excel file upload"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not allowed_excel_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'File type not allowed. Please upload Excel files (.xlsx, .xls, .csv)'
            }), 400
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save file
        file.save(file_path)
        
        # Process the Excel file
        result = contract_processor.process_excel_file(file_path)
        
        # Store file path in session for later use
        if result['success']:
            result['excel_file_path'] = file_path
        else:
            # Clean up if failed
            try:
                os.remove(file_path)
            except:
                pass
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    """Handle PDF template upload"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not allowed_pdf_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'File type not allowed. Please upload PDF files (.pdf)'
            }), 400
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"template_{uuid.uuid4().hex[:8]}_{filename}"
        file_path = os.path.join(app.config['TEMPLATES_FOLDER'], unique_filename)
        
        # Save file
        file.save(file_path)
        
        return jsonify({
            'success': True,
            'pdf_path': file_path,
            'filename': unique_filename,
            'message': 'PDF template uploaded successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    """Generate filled PDF for specific record"""
    try:
        data = request.json.get('data')
        pdf_template_path = request.json.get('pdf_template_path')
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No record data provided'
            }), 400
        
        if not pdf_template_path:
            return jsonify({
                'success': False,
                'error': 'No PDF template path provided'
            }), 400
        
        # Generate PDF
        result = contract_processor.fill_pdf_template(pdf_template_path, data)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/download/<filename>')
def download_pdf(filename):
    """Download generated PDF"""
    try:
        file_path = os.path.join(app.config['FILLED_PDFS_FOLDER'], filename)
        
        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        else:
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/records')
def get_all_records():
    """Get all records from uploaded Excel (for testing)"""
    try:
        # This would typically come from session/database
        # For now, return sample
        return jsonify({
            'success': True,
            'records': []
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/filled-pdfs')
def list_filled_pdfs():
    """List all filled PDFs"""
    try:
        pdfs = []
        for filename in os.listdir(app.config['FILLED_PDFS_FOLDER']):
            if filename.endswith('.pdf'):
                file_path = os.path.join(app.config['FILLED_PDFS_FOLDER'], filename)
                stats = os.stat(file_path)
                
                pdfs.append({
                    'filename': filename,
                    'created_at': datetime.fromtimestamp(stats.st_ctime).isoformat(),
                    'size': stats.st_size
                })
        
        # Sort by creation time (newest first)
        pdfs.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'pdfs': pdfs
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
@app.route('/api/debug-excel-fields', methods=['POST'])
def debug_excel_fields():
    """Debug endpoint to see what fields are in the Excel file"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file'}), 400
        
        file = request.files['file']
        
        # Save temporarily
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"debug_{uuid.uuid4().hex}.xlsx")
        file.save(temp_path)
        
        # Parse to get fields
        parser = ExcelParser()
        fields = parser.get_field_names(temp_path)
        
        # Clean up
        os.remove(temp_path)
        
        return jsonify({
            'success': True,
            'fields': fields,
            'count': len(fields)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/debug-pdf-fields', methods=['POST'])
def debug_pdf_fields():
    """Debug endpoint to see what fields are in the PDF"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file'}), 400
        
        file = request.files['file']
        
        # Save temporarily
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"debug_pdf_{uuid.uuid4().hex}.pdf")
        file.save(temp_path)
        
        # Extract PDF fields
        filler = PDFFiller()
        fields = filler.extract_form_fields(temp_path)
        
        # Clean up
        os.remove(temp_path)
        
        return jsonify({
            'success': True,
            'fields': fields,
            'count': len(fields)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/delete/<filename>', methods=['DELETE'])
def delete_pdf(filename):
    """Delete a filled PDF"""
    try:
        file_path = os.path.join(app.config['FILLED_PDFS_FOLDER'], filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({
                'success': True,
                'message': 'PDF deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'PDF Filler System',
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat()
    })

# Serve static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)