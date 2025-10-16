"""
=============================================================================
DASHBOARD ROUTES - Check Validation System
=============================================================================
Primary routes for check validation dashboard and document management.
Handles main UI, check queues, validation workflows, and document dashboards.

Author: Sweet James Development Team  
Last Updated: September 2025
=============================================================================
"""

from flask import Blueprint, render_template, session, redirect, url_for, jsonify, Response, request
from utils.decorators import (
    login_required,
)
from utils.logger import get_api_logger
from services.supabase_service import supabase_service
import requests
import io

# =============================================================================
# CONFIGURATION & SETUP
# =============================================================================

api_logger = get_api_logger()

dashboard_bp = Blueprint("dashboard", __name__)

# =============================================================================
# MAIN DASHBOARD ROUTES
# =============================================================================

@dashboard_bp.route("/")
@login_required
def dashboard_home():
    """Universal Document Ingestion RAG System - Main Dashboard"""
    user = session.get("user")
    
    # Get system-wide metrics across all document types
    try:
        # Get all checks (regardless of batch selection)
        checks_response = supabase_service.client.table('checks')\
            .select('*')\
            .order('created_at', desc=True)\
            .execute()
        
        # Calculate basic counts
        total_count = len(checks_response.data) if checks_response.data else 0
        
        # TODO: Add other document type metrics when tables are created
        # contracts_response = supabase_service.client.table('contracts').select('*').execute()
        # legal_docs_response = supabase_service.client.table('legal_documents').select('*').execute()
        
        document_metrics = {
            'checks': {
                'total': total_count,
                'processed_today': 23,  # TODO: Calculate from database
                'pending': 8,           # TODO: Calculate from database
                'success_rate': 94.2    # TODO: Calculate from database
            },
            'contracts': {
                'total': 156,          # TODO: Get from database
                'processed_today': 12,
                'pending': 3,
                'success_rate': 97.1
            },
            'legal_documents': {
                'total': 89,           # TODO: Get from database
                'processed_today': 7,
                'pending': 2,
                'success_rate': 95.8
            },
            'general_documents': {
                'total': 234,          # TODO: Get from database
                'processed_today': 18,
                'pending': 5,
                'success_rate': 93.4
            }
        }
        
        api_logger.info("Loading universal document dashboard")
        return render_template("main_dashboard.html", user=user, metrics=document_metrics)
        
    except Exception as e:
        api_logger.error(f"Error loading main dashboard: {str(e)}")
        # Fallback metrics if database fails
        document_metrics = {
            'checks': {'total': 0, 'processed_today': 0, 'pending': 0, 'success_rate': 0},
            'contracts': {'total': 0, 'processed_today': 0, 'pending': 0, 'success_rate': 0},
            'legal_documents': {'total': 0, 'processed_today': 0, 'pending': 0, 'success_rate': 0},
            'general_documents': {'total': 0, 'processed_today': 0, 'pending': 0, 'success_rate': 0}
        }
        return render_template("main_dashboard.html", user=user, metrics=document_metrics, error_message="Failed to load system metrics")

# =============================================================================
# CHECK VALIDATION ROUTES
# =============================================================================

@dashboard_bp.route("/checks/")
@login_required
def checks_dashboard():
    """Check-specific dashboard with AI chat and validation tools"""
    user = session.get("user")
    return render_template("checks_dashboard.html", user=user)

