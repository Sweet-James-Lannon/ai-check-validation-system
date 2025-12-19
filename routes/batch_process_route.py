# routes/batch_process_route.py
"""
Batch Processing Endpoint - Complete PDF Processing Pipeline

This endpoint replaces the complex n8n workflow with a single API call:
1. Receives PDF + access token from n8n
2. Analyzes pink separators
3. Splits into individual pages
4. Creates OneDrive folders
5. Uploads all files in parallel

n8n workflow becomes: Trigger → Download → Call this endpoint
"""

import io
import logging
import fitz  # PyMuPDF
from flask import Blueprint, request, jsonify
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor

# Import your existing OneDrive service
# from services.one_drive_service import OneDriveService

logger = logging.getLogger(__name__)

batch_process_bp = Blueprint('batch_process', __name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Pink separator detection thresholds
PINK_DETECTION = {
    'red_min': 200,
    'green_max': 180,
    'blue_max': 180,
    'coverage_threshold': 0.15  # 15% of page must be pink
}


# =============================================================================
# PDF ANALYSIS FUNCTIONS
# =============================================================================

def is_pink_separator_page(page) -> bool:
    """
    Detect if a page is a pink separator page.
    
    Args:
        page: PyMuPDF page object
        
    Returns:
        True if page is a pink separator
    """
    try:
        # Render page to image
        pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))  # Low res for speed
        
        # Count pink pixels
        pink_pixels = 0
        total_pixels = pix.width * pix.height
        
        for y in range(0, pix.height, 2):  # Sample every 2nd pixel for speed
            for x in range(0, pix.width, 2):
                pixel = pix.pixel(x, y)
                r, g, b = pixel[0], pixel[1], pixel[2]
                
                # Check if pixel is "pink" (high red, low green/blue)
                if (r >= PINK_DETECTION['red_min'] and 
                    g <= PINK_DETECTION['green_max'] and 
                    b <= PINK_DETECTION['blue_max']):
                    pink_pixels += 1
        
        # Adjust for sampling
        coverage = (pink_pixels * 4) / total_pixels
        return coverage >= PINK_DETECTION['coverage_threshold']
        
    except Exception as e:
        logger.warning(f"Error analyzing page for pink: {e}")
        return False


def analyze_pink_separators(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Analyze PDF to find check boundaries based on pink separator pages.
    
    Args:
        pdf_bytes: PDF file content
        
    Returns:
        List of check batches with start/end pages
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    
    logger.info(f"Analyzing {total_pages} pages for pink separators")
    
    # Find all pink separator pages
    separator_pages = []
    for page_num in range(total_pages):
        if is_pink_separator_page(doc[page_num]):
            separator_pages.append(page_num)
            logger.info(f"Found pink separator at page {page_num + 1}")
    
    # Build check batches
    batches = []
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    
    if not separator_pages:
        # No separators = entire document is one check
        batches.append({
            'letter': 'A',
            'start_page': 0,
            'end_page': total_pages - 1,
            'page_count': total_pages
        })
    else:
        # First batch: page 0 to first separator (exclusive)
        if separator_pages[0] > 0:
            batches.append({
                'letter': letters[len(batches)],
                'start_page': 0,
                'end_page': separator_pages[0] - 1,
                'page_count': separator_pages[0]
            })
        
        # Middle batches: between separators
        for i in range(len(separator_pages)):
            start = separator_pages[i] + 1  # Page after separator
            
            if i + 1 < len(separator_pages):
                end = separator_pages[i + 1] - 1  # Page before next separator
            else:
                end = total_pages - 1  # Last page
            
            if start <= end:  # Only if there are pages in this batch
                batches.append({
                    'letter': letters[len(batches)],
                    'start_page': start,
                    'end_page': end,
                    'page_count': end - start + 1
                })
    
    doc.close()
    logger.info(f"Found {len(batches)} check batches")
    return batches


def split_pdf_into_pages(
    pdf_bytes: bytes, 
    batch_number: str,
    batches: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Split PDF into individual page files for each check batch.
    
    Args:
        pdf_bytes: PDF file content
        batch_number: Batch number (e.g., "0000024")
        batches: List of check batches from analyze_pink_separators
        
    Returns:
        List of page dicts with filename and content
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_pages = []
    
    for batch in batches:
        letter = batch['letter']
        start = batch['start_page']
        end = batch['end_page']
        
        batch_folder = f"Batch {batch_number}-{letter}"
        
        # Create COMPLETE PDF (all pages in this check)
        complete_doc = fitz.open()
        for page_num in range(start, end + 1):
            complete_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        
        complete_bytes = complete_doc.write()
        complete_doc.close()
        
        all_pages.append({
            'batch': letter,
            'batch_folder': batch_folder,
            'filename': f"{batch_number}-{letter}-COMPLETE.pdf",
            'page_number': 'COMPLETE',
            'content': complete_bytes
        })
        
        # Create individual page PDFs
        for page_num in range(start, end + 1):
            page_doc = fitz.open()
            page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            page_bytes = page_doc.write()
            page_doc.close()
            
            relative_page = page_num - start + 1
            all_pages.append({
                'batch': letter,
                'batch_folder': batch_folder,
                'filename': f"{batch_number}-{letter}-{relative_page}.pdf",
                'page_number': relative_page,
                'content': page_bytes
            })
    
    doc.close()
    logger.info(f"Split PDF into {len(all_pages)} files")
    return all_pages


# =============================================================================
# MAIN ENDPOINT
# =============================================================================

@batch_process_bp.route('/api/batch/process', methods=['POST'])
def process_batch():
    """
    Complete batch processing pipeline.
    
    Expects:
        - pdf_file: The batch PDF (multipart form)
        - batch_number: e.g., "024" or "0000024"
        - batch_date: e.g., "2025_12_17"
        - parent_folder_id: OneDrive folder ID for batches
        - Authorization header: Bearer <access_token>
        
    Returns:
        JSON with processing results
    """
    
    # Import here to avoid circular imports
    from services.one_drive_service import OneDriveService
    
    try:
        # ---------------------------------------------------------------------
        # 1. VALIDATE INPUTS
        # ---------------------------------------------------------------------
        
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'No pdf_file provided'}), 400
        
        pdf_file = request.files['pdf_file']
        batch_number = request.form.get('batch_number', '')
        batch_date = request.form.get('batch_date', '')
        parent_folder_id = request.form.get('parent_folder_id', '')
        
        # Get access token from header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        
        access_token = auth_header.replace('Bearer ', '')
        
        if not all([batch_number, batch_date, parent_folder_id]):
            return jsonify({
                'error': 'Missing required fields',
                'required': ['batch_number', 'batch_date', 'parent_folder_id']
            }), 400
        
        # Normalize batch number to 7 digits
        batch_number_normalized = str(int(batch_number)).zfill(7)
        
        logger.info(f"=== PROCESSING BATCH {batch_number_normalized} ===")
        
        # Read PDF
        pdf_bytes = pdf_file.read()
        logger.info(f"Received PDF: {len(pdf_bytes)} bytes")
        
        # ---------------------------------------------------------------------
        # 2. INITIALIZE ONEDRIVE CLIENT
        # ---------------------------------------------------------------------
        
        onedrive = OneDriveService(access_token)
        
        # ---------------------------------------------------------------------
        # 3. ANALYZE PINK SEPARATORS
        # ---------------------------------------------------------------------
        
        logger.info("Analyzing pink separators...")
        batches = analyze_pink_separators(pdf_bytes)
        
        # ---------------------------------------------------------------------
        # 4. CREATE MAIN BATCH FOLDER
        # ---------------------------------------------------------------------
        
        batch_folder_name = f"{batch_date}-BATCH-{batch_number_normalized}"
        logger.info(f"Creating batch folder: {batch_folder_name}")
        
        batch_folder_id = onedrive.create_folder_if_not_exists(
            parent_folder_id,
            batch_folder_name
        )
        
        # ---------------------------------------------------------------------
        # 5. MOVE ORIGINAL PDF TO BATCH FOLDER (optional)
        # ---------------------------------------------------------------------
        
        # If you want to move the original PDF:
        # original_file_id = request.form.get('original_file_id')
        # if original_file_id:
        #     onedrive.move_file(original_file_id, batch_folder_id)
        
        # ---------------------------------------------------------------------
        # 6. SPLIT PDF INTO PAGES
        # ---------------------------------------------------------------------
        
        logger.info("Splitting PDF into pages...")
        all_pages = split_pdf_into_pages(pdf_bytes, batch_number_normalized, batches)
        
        # ---------------------------------------------------------------------
        # 7. CREATE CHECK SUBFOLDERS
        # ---------------------------------------------------------------------
        
        logger.info("Creating check subfolders...")
        subfolder_ids = {}
        
        unique_folders = set(page['batch_folder'] for page in all_pages)
        for folder_name in unique_folders:
            subfolder_id = onedrive.create_folder_if_not_exists(batch_folder_id, folder_name)
            subfolder_ids[folder_name] = subfolder_id
            logger.info(f"Created subfolder: {folder_name} ({subfolder_id})")
        
        # ---------------------------------------------------------------------
        # 8. UPLOAD ALL FILES (PARALLEL)
        # ---------------------------------------------------------------------
        
        logger.info(f"Uploading {len(all_pages)} files in parallel...")
        
        upload_results = {
            'successful': [],
            'failed': []
        }
        
        # Prepare ALL files with their target folder IDs
        all_files_to_upload = [
            {
                'filename': p['filename'],
                'content': p['content'],
                'parent_id': subfolder_ids[p['batch_folder']]
            }
            for p in all_pages
        ]
        
        # Upload EVERYTHING at once
        upload_results = onedrive.upload_files_parallel_multi_folder(
            all_files_to_upload,
            max_workers=15
        )
        
        # ---------------------------------------------------------------------
        # 9. RETURN RESULTS
        # ---------------------------------------------------------------------
        
        success = len(upload_results['failed']) == 0
        
        response = {
            'status': 'success' if success else 'partial_failure',
            'batch_number': batch_number_normalized,
            'batch_folder_id': batch_folder_id,
            'batch_folder_name': batch_folder_name,
            'checks_found': len(batches),
            'checks': [
                {
                    'letter': b['letter'],
                    'page_count': b['page_count'],
                    'folder_id': subfolder_ids.get(f"Batch {batch_number_normalized}-{b['letter']}")
                }
                for b in batches
            ],
            'files_uploaded': len(upload_results['successful']),
            'files_failed': len(upload_results['failed']),
            'failed_files': upload_results['failed'] if upload_results['failed'] else None
        }
        
        logger.info(f"=== BATCH {batch_number_normalized} COMPLETE ===")
        logger.info(f"Uploaded: {len(upload_results['successful'])} files")
        
        if upload_results['failed']:
            logger.warning(f"Failed: {len(upload_results['failed'])} files")
        
        return jsonify(response), 200 if success else 207
        
    except Exception as e:
        logger.exception(f"Batch processing failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


# =============================================================================
# HEALTH CHECK
# =============================================================================

@batch_process_bp.route('/api/batch/process/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'batch_process'})