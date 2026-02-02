document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const excelDropZone = document.getElementById('excelDropZone');
    const pdfDropZone = document.getElementById('pdfDropZone');
    const excelFileInput = document.getElementById('excelFileInput');
    const pdfFileInput = document.getElementById('pdfFileInput');
    const recordsSection = document.getElementById('recordsSection');
    const previewSection = document.getElementById('previewSection');
    const recordsGrid = document.getElementById('recordsGrid');
    const selectedRecordInfo = document.getElementById('selectedRecordInfo');
    const recordDetails = document.getElementById('recordDetails');
    const selectedRecordName = document.getElementById('selectedRecordName');
    const selectedRecordId = document.getElementById('selectedRecordId');
    const generatePdfBtn = document.getElementById('generatePdfBtn');
    const previewTemplateBtn = document.getElementById('previewTemplateBtn');
    const downloadSection = document.getElementById('downloadSection');
    const downloadLink = document.getElementById('downloadLink');
    const generatedFileName = document.getElementById('generatedFileName');
    const pdfsBody = document.getElementById('pdfsBody');
    const refreshPdfsBtn = document.getElementById('refreshPdfsBtn');
    const clearAllBtn = document.getElementById('clearAllBtn');
    const searchInput = document.getElementById('searchInput');
    const recordsCount = document.getElementById('recordsCount');
    const pdfTemplateName = document.getElementById('pdfTemplateName');
    const loadingModal = document.getElementById('loadingModal');
    const loadingMessage = document.getElementById('loadingMessage');
    const loadingDetails = document.getElementById('loadingDetails');
    const excelFileInfo = document.getElementById('excelFileInfo');
    const pdfFileInfo = document.getElementById('pdfFileInfo');
    const pdfPreviewModal = document.getElementById('pdfPreviewModal');
    const pdfPreviewFrame = document.getElementById('pdfPreviewFrame');
    const closePdfPreview = document.getElementById('closePdfPreview');
    const uploadStatus = document.getElementById('uploadStatus');
    const debugExcelBtn = document.getElementById('debugExcelBtn');
    const debugPdfBtn = document.getElementById('debugPdfBtn');

    // State variables
    let records = [];
    let selectedRecord = null;
    let pdfTemplatePath = null;
    let pdfTemplateFilename = null;
    let excelFilePath = null;
    let filteredRecords = [];

    // Initialize
    loadGeneratedPDFs();
    checkSystemStatus();

    // Excel File Upload
    setupFileUpload(excelDropZone, excelFileInput, 'excel', handleExcelUpload);
    setupFileUpload(pdfDropZone, pdfFileInput, 'pdf', handlePDFUpload);

    function setupFileUpload(dropZone, fileInput, type, handler) {
        dropZone.addEventListener('click', () => fileInput.click());
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('drag-over'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('drag-over'), false);
        });
        
        dropZone.addEventListener('drop', handleDrop, false);
        fileInput.addEventListener('change', handleFileSelect, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handler(files[0]);
        }
        
        function handleFileSelect(e) {
            const files = e.target.files;
            handler(files[0]);
        }
    }

    async function handleExcelUpload(file) {
        if (!file) return;
        
        if (!file.name.match(/\.(xlsx|xls|csv)$/i)) {
            showError('Please upload an Excel file (.xlsx, .xls, or .csv)');
            return;
        }

        showLoading('Uploading Excel file...', 'Extracting ALL data from spreadsheet');
        
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload-excel', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                records = result.records;
                excelFilePath = result.excel_file_path;
                filteredRecords = [...records];
                
                // Update UI
                excelFileInfo.innerHTML = `
                    <strong>✓ Excel file uploaded:</strong> ${file.name}<br>
                    <small>${result.count} records • ${Object.keys(records[0] || {}).length} fields extracted • ${formatFileSize(file.size)}</small>
                `;
                excelFileInfo.classList.add('show', 'success');
                
                // Show records section
                recordsSection.style.display = 'block';
                updateRecordsDisplay();
                
                showSuccess('Excel file processed successfully!');
                updateUploadStatus();
                
                // Log the first record for debugging
                if (records.length > 0) {
                    console.log('First record data:', records[0]);
                }
            } else {
                showError(`Failed to process Excel file: ${result.error}`);
                excelFileInfo.classList.add('show', 'error');
            }
        } catch (error) {
            showError(`Error uploading file: ${error.message}`);
            excelFileInfo.classList.add('show', 'error');
        } finally {
            hideLoading();
        }
    }

    async function handlePDFUpload(file) {
        if (!file) return;
        
        if (!file.name.match(/\.pdf$/i)) {
            showError('Please upload a PDF file (.pdf)');
            return;
        }

        showLoading('Uploading PDF template...', 'Analyzing PDF structure');
        
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload-pdf', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                pdfTemplatePath = result.pdf_path;
                pdfTemplateFilename = result.filename;
                
                // Update UI
                pdfFileInfo.innerHTML = `
                    <strong>✓ PDF template uploaded:</strong> ${file.name}<br>
                    <small>Ready for filling • ${formatFileSize(file.size)}</small>
                `;
                pdfFileInfo.classList.add('show', 'success');
                pdfTemplateName.textContent = file.name;
                
                // Enable buttons
                previewTemplateBtn.disabled = false;
                
                showSuccess('PDF template uploaded successfully!');
                updateUploadStatus();
                
                // If records are already loaded, show preview section
                if (records.length > 0) {
                    previewSection.style.display = 'block';
                }
            } else {
                showError(`Failed to upload PDF: ${result.error}`);
                pdfFileInfo.classList.add('show', 'error');
            }
        } catch (error) {
            showError(`Error uploading PDF: ${error.message}`);
            pdfFileInfo.classList.add('show', 'error');
        } finally {
            hideLoading();
        }
    }

    function updateRecordsDisplay() {
        recordsCount.textContent = filteredRecords.length;
        
        if (filteredRecords.length === 0) {
            recordsGrid.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-search"></i>
                    <p>No records found matching your search</p>
                </div>
            `;
            return;
        }
        
        recordsGrid.innerHTML = filteredRecords.map((record, index) => `
            <div class="record-card ${selectedRecord === record ? 'selected' : ''}" 
                 data-index="${index}" 
                 onclick="selectRecord(${index})">
                <span class="record-badge">#${record.RECORD_ID}</span>
                <div class="record-avatar">
                    <i class="fas fa-user"></i>
                </div>
                <h3 class="record-name">${record.DISPLAY_NAME || `Record ${record.RECORD_ID}`}</h3>
                <div class="record-meta">
                    ${getRecordPreviewInfo(record)}
                </div>
            </div>
        `).join('');
    }

    function getRecordPreviewInfo(record) {
        // Show up to 3 fields that have data
        let info = '';
        let count = 0;
        
        for (const [key, value] of Object.entries(record)) {
            if (key !== 'RECORD_ID' && key !== 'EXCEL_ROW' && key !== 'DISPLAY_NAME' && value && count < 3) {
                const icon = getIconForField(key);
                const displayKey = key.length > 15 ? key.substring(0, 15) + '...' : key;
                info += `<div><i class="fas fa-${icon}"></i> ${displayKey}: ${value}</div>`;
                count++;
            }
        }
        
        if (info === '') {
            info = '<div><i class="fas fa-info-circle"></i> No data preview available</div>';
        }
        
        return info;
    }

    // Global function for record selection
    window.selectRecord = function(index) {
        selectedRecord = filteredRecords[index];
        
        // Update UI
        document.querySelectorAll('.record-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`.record-card[data-index="${index}"]`)?.classList.add('selected');
        
        // Show preview section if not visible
        if (pdfTemplatePath) {
            previewSection.style.display = 'block';
        }
        
        // Update selected record info
        selectedRecordName.textContent = selectedRecord.DISPLAY_NAME || `Record ${selectedRecord.RECORD_ID}`;
        selectedRecordId.textContent = `Record ID: ${selectedRecord.RECORD_ID} • Row: ${selectedRecord.EXCEL_ROW}`;
        
        // Update record details - show ALL fields except metadata
        const detailsHTML = Object.entries(selectedRecord)
            .filter(([key]) => !['RECORD_ID', 'EXCEL_ROW', 'DISPLAY_NAME'].includes(key))
            .map(([key, value]) => `
                <div class="detail-item">
                    <div class="detail-label">
                        <i class="fas fa-${getIconForField(key)}"></i>
                        ${formatFieldName(key)}
                    </div>
                    <div class="detail-value">${value || '<em style="color:#999;">Empty</em>'}</div>
                </div>
            `)
            .join('');
        
        recordDetails.innerHTML = detailsHTML;
        
        // Enable generate button
        generatePdfBtn.disabled = false;
        
        // Scroll to preview section
        previewSection.scrollIntoView({ behavior: 'smooth' });
        
        // Debug: log all data
        console.log('Selected record data:', selectedRecord);
    };

    // Search functionality
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        
        if (!searchTerm) {
            filteredRecords = [...records];
        } else {
            filteredRecords = records.filter(record => {
                // Search through ALL fields
                return Object.entries(record).some(([key, value]) => {
                    if (key === 'RECORD_ID' || key === 'EXCEL_ROW') return false;
                    const strValue = String(value || '').toLowerCase();
                    const strKey = String(key || '').toLowerCase();
                    return strValue.includes(searchTerm) || strKey.includes(searchTerm);
                });
            });
        }
        
        updateRecordsDisplay();
    });

    // Generate PDF for selected record
    generatePdfBtn.addEventListener('click', async function() {
        if (!selectedRecord || !pdfTemplatePath) {
            showError('Please select a record and upload a PDF template first');
            return;
        }

        showLoading('Generating filled PDF...', 'Matching Excel data with PDF fields');

        try {
            const response = await fetch('/api/generate-pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    data: selectedRecord,
                    pdf_template_path: pdfTemplatePath
                })
            });

            const result = await response.json();

            if (result.success) {
                // Show download section
                downloadLink.href = `/api/download/${result.filename}`;
                downloadLink.download = result.filename;
                generatedFileName.textContent = `Filename: ${result.filename}`;
                downloadSection.style.display = 'block';
                
                // Scroll to download section
                downloadSection.scrollIntoView({ behavior: 'smooth' });
                
                showSuccess('PDF generated successfully!');
                
                // Refresh PDFs list
                loadGeneratedPDFs();
            } else {
                showError(`Failed to generate PDF: ${result.error}`);
            }
        } catch (error) {
            showError(`Error generating PDF: ${error.message}`);
        } finally {
            hideLoading();
        }
    });

    // Preview PDF template
    previewTemplateBtn.addEventListener('click', function() {
        if (pdfTemplatePath) {
            // Use the correct endpoint for template preview
            const url = `/api/download-template?preview=${encodeURIComponent(pdfTemplatePath)}`;
            pdfPreviewFrame.src = url;
            pdfPreviewModal.style.display = 'flex';
        }
    });

    // Debug Excel Fields
    debugExcelBtn.addEventListener('click', async function() {
        const input = document.getElementById('excelFileInput');
        if (input.files.length > 0) {
            showLoading('Analyzing Excel file...', 'Extracting field names');
            
            const formData = new FormData();
            formData.append('file', input.files[0]);
            
            try {
                const response = await fetch('/api/debug-excel-fields', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                console.log('Excel Debug Result:', result);
                
                if (result.success) {
                    const message = `Found ${result.field_count} fields in Excel:\n\n` +
                                   result.fields.map(f => `• ${f}`).join('\n') +
                                   `\n\nSample data:\n${JSON.stringify(result.sample_record, null, 2)}`;
                    alert(message);
                } else {
                    showError(`Debug failed: ${result.error}`);
                }
            } catch (error) {
                showError(`Debug error: ${error.message}`);
            } finally {
                hideLoading();
            }
        } else {
            alert('Please select an Excel file first');
        }
    });

    // Debug PDF Fields
    debugPdfBtn.addEventListener('click', async function() {
        const input = document.getElementById('pdfFileInput');
        if (input.files.length > 0) {
            showLoading('Analyzing PDF template...', 'Extracting form fields');
            
            const formData = new FormData();
            formData.append('file', input.files[0]);
            
            try {
                const response = await fetch('/api/debug-pdf-fields', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                console.log('PDF Debug Result:', result);
                
                if (result.success) {
                    if (result.fields.length > 0) {
                        const message = `Found ${result.field_count} form fields in PDF:\n\n` +
                                       result.fields.map(f => `• ${f.name} (${f.type})`).join('\n');
                        alert(message);
                    } else {
                        alert('No interactive form fields found in PDF.\n\nData will be added as text overlay at the top of the PDF.');
                    }
                } else {
                    showError(`Debug failed: ${result.error}`);
                }
            } catch (error) {
                showError(`Debug error: ${error.message}`);
            } finally {
                hideLoading();
            }
        } else {
            alert('Please select a PDF file first');
        }
    });

    // Close PDF preview
    closePdfPreview.addEventListener('click', function() {
        pdfPreviewModal.style.display = 'none';
        if (pdfPreviewFrame.src) {
            pdfPreviewFrame.src = '';
        }
    });

    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === pdfPreviewModal) {
            closePdfPreview.click();
        }
    });

    // Load generated PDFs
    async function loadGeneratedPDFs() {
        try {
            const response = await fetch('/api/filled-pdfs');
            const result = await response.json();
            
            if (result.success) {
                if (result.pdfs.length === 0) {
                    pdfsBody.innerHTML = `
                        <tr>
                            <td colspan="4" class="empty-table">
                                <i class="fas fa-folder-open"></i>
                                <p>No PDFs generated yet</p>
                            </td>
                        </tr>
                    `;
                } else {
                    pdfsBody.innerHTML = result.pdfs.map(pdf => `
                        <tr>
                            <td>${pdf.filename}</td>
                            <td>${new Date(pdf.created_at).toLocaleString()}</td>
                            <td>${formatFileSize(pdf.size)}</td>
                            <td>
                                <button class="action-btn action-download" onclick="downloadPDF('${pdf.filename}')">
                                    <i class="fas fa-download"></i> Download
                                </button>
                                <button class="action-btn action-delete" onclick="deletePDF('${pdf.filename}')">
                                    <i class="fas fa-trash"></i> Delete
                                </button>
                            </td>
                        </tr>
                    `).join('');
                }
            }
        } catch (error) {
            console.error('Error loading PDFs:', error);
        }
    }

    // Refresh PDFs list
    refreshPdfsBtn.addEventListener('click', loadGeneratedPDFs);

    // Clear all PDFs
    clearAllBtn.addEventListener('click', async function() {
        if (confirm('Are you sure you want to delete ALL generated PDFs? This action cannot be undone.')) {
            showLoading('Deleting all PDFs...', 'This may take a moment');
            
            try {
                // Get all PDFs first
                const response = await fetch('/api/filled-pdfs');
                const result = await response.json();
                
                if (result.success) {
                    // Delete each PDF
                    const deletePromises = result.pdfs.map(pdf => 
                        fetch(`/api/delete/${pdf.filename}`, { method: 'DELETE' })
                    );
                    
                    await Promise.all(deletePromises);
                    
                    showSuccess('All PDFs deleted successfully!');
                    loadGeneratedPDFs();
                }
            } catch (error) {
                showError(`Error deleting PDFs: ${error.message}`);
            } finally {
                hideLoading();
            }
        }
    });

    // Update upload status
    function updateUploadStatus() {
        const excelReady = records.length > 0;
        const pdfReady = !!pdfTemplatePath;
        
        if (excelReady && pdfReady) {
            uploadStatus.innerHTML = `
                <div class="upload-status-ready">
                    <i class="fas fa-check-circle"></i>
                    <span>Both files uploaded! Select a record and click "Fill & Generate PDF"</span>
                </div>
            `;
            uploadStatus.classList.add('show');
        } else if (excelReady || pdfReady) {
            const missing = excelReady ? 'PDF template' : 'Excel file';
            uploadStatus.innerHTML = `
                <div class="upload-status-waiting">
                    <i class="fas fa-info-circle"></i>
                    <span>Upload ${missing} to continue</span>
                </div>
            `;
            uploadStatus.classList.add('show');
        } else {
            uploadStatus.classList.remove('show');
        }
    }

    // Utility Functions
    function getIconForField(field) {
        const fieldLower = field.toLowerCase();
        if (fieldLower.includes('name')) return 'user';
        if (fieldLower.includes('id')) return 'id-card';
        if (fieldLower.includes('email')) return 'envelope';
        if (fieldLower.includes('phone') || fieldLower.includes('mobile')) return 'phone';
        if (fieldLower.includes('address')) return 'home';
        if (fieldLower.includes('date')) return 'calendar';
        if (fieldLower.includes('amount') || fieldLower.includes('salary') || fieldLower.includes('price')) return 'money-bill';
        if (fieldLower.includes('department') || fieldLower.includes('company')) return 'building';
        if (fieldLower.includes('position') || fieldLower.includes('role')) return 'briefcase';
        return 'tag';
    }

    function formatFieldName(field) {
        return field
            .replace(/_/g, ' ')
            .replace(/([A-Z])/g, ' $1')
            .replace(/^./, str => str.toUpperCase())
            .trim();
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function showLoading(message, details = '') {
        loadingMessage.textContent = message;
        loadingDetails.textContent = details;
        loadingModal.style.display = 'flex';
    }

    function hideLoading() {
        loadingModal.style.display = 'none';
        loadingDetails.textContent = '';
    }

    function showSuccess(message) {
        // Simple alert for now
        console.log('Success:', message);
    }

    function showError(message) {
        alert(`Error: ${message}`);
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    async function checkSystemStatus() {
        try {
            const response = await fetch('/health');
            const data = await response.json();
            
            if (data.status === 'healthy') {
                console.log('System is online');
            }
        } catch (error) {
            console.error('System status check failed:', error);
        }
    }
});

// Global functions for PDF actions
async function downloadPDF(filename) {
    try {
        const response = await fetch(`/api/download/${filename}`);
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            alert('Failed to download file');
        }
    } catch (error) {
        alert(`Error downloading file: ${error.message}`);
    }
}

async function deletePDF(filename) {
    if (confirm(`Are you sure you want to delete "${filename}"?`)) {
        try {
            const response = await fetch(`/api/delete/${filename}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('PDF deleted successfully');
                // Refresh the PDFs list
                location.reload();
            } else {
                alert(`Failed to delete: ${result.error}`);
            }
        } catch (error) {
            alert(`Error deleting PDF: ${error.message}`);
        }
    }
}