@dashboard_bp.route("/checks/queue")
@dashboard_bp.route("/checks/queue/<batch_id>")
@login_required
def check_queue(batch_id=None):
    """Check queue page - shows batch summary or specific batch checks"""
    try:
        user = session.get("user")
        
        if batch_id:
            # Level 2: Show checks for specific batch
            api_logger.info(f"Loading checks for batch: {batch_id}")
            
            checks_response = supabase_service.client.table('checks')\
                .select('*')\
                .eq('batch_id', batch_id)\
                .order('created_at', desc=True)\
                .execute()
            
            # Get the batch name for display
            batch_name = batch_id.replace('BATCH_', '')
            
            # Format checks for display with confidence percentage
            formatted_checks = []
            for check in checks_response.data:
                formatted_check = check.copy()
                confidence_score = check.get('confidence_score', 0)
                formatted_check['confidence_percentage'] = round(confidence_score * 100, 1) if confidence_score else 0
                formatted_checks.append(formatted_check)
            
            total_count = len(formatted_checks)
            
            api_logger.info(f"Loaded {total_count} checks for batch {batch_id}")
            
            return render_template('check_queue.html',
                                 user=user,
                                 checks=formatted_checks,
                                 total_count=total_count,
                                 current_batch_id=batch_id,
                                 current_batch_name=f"Batch {batch_name}",
                                 view_mode="batch_detail")
        else:
            # Level 1: Show batch summary using our new Supabase function
            api_logger.info("Loading batch summary")
            
            batches_response = supabase_service.client.rpc('get_batches_summary').execute()
            
            api_logger.info(f"Loaded {len(batches_response.data) if batches_response.data else 0} batches")
            
            return render_template('check_queue.html',
                                 user=user,
                                 batches=batches_response.data,
                                 checks=[],  # Empty list for batch view
                                 total_count=0,  # No checks loaded yet
                                 view_mode="batch_list")
        
    except Exception as e:
        api_logger.error(f"Error loading check queue: {str(e)}")
        import traceback
        api_logger.error(traceback.format_exc())
        user = session.get("user")
        return render_template("check_queue.html", 
                             user=user,
                             batches=[],
                             selected_batch=None,
                             checks=[], 
                             total_count=0,
                             status_counts={'pending': 0, 'needs_review': 0, 'approved': 0},
                             current_status='pending',
                             error_message="Failed to load checks from database")

@dashboard_bp.route("/checks/detail/<check_id>")
@login_required
def check_detail(check_id):
    """Individual check detail page for validation"""
    try:
        user = session.get("user")
        
        # Get specific check from Supabase
        response = supabase_service.client.table('checks').select('*').eq('id', check_id).single().execute()
        
        if not response.data:
            api_logger.warning(f"Check {check_id} not found")
            return render_template("error.html", 
                                 user=user,
                                 error_message=f"Check {check_id} not found"), 404
        
        check = response.data
        
        # Process batch images if they exist
        batch_images = check.get('batch_images', [])
        processed_batch_images = []
        
        if batch_images and isinstance(batch_images, list):
            for img in batch_images:
                if isinstance(img, dict):
                    processed_batch_images.append({
                        'url': img.get('url', ''),
                        'file_name': img.get('file_name', ''),
                        'filename': img.get('filename', ''),
                        'download_url': img.get('download_url', ''),
                        'primary_url': img.get('primary_url', ''),
                        'file_size': img.get('file_size', ''),
                        'mime_type': img.get('mime_type', ''),
                        'file_type': img.get('file_type', ''),
                        'file_id': img.get('file_id', ''),
                        'status': img.get('status', ''),
                        'extracted_data': img.get('extracted_data', {}),
                        'amount': img.get('amount'),
                        'payee_name': img.get('payee_name'),
                        'check_number': img.get('check_number'),
                        'insurance_company': img.get('insurance_company')
                    })
        
        # Extract data from batch images if available
        extracted_data = {}
        if processed_batch_images:
            # Find the first PDF with extracted data
            for img in processed_batch_images:
                if img.get('file_type') == 'pdf' and img.get('extracted_data'):
                    extracted_data = img.get('extracted_data', {})
                    break
        
        # Use extracted data from PDFs if available, otherwise fall back to database fields
        formatted_check = {
            'id': check.get('id'),
            'check_number': extracted_data.get('check_number') or check.get('check_number', ''),
            'check_type': check.get('check_type', ''),
            'payee_name': extracted_data.get('payee_name') or check.get('payee_name', ''),
            'pay_to': extracted_data.get('pay_to') or check.get('pay_to', ''),
            'amount': extracted_data.get('amount') or check.get('amount', ''),
            'check_date': extracted_data.get('check_date') or check.get('check_date', ''),
            'check_issue_date': extracted_data.get('check_issue_date') or check.get('check_issue_date', ''),
            'memo': extracted_data.get('memo') or check.get('memo', ''),
            'routing_number': extracted_data.get('routing_number') or check.get('routing_number', ''),
            'account_number': extracted_data.get('account_number') or check.get('account_number', ''),
            'micr_line': check.get('micr_line', ''),
            'matter_name': check.get('matter_name', ''),
            'matter_id': check.get('matter_id', ''),
            'case_type': check.get('case_type', ''),
            'delivery_service': check.get('delivery_service', ''),
            'insurance_company_name': extracted_data.get('insurance_company') or check.get('insurance_company_name', ''),
            'claim_number': extracted_data.get('claim_number') or check.get('claim_number', ''),
            'policy_number': extracted_data.get('policy_number') or check.get('policy_number', ''),
            'confidence_score': check.get('confidence_score', 0),
            'status': check.get('status', 'pending'),
            'check_view_status': check.get('check_view_status', 'pending'),
            'flags': check.get('flags', []),
            'file_name': check.get('file_name', ''),
            'file_id': check.get('file_id', ''),
            'raw_ocr_content': check.get('raw_ocr_content', ''),
            'raw_ocr_data': check.get('raw_ocr_data', {}),
            'forward_reason': check.get('forward_reason', ''),
            'source_system': check.get('source_system', ''),
            'created_at': check.get('created_at', ''),
            'updated_at': check.get('updated_at', ''),
            'reviewed_at': check.get('reviewed_at', ''),
            'reviewed_by': check.get('reviewed_by', ''),
            'validated_at': check.get('validated_at', ''),
            'validated_by': check.get('validated_by', ''),
            'confidence_percentage': round((check.get('confidence_score', 0) * 100), 1) if check.get('confidence_score') else 0,
            'image_data': check.get('image_data', ''),
            'image_mime_type': check.get('image_mime_type', ''),
            'image_url_link': check.get('image_url_link', ''),
            'image_download_url': check.get('image_download_url', ''),
            'folder_name': check.get('folder_name', ''),
            'batch_id': check.get('batch_id', ''),
            'file_count': check.get('file_count', 1),
            'batch_images': processed_batch_images,
            'insurance_record_id': check.get('insurance_record_id', ''),
            'salesforce_response': check.get('salesforce_response', {}),
            'salesforce_validated': check.get('salesforce_validated', False),
            'validation_score': check.get('validation_score', None),
            # Legacy field mappings for backward compatibility
            'validated_by_name': check.get('validated_by', ''),
            'flagged_at': check.get('reviewed_at', ''),
            'flagged_by': check.get('reviewed_by', ''),
            'flagged_by_name': check.get('reviewed_by', '')
        }
                
        api_logger.info(f"Loading check detail for {check_id}")
        
        return render_template("check_detail.html", 
                             user=user, 
                             check=formatted_check)
        
    except Exception as e:
        api_logger.error(f"Error loading check detail {check_id}: {str(e)}")
        user = session.get("user")
        return render_template("error.html", 
                             user=user,
                             error_message=f"Failed to load check {check_id}"), 500

@dashboard_bp.route("/checks/batch-images/<check_id>")
@login_required
def check_batch_images(check_id):
    """API endpoint to get batch images for a specific check"""
    try:
        user = session.get("user")
        
        # Get specific check from Supabase
        response = supabase_service.client.table('checks').select('batch_images, batch_id, folder_name, file_count').eq('id', check_id).single().execute()
        
        if not response.data:
            api_logger.warning(f"Check {check_id} not found for batch images")
            return jsonify({"error": "Check not found"}), 404
        
        check = response.data
        batch_images = check.get('batch_images', [])
        
        # Process and validate batch images
        processed_images = []
        if batch_images and isinstance(batch_images, list):
            for img in batch_images:
                if isinstance(img, dict):
                    processed_images.append({
                        'url': img.get('url', ''),
                        'filename': img.get('filename', ''),
                        'download_url': img.get('download_url', ''),
                        'file_size': img.get('file_size', ''),
                        'mime_type': img.get('mime_type', ''),
                        'thumbnail_url': img.get('thumbnail_url', img.get('url', ''))
                    })
        
        api_logger.info(f"Retrieved {len(processed_images)} batch images for check {check_id}")
        
        return jsonify({
            "batch_id": check.get('batch_id', ''),
            "folder_name": check.get('folder_name', ''),
            "file_count": check.get('file_count', 1),
            "images": processed_images
        })
        
    except Exception as e:
        api_logger.error(f"Error loading batch images for check {check_id}: {str(e)}")
        return jsonify({"error": f"Failed to load batch images: {str(e)}"}), 500

@dashboard_bp.route("/checks/image-proxy/<check_id>/<int:image_index>")
@login_required
def proxy_check_image(check_id, image_index):
    """Proxy SharePoint images through Flask to handle authentication and CORS"""
    try:
        user = session.get("user")
        
        # Get specific check from Supabase
        response = supabase_service.client.table('checks').select('batch_images, image_data, image_mime_type').eq('id', check_id).single().execute()
        
        if not response.data:
            api_logger.warning(f"Check {check_id} not found for image proxy")
            return "Image not found", 404
        
        check = response.data
        
        # If it's a single image with base64 data, serve that
        if image_index == 0 and check.get('image_data'):
            import base64
            try:
                image_data = base64.b64decode(check['image_data'])
                mime_type = check.get('image_mime_type', 'image/jpeg')
                return Response(image_data, mimetype=mime_type)
            except Exception as e:
                api_logger.error(f"Error serving base64 image: {str(e)}")
                return "Image decode error", 500
        
        # Handle batch images
        batch_images = check.get('batch_images', [])
        if not batch_images or image_index >= len(batch_images):
            return "Image not found", 404
            
        image_info = batch_images[image_index]
        if not isinstance(image_info, dict):
            return "Invalid image data", 400
            
        # Get the download URL
        download_url = image_info.get('download_url') or image_info.get('primary_url')
        if not download_url:
            return "No image URL available", 404
        
        # Check if this is a PDF file
        file_type = image_info.get('file_type', '').lower()
        
        # Fetch the file from SharePoint
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            file_response = requests.get(download_url, headers=headers, timeout=30)
            file_response.raise_for_status()
            
            # If it's a PDF, try to convert first page to image
            if file_type == 'pdf':
                try:
                    import fitz  # PyMuPDF
                    
                    # Create PDF document from bytes
                    pdf_doc = fitz.open(stream=file_response.content, filetype="pdf")
                    
                    # Get first page
                    page = pdf_doc[0]
                    
                    # Convert to image (2x scale for better quality)
                    mat = fitz.Matrix(2.0, 2.0)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Convert to bytes
                    img_data = pix.tobytes("png")
                    pdf_doc.close()
                    
                    # Return as PNG image
                    return Response(
                        img_data,
                        mimetype='image/png',
                        headers={
                            'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                            'Access-Control-Allow-Origin': '*'
                        }
                    )
                    
                except ImportError:
                    # PyMuPDF not available, fallback to showing PDF icon
                    api_logger.warning("PyMuPDF not installed, cannot convert PDF to image")
                    # Create a simple placeholder image indicating it's a PDF
                    return Response(
                        "PDF conversion not available",
                        status=404
                    )
                except Exception as e:
                    api_logger.error(f"Error converting PDF to image: {str(e)}")
                    # Fallback to showing PDF icon
                    return Response(
                        f"PDF conversion error: {str(e)}",
                        status=500
                    )
            else:
                # Not a PDF, serve as regular image
                content_type = file_response.headers.get('content-type', 'image/jpeg')
                
                # Return the image
                return Response(
                    file_response.content,
                    mimetype=content_type,
                    headers={
                        'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                        'Access-Control-Allow-Origin': '*'
                    }
                )
            
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Error fetching image from SharePoint: {str(e)}")
            return "Image fetch error", 500
            
    except Exception as e:
        api_logger.error(f"Error proxying image for check {check_id}, index {image_index}: {str(e)}")
        return "Server error", 500

# =============================================================================
# DOCUMENT MANAGEMENT ROUTES
# =============================================================================

@dashboard_bp.route("/contracts/")
@login_required
def contracts_dashboard():
    """Contracts-specific dashboard with AI chat and analysis tools"""
    user = session.get("user")
    return render_template("contracts_dashboard.html", user=user)

@dashboard_bp.route("/legal-documents/")
@login_required
def legal_documents_dashboard():
    """Legal documents dashboard with AI chat and analysis tools"""
    user = session.get("user")
    return render_template("legal_documents_dashboard.html", user=user)

@dashboard_bp.route("/documents/")
@login_required
def general_documents_dashboard():
    """General documents dashboard with AI chat and analysis tools"""
    user = session.get("user")
    return render_template("general_documents_dashboard.html", user=user)

# =============================================================================
# END OF FILE
# =============================================================================