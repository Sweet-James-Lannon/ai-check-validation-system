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
import time

# =============================================================================
# PDF CACHE - SPEED UP REPEATED DOWNLOADS! 🚀
# =============================================================================
# In-memory cache for PDFs (5 minute TTL)
pdf_cache = {}
PDF_CACHE_TTL = 300  # 5 minutes

def get_cached_pdf(cache_key):
    """Get PDF from cache if available and not expired"""
    if cache_key in pdf_cache:
        cached_data, timestamp = pdf_cache[cache_key]
        if time.time() - timestamp < PDF_CACHE_TTL:
            api_logger.info(f"💨 PDF cache HIT: {cache_key}")
            return cached_data
        else:
            # Expired - remove it
            del pdf_cache[cache_key]
            api_logger.info(f"⏰ PDF cache EXPIRED: {cache_key}")
    return None

def cache_pdf(cache_key, pdf_data):       
    """Cache PDF data with timestamp"""
    pdf_cache[cache_key] = (pdf_data, time.time())
    api_logger.info(f"💾 PDF cached: {cache_key} ({len(pdf_data)} bytes)")
 
# =============================================================================
# CONFIGURATION & SETUP
# =============================================================================

api_logger = get_api_logger()

dashboard_bp = Blueprint("dashboard", __name__)

# =============================================================================
# MAIN DASHBOARD ROUTES
# =============================================================================

#░█▀▄░█▀▀░█▀▄░█░█░█▀▀░░░█▀▀░█░█░█▀▀░█▀▀░█░█░░░█▀▄░█▀█░▀█▀░█▀█
#░█░█░█▀▀░█▀▄░█░█░█░█░░░█░░░█▀█░█▀▀░█░░░█▀▄░░░█░█░█▀█░░█░░█▀█
#░▀▀░░▀▀▀░▀▀░░▀▀▀░▀▀▀░░░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░░░▀▀░░▀░▀░░▀░░▀░▀

@dashboard_bp.route("/debug_check/<check_id>")
@login_required
def debug_check_data(check_id):
    """Debug endpoint to see raw check data and date formatting"""
    from datetime import date, datetime
    
    # Get raw check data
    response = supabase_service.client.table('checks')\
        .select('id,file_name,batch_id,batch_id_fk,provider_name,insurance_company,claim_number,policy_number,amount,check_number,check_issue_date,pay_to,routing_number,account_number,memo,matter_name,matter_id,matter_url,case_type,delivery_service,tracking_number,claimant,insured_name,status,confidence_score,flags,validated_at,validated_by,reviewed_at,reviewed_by,created_at,updated_at,batch_images,page_count,check_type,n8n_sync_enabled,image_data,image_mime_type')\
        .eq('id', check_id)\
        .single()\
        .execute()
    
    check = response.data
    
    debug_info = {
        'raw_check_issue_date': str(check.get('check_issue_date')),
        'raw_check_issue_date_type': str(type(check.get('check_issue_date'))),
        'raw_date_of_loss': str(check.get('date_of_loss')),
        'raw_date_of_loss_type': str(type(check.get('date_of_loss'))),
        'all_fields': {k: str(v) for k, v in check.items() if 'date' in k.lower()}
    }
    
    return jsonify(debug_info)

#░█▀▄░█▀█░█▀▀░█░█░█▀▄░█▀█░█▀█░█▀▄░█▀▄░░░█░█░█▀█░█▄█░█▀▀
#░█░█░█▀█░▀▀█░█▀█░█▀▄░█░█░█▀█░█▀▄░█░█░░░█▀█░█░█░█░█░█▀▀
#░▀▀░░▀░▀░▀▀▀░▀░▀░▀▀░░▀▀▀░▀░▀░▀░▀░▀▀░░░░▀░▀░▀▀▀░▀░▀░▀▀▀

@dashboard_bp.route("/")
@login_required
def dashboard_home():
    """Redirect to check queue as default landing page"""
    return redirect(url_for('dashboard.check_queue'))

#░█▄█░█▀█░▀█▀░█▀█░░░█▀▄░█▀█░█▀▀░█░█░█▀▄░█▀█░█▀█░█▀▄░█▀▄
#░█░█░█▀█░░█░░█░█░░░█░█░█▀█░▀▀█░█▀█░█▀▄░█░█░█▀█░█▀▄░█░█
#░▀░▀░▀░▀░▀▀▀░▀░▀░░░▀▀░░▀░▀░▀▀▀░▀░▀░▀▀░░▀▀▀░▀░▀░▀░▀░▀▀░

@dashboard_bp.route("/dashboard")
@login_required
def main_dashboard():
    """Universal Document Ingestion RAG System - Main Dashboard"""
    user = session.get("user")
    
    # Get system-wide metrics across all document types
    try:
        # Get all checks (regardless of batch selection)
        checks_response = supabase_service.client.table('checks')\
            .select('id,file_name,batch_id,batch_id_fk,provider_name,insurance_company,claim_number,policy_number,amount,check_number,check_issue_date,pay_to,routing_number,account_number,memo,matter_name,matter_id,matter_url,case_type,delivery_service,tracking_number,claimant,insured_name,status,confidence_score,flags,validated_at,validated_by,reviewed_at,reviewed_by,created_at,updated_at,batch_images,page_count')\
            .order('created_at', desc=True)\
            .execute()
        
        checks = checks_response.data
        
        # Ensure provider_name is available (fallback to pay_to or claimant)
        if checks:
            for check in checks:
                if not check.get('provider_name'):
                    check['provider_name'] = check.get('pay_to') or check.get('claimant')
        
        # Calculate basic counts
        total_count = len(checks) if checks else 0
        validated_count = len([c for c in checks if c.get('status') == 'approved' and c.get('validated_at')]) if checks else 0
        
        # TODO: Add other document type metrics when tables are created
        # contracts_response = supabase_service.client.table('contracts').select('*').execute()
        # legal_docs_response = supabase_service.client.table('legal_documents').select('*').execute()
        
        document_metrics = {
            'checks': {
                'total': total_count,
                'processed_today': 23,  # TODO: Calculate from database
                'pending': 8,           # TODO: Calculate from database
                'validated': validated_count
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
            'checks': {'total': 0, 'processed_today': 0, 'pending': 0, 'validated': 0},
            'contracts': {'total': 0, 'processed_today': 0, 'pending': 0, 'success_rate': 0},
            'legal_documents': {'total': 0, 'processed_today': 0, 'pending': 0, 'success_rate': 0},
            'general_documents': {'total': 0, 'processed_today': 0, 'pending': 0, 'success_rate': 0}
        }
        return render_template("main_dashboard.html", user=user, metrics=document_metrics, error_message="Failed to load system metrics")

# =============================================================================
# CHECK VALIDATION ROUTES
# =============================================================================

#░█▀▀░█░█░█▀▀░█▀▀░█░█░█▀▀░░░█▀▄░█▀█░█▀▀░█░█░█▀▄░█▀█░█▀█░█▀▄░█▀▄
#░█░░░█▀█░█▀▀░█░░░█▀▄░▀▀█░░░█░█░█▀█░▀▀█░█▀█░█▀▄░█░█░█▀█░█▀▄░█░█
#░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░▀▀▀░░░▀▀░░▀░▀░▀▀▀░▀░▀░▀▀░░▀▀▀░▀░▀░▀░▀░▀▀░

@dashboard_bp.route("/checks/")
@login_required
def checks_dashboard():
    """Check-specific dashboard with AI chat and validation tools"""
    user = session.get("user")
    return render_template("checks_dashboard.html", user=user)

#░█▀▀░█░█░█▀▀░█▀▀░█░█░░░█▀█░█░█░█▀▀░█░█░█▀▀
#░█░░░█▀█░█▀▀░█░░░█▀▄░░░█░█░█░█░█▀▀░█░█░█▀▀
#░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░░░▀▀█░▀▀▀░▀▀▀░▀▀▀░▀▀▀

@dashboard_bp.route("/checks/queue")
@dashboard_bp.route("/checks/queue/<batch_id>")
@login_required
def check_queue(batch_id=None):
    """Check queue page - shows batch summary or specific batch checks"""
    try:
        user = session.get("user")
        
        # Check for batch parameter in query string if not in URL path
        if not batch_id:
            batch_id = request.args.get('batch')
        
        if batch_id:
            # Level 2: Show checks for specific batch
            api_logger.info(f"Loading checks for batch: {batch_id}")
            
            # Select specific fields to avoid schema cache issues with non-existent columns
            checks_response = supabase_service.client.table('checks')\
                .select('id,file_name,batch_id,batch_id_fk,provider_name,insurance_company,claim_number,policy_number,amount,check_number,check_issue_date,pay_to,routing_number,account_number,memo,matter_name,matter_id,matter_url,case_type,delivery_service,tracking_number,claimant,insured_name,status,confidence_score,flags,validated_at,validated_by,reviewed_at,reviewed_by,created_at,updated_at,batch_images,page_count')\
                .eq('batch_id', batch_id)\
                .order('created_at', desc=True)\
                .execute()
            
            checks = checks_response.data
        
            # Format checks for display with confidence percentage
            formatted_checks = []
            for check in checks:
                formatted_check = check.copy()
                confidence_score = check.get('confidence_score', 0)
                formatted_check['confidence_percentage'] = round(confidence_score * 100, 1) if confidence_score else 0
                
                # Debug logging - show what we're getting from DB
                api_logger.info(f"Check ID: {check.get('id')}, provider_name: '{check.get('provider_name')}'")
                
                formatted_checks.append(formatted_check)
            
            total_count = len(formatted_checks)
            
            api_logger.info(f"Loaded {total_count} checks for batch {batch_id}")
            
            return render_template('check_queue.html',
                                 user=user,
                                 checks=formatted_checks,
                                 total_count=total_count,
                                 current_batch_id=batch_id,
                                 current_batch_name=f"Batch {batch_id.replace('BATCH_', '')}",
                                 archived_batches=[],  # No archived batches in batch detail view
                                 view_mode="batch_detail")
        else:
            # Level 1: Show batch summary using our new Supabase function
            api_logger.info("Loading batch summary")
            
            batches_response = supabase_service.client.rpc('get_batches_summary').execute()
            all_batches = batches_response.data if batches_response.data else []
            
            # Separate active vs archived batches
            # A batch is "archived" when ALL checks are approved (no pending or needs_review)
            active_batches = []
            archived_batches = []
            
            for batch in all_batches:
                pending = batch.get('pending_count', 0)
                needs_review = batch.get('needs_review_count', 0)
                approved = batch.get('approved_count', 0)
                total_checks = batch.get('check_count', 0)
                
                # Archived = all checks approved AND no pending/needs_review
                if pending == 0 and needs_review == 0 and approved == total_checks and total_checks > 0:
                    archived_batches.append(batch)
                else:
                    active_batches.append(batch)
            
            # Calculate total pending + needs_review across active batches only
            total_pending_and_review = 0
            for batch in active_batches:
                total_pending_and_review += batch.get('pending_count', 0) + batch.get('needs_review_count', 0)
            
            api_logger.info(f"Loaded {len(active_batches)} active batches and {len(archived_batches)} archived batches")
            api_logger.info(f"Total pending + needs_review: {total_pending_and_review}")
            
            return render_template('check_queue.html',
                                 user=user,
                                 batches=active_batches,  # Active batches only
                                 archived_batches=archived_batches,  # Archived batches
                                 checks=[],  # Empty list for batch view
                                 total_count=total_pending_and_review,  # Total pending + needs_review
                                 view_mode="batch_list")
        
    except Exception as e:
        api_logger.error(f"Error loading check queue: {str(e)}")
        import traceback
        api_logger.error(traceback.format_exc())
        user = session.get("user")
        return render_template("check_queue.html", 
                             user=user,
                             batches=[],
                             archived_batches=[],  # Add archived batches to error handler
                             selected_batch=None,
                             checks=[], 
                             total_count=0,
                             status_counts={'pending': 0, 'needs_review': 0, 'approved': 0},
                             current_status='pending',
                             error_message="Failed to load checks from database")

#░█▀▀░█░█░█▀▀░█▀▀░█░█░░░█▀▄░█▀▀░▀█▀░█▀█░▀█▀░█░░
#░█░░░█▀█░█▀▀░█░░░█▀▄░░░█░█░█▀▀░░█░░█▀█░░█░░█░░
#░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░░░▀▀░░▀▀▀░░▀░░▀░▀░▀▀▀░▀▀▀

@dashboard_bp.route("/checks/detail/<check_id>")
@login_required
def check_detail(check_id):
    """Individual check detail page for validation"""
    try:
        user = session.get("user")
        
        # Get specific check from Supabase (explicit fields to avoid schema cache issues)
        response = supabase_service.client.table('checks').select('id,file_name,batch_id,batch_id_fk,provider_name,insurance_company,claim_number,policy_number,amount,check_number,check_issue_date,pay_to,routing_number,account_number,memo,matter_name,matter_id,matter_url,case_type,delivery_service,tracking_number,claimant,insured_name,status,confidence_score,flags,validated_at,validated_by,reviewed_at,reviewed_by,created_at,updated_at,batch_images,page_count,check_type,n8n_sync_enabled,image_data,image_mime_type').eq('id', check_id).single().execute()
        
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
            # Core fields from schema
            'id': check.get('id'),
            'check_number': extracted_data.get('check_number') or check.get('check_number', ''),
            'check_type': check.get('check_type', ''),
            'amount': check.get('amount', ''),
            'pay_to': extracted_data.get('pay_to') or check.get('pay_to', ''),
            'matter_name': check.get('matter_name', ''),
            'matter_id': check.get('matter_id', ''),
            'matter_url': check.get('matter_url', ''),
            'case_type': check.get('case_type', ''),
            'delivery_service': check.get('delivery_service', ''),
            'memo': extracted_data.get('memo') or check.get('memo', ''),
            'routing_number': extracted_data.get('routing_number') or check.get('routing_number', ''),
            'account_number': extracted_data.get('account_number') or check.get('account_number', ''),
            
            # Date fields - just pass through raw values from Supabase
            'check_issue_date': extracted_data.get('check_issue_date') or check.get('check_issue_date'),
            'date_of_loss': check.get('date_of_loss'),
            
            # Status and validation
            'confidence_score': check.get('confidence_score', 0),
            'confidence_percentage': round((check.get('confidence_score', 0) * 100), 1) if check.get('confidence_score') else 0,
            'status': check.get('status', 'pending'),
            'flags': check.get('flags', []),
            
            # Insurance fields (NEW SCHEMA)
            'insurance_company': check.get('insurance_company', ''),
            'insurance_id': check.get('insurance_id', ''),
            'claim_number': extracted_data.get('claim_number') or check.get('claim_number', ''),
            'policy_number': extracted_data.get('policy_number') or check.get('policy_number', ''),
            'provider_name': check.get('provider_name') or check.get('pay_to') or check.get('claimant', ''),
            'claimant': check.get('claimant', ''),
            'insured_name': check.get('insured_name', ''),
            'reference_number': check.get('reference_number', ''),
            'bank_name': check.get('bank_name', ''),
            'extraction_notes': check.get('extraction_notes', ''),
            
            # File and batch management
            'file_name': check.get('file_name', ''),
            'file_id': check.get('file_id', ''),
            'batch_id': check.get('batch_id', ''),
            'batch_id_fk': check.get('batch_id_fk', ''),
            'batch_images': processed_batch_images,
            'page_count': check.get('page_count', 0),
            
            # Image data
            'image_data': check.get('image_data', ''),
            'image_mime_type': check.get('image_mime_type', ''),
            'image_url_link': check.get('image_url_link', ''),
            
            # OCR and processing
            'raw_ocr_content': check.get('raw_ocr_content', ''),
            
            # Review and validation timestamps
            'created_at': check.get('created_at', ''),
            'updated_at': check.get('updated_at', ''),
            'reviewed_at': check.get('reviewed_at', ''),
            'reviewed_by': check.get('reviewed_by', ''),
            'validated_at': check.get('validated_at', ''),
            'validated_by': check.get('validated_by', ''),
            'forward_reason': check.get('forward_reason', ''),
            
            # Salesforce integration
            'salesforce_response': check.get('salesforce_response', {}),
            'salesforce_validated': check.get('salesforce_validated', False),
            'validation_score': check.get('validation_score', None)
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

#░█▀▀░█░█░█▀▀░█▀▀░█░█░░░█▀▄░█▀█░▀█▀░█▀▀░█░█░░░▀█▀░█▄█░█▀█░█▀▀░█▀▀░█▀▀
#░█░░░█▀█░█▀▀░█░░░█▀▄░░░█▀▄░█▀█░░█░░█░░░█▀█░░░░█░░█░█░█▀█░█░█░█▀▀░▀▀█
#░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░░░▀▀░░▀░▀░░▀░░▀▀▀░▀░▀░░░▀▀▀░▀░▀░▀░▀░▀▀▀░▀▀▀░▀▀▀

@dashboard_bp.route("/checks/batch-images/<check_id>")
@login_required
def check_batch_images(check_id):
    """API endpoint to get batch images for a specific check"""
    try:
        user = session.get("user")
        
        # Get specific check from Supabase - only select fields that exist in schema
        response = supabase_service.client.table('checks').select('batch_images, batch_id, page_count').eq('id', check_id).single().execute()
        
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
            "image_count": len(processed_images),
            "page_count": check.get('page_count', 0),
            "images": processed_images
        })
        
    except Exception as e:
        api_logger.error(f"Error loading batch images for check {check_id}: {str(e)}")
        return jsonify({"error": f"Failed to load batch images: {str(e)}"}), 500

#░█▀▀░█░█░█▀▀░█▀▀░█░█░░░█▀▄░█▀█░▀█▀░█▀▀░█░█░░░▀█▀░█▄█░█▀█░█▀▀░█▀▀░█▀▀
#░█░░░█▀█░█▀▀░█░░░█▀▄░░░█▀▄░█▀█░░█░░█░░░█▀█░░░░█░░█░█░█▀█░█░█░█▀▀░▀▀█
#░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░░░▀▀░░▀░▀░░▀░░▀▀▀░▀░▀░░░▀▀▀░▀░▀░▀░▀░▀▀▀░▀▀▀░▀▀▀

@dashboard_bp.route("/checks/image-proxy/<check_id>/<int:image_index>")
@login_required
def proxy_check_image(check_id, image_index):
    """Serve check images from Supabase Storage"""
    try:
        user = session.get("user")
        
        api_logger.info(f"=== Image proxy request: check_id={check_id}, image_index={image_index} ===")
        
        # Get specific check from Supabase
        response = supabase_service.client.table('checks').select('batch_images, image_data, image_mime_type, file_name, batch_id').eq('id', check_id).single().execute()
        
        if not response.data:
            api_logger.warning(f"Check {check_id} not found for image proxy")
            return "Image not found", 404
        
        check = response.data
        api_logger.info(f"Check found. batch_id: {check.get('batch_id')}, has batch_images: {bool(check.get('batch_images'))}")
        
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
        
        # Handle batch images from Supabase Storage
        batch_images = check.get('batch_images', [])
        if not batch_images or image_index >= len(batch_images):
            return "Image not found", 404
            
        image_info = batch_images[image_index]
        if not isinstance(image_info, dict):
            return "Invalid image data", 400
        
        # Get the storage path
        storage_path = None
        file_name = image_info.get('filename') or image_info.get('file_name')
        
        if not file_name:
            api_logger.error(f"No filename found in image_info: {image_info}")
            return "No filename available", 404
        
        api_logger.info(f"Looking for file: {file_name}")
        
        # The database URLs are outdated - they reference "Batch 157-C" but files are in "batch-{timestamp}" folders
        # We need to search for the file across all batch folders
        bucket_name = 'check-documents'
        
        try:
            # List all folders in the bucket
            folders = supabase_service.client.storage.from_(bucket_name).list()
            api_logger.info(f"Found {len(folders)} folders in bucket")
            
            # Search for the file in each batch folder
            for folder_info in folders:
                folder_name = folder_info.get('name')
                if not folder_name or not folder_name.startswith('batch-'):
                    continue
                
                try:
                    # List files in this folder
                    files = supabase_service.client.storage.from_(bucket_name).list(folder_name)
                    
                    # Check if our file is in this folder
                    for file_info in files:
                        if file_info.get('name') == file_name:
                            storage_path = f"{folder_name}/{file_name}"
                            api_logger.info(f"Found file in folder: {storage_path}")
                            break
                    
                    if storage_path:
                        break
                except Exception as e:
                    api_logger.warning(f"Error listing files in folder {folder_name}: {e}")
                    continue
        except Exception as e:
            api_logger.error(f"Error listing folders in bucket: {e}")
        
        if not storage_path:
            api_logger.error(f"No storage path found for check {check_id}, image {image_index}. batch_id: {check.get('batch_id')}, image_info: {image_info}")
            return "No storage path available", 404
        
        api_logger.info(f"Fetching image from Supabase Storage: {storage_path}")
        
        # Check if this is a PDF file
        file_type = image_info.get('file_type', '').lower() or storage_path.lower().split('.')[-1]
        mime_type = image_info.get('mime_type', 'image/jpeg')
        
        # Fetch the file from Supabase Storage
        try:
            # Get signed URL or public URL from Supabase Storage
            bucket_name = 'check-documents'  # Correct bucket name
            api_logger.info(f"Attempting to download from bucket '{bucket_name}' path: {storage_path}")
            
            file_data = supabase_service.client.storage.from_(bucket_name).download(storage_path)
            
            if not file_data:
                error_msg = f"No data returned from Supabase Storage for bucket '{bucket_name}', path: {storage_path}"
                api_logger.error(error_msg)
                return error_msg, 404
            
            # If it's a PDF, try to convert first page to image
            if file_type == 'pdf':
                try:
                    import fitz  # PyMuPDF
                    
                    # Create PDF document from bytes
                    pdf_doc = fitz.open(stream=file_data, filetype="pdf")
                    
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
                            'Cache-Control': 'public, max-age=86400',  # Cache for 24 hours
                            'Access-Control-Allow-Origin': '*'
                        }
                    )
                    
                except ImportError:
                    # PyMuPDF not available, fallback to showing PDF icon
                    api_logger.warning("PyMuPDF not installed, cannot convert PDF to image")
                    return Response(
                        "PDF conversion not available",
                        status=404
                    )
                except Exception as e:
                    api_logger.error(f"Error converting PDF to image: {str(e)}")
                    return Response(
                        f"PDF conversion error: {str(e)}",
                        status=500
                    )
            else:
                # Not a PDF, serve as regular image
                # Return the image directly from Supabase Storage
                return Response(
                    file_data,
                    mimetype=mime_type,
                    headers={
                        'Cache-Control': 'public, max-age=86400',  # Cache for 24 hours
                        'Access-Control-Allow-Origin': '*'
                    }
                )
            
        except Exception as e:
            api_logger.error(f"Error fetching image from Supabase Storage: {str(e)}")
            api_logger.error(f"Error type: {type(e).__name__}")
            import traceback
            api_logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return f"Storage error: {str(e)}", 500
            
    except Exception as e:
        api_logger.error(f"Error proxying image for check {check_id}, index {image_index}: {str(e)}")
        api_logger.error(f"Error type: {type(e).__name__}")
        import traceback
        api_logger.error(f"Full traceback:\n{traceback.format_exc()}")
        return f"Server error: {str(e)}", 500

# =============================================================================
# PDF DIRECT SERVING - BLAZING FAST! 🔥
# =============================================================================

#░█▀▀░█▀▀░█▀▄░█░█░█▀▀░░░█▀▀░█░█░█▀▀░█▀▀░█░█░░░█▀█░█▀▄░█▀▀
#░▀▀█░█▀▀░█▀▄░▀▄▀░█▀▀░░░█░░░█▀█░█▀▀░█░░░█▀▄░░░█▀▀░█░█░█▀▀
#░▀▀▀░▀▀▀░▀░▀░░▀░░▀▀▀░░░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░░░▀░░░▀▀░░▀░░

@dashboard_bp.route("/checks/pdf/<check_id>/<int:page_index>")
@login_required
def serve_check_pdf(check_id, page_index):
    """
    Serve PDF files directly without image conversion - MUCH FASTER!
    PDF.js on the client side handles rendering
    WITH CACHING FOR BLAZING SPEED! 🚀
    """
    try:
        api_logger.info(f"=== PDF request: check_id={check_id}, page_index={page_index} ===")
        
        # Get check from Supabase (need updated_at for cache busting)
        response = supabase_service.client.table('checks').select('batch_images, batch_id, updated_at').eq('id', check_id).single().execute()
        
        if not response.data:
            api_logger.warning(f"Check {check_id} not found for PDF serving")
            return "PDF not found", 404
        
        check = response.data
        batch_images = check.get('batch_images', [])
        updated_at = check.get('updated_at', '')
        
        # Create cache key with updated_at timestamp for cache busting after splits
        # This ensures that after a split, we don't serve stale cached PDFs
        cache_key = f"{check_id}_{page_index}_{updated_at}"
        
        # CHECK CACHE FIRST! 💨
        cached_pdf = get_cached_pdf(cache_key)
        if cached_pdf:
            api_logger.info(f"💨 Serving cached PDF for {cache_key}")
            return Response(
                cached_pdf,
                mimetype='application/pdf',
                headers={
                    'Cache-Control': 'no-cache',  # Changed: Don't cache in browser after splits
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/pdf',
                    'X-Cache': 'HIT'  # Debug header
                }
            )
        
        if not batch_images or page_index >= len(batch_images):
            api_logger.warning(f"No batch images or invalid index for check {check_id}. Has {len(batch_images)} pages, requested index {page_index}")
            return "PDF page not found", 404
        
        image_info = batch_images[page_index]
        if not isinstance(image_info, dict):
            return "Invalid PDF data", 400
        
        # Extract storage path from URL (much faster than searching!)
        pdf_url = image_info.get('url') or image_info.get('primary_url') or image_info.get('download_url')
        
        if not pdf_url:
            api_logger.error(f"No URL found in image_info: {image_info}")
            return "No PDF URL available", 404
        
        # Extract the storage path from the URL
        # URL format: https://...supabase.co/storage/v1/object/public/check-documents/batch-1762471297198/006-C-1.pdf
        # We need: batch-1762471297198/006-C-1.pdf
        bucket_name = 'check-documents'
        
        try:
            # Split URL to get the path after the bucket name
            if '/check-documents/' in pdf_url:
                storage_path = pdf_url.split('/check-documents/')[1]
            else:
                # Fallback: try to extract filename and folder
                file_name = image_info.get('filename') or image_info.get('file_name')
                if not file_name:
                    api_logger.error(f"No filename or path found in image_info: {image_info}")
                    return "No filename available", 404
                
                # Try to find the folder from URL or use batch ID
                if '/' in pdf_url:
                    parts = pdf_url.split('/')
                    # Look for batch folder pattern
                    for i, part in enumerate(parts):
                        if part.startswith('batch-') and i + 1 < len(parts):
                            storage_path = f"{part}/{file_name}"
                            break
                    else:
                        storage_path = file_name
                else:
                    storage_path = file_name
            
            api_logger.info(f"Extracted storage path: {storage_path}")
            
        except Exception as e:
            api_logger.error(f"Error extracting storage path from URL: {e}")
            return "Failed to parse PDF URL", 404
        
        api_logger.info(f"Fetching PDF from Supabase Storage: {storage_path}")
        
        # Download the PDF file
        try:
            pdf_data = supabase_service.client.storage.from_(bucket_name).download(storage_path)
            
            if not pdf_data:
                api_logger.error(f"No data returned from Supabase Storage for: {storage_path}")
                return "PDF file is empty", 404
            
            # CACHE IT! 💾 (server-side only, with updated_at in key for cache busting)
            cache_pdf(cache_key, pdf_data)
            
            # Return PDF with NO BROWSER CACHING to prevent stale data after splits
            # Server-side cache is still used (with updated_at in key for invalidation)
            return Response(
                pdf_data,
                mimetype='application/pdf',
                headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate',  # Prevent browser caching
                    'Pragma': 'no-cache',  # HTTP 1.0 compatibility
                    'Expires': '0',  # Proxies
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/pdf',
                    'Content-Length': str(len(pdf_data)),  # Help browser estimate download time
                    'Accept-Ranges': 'bytes',  # Enable range requests for faster streaming
                    'X-Cache': 'MISS'  # Debug header
                }
            )
            
        except Exception as e:
            api_logger.error(f"Error fetching PDF from Supabase Storage: {str(e)}")
            import traceback
            api_logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return f"Storage error: {str(e)}", 500
            
    except Exception as e:
        api_logger.error(f"Error serving PDF for check {check_id}, page {page_index}: {str(e)}")
        import traceback
        api_logger.error(f"Full traceback:\n{traceback.format_exc()}")
        return f"Server error: {str(e)}", 500

# =============================================================================
# DOCUMENT MANAGEMENT ROUTES
# =============================================================================

#░█▀▀░█▀█░█▀█░▀█▀░█▀▄░█▀█░█▀▀░▀█▀░█▀▀░░░█▀▄░█▀█░█▀▀░█░█░█▀▄░█▀█░█▀█░█▀▄░█▀▄
#░█░░░█░█░█░█░░█░░█▀▄░█▀█░█░░░░█░░▀▀█░░░█░█░█▀█░▀▀█░█▀█░█▀▄░█░█░█▀█░█▀▄░█░█
#░▀▀▀░▀▀▀░▀░▀░░▀░░▀░▀░▀░▀░▀▀▀░░▀░░▀▀▀░░░▀▀░░▀░▀░▀▀▀░▀░▀░▀▀░░▀▀▀░▀░▀░▀░▀░▀▀░

@dashboard_bp.route("/contracts/")
@login_required
def contracts_dashboard():
    """Contracts-specific dashboard with AI chat and analysis tools"""
    user = session.get("user")
    return render_template("contracts_dashboard.html", user=user)

#░█░░░█▀▀░█▀▀░█▀█░█░░░░░█▀▄░█▀█░█▀▀░█▀▀░░░█▀▄░█▀█░█▀▀░█░█░█▀▄░█▀█░█▀█░█▀▄░█▀▄
#░█░░░█▀▀░█░█░█▀█░█░░░░░█░█░█░█░█░░░▀▀█░░░█░█░█▀█░▀▀█░█▀█░█▀▄░█░█░█▀█░█▀▄░█░█
#░▀▀▀░▀▀▀░▀▀▀░▀░▀░▀▀▀░░░▀▀░░▀▀▀░▀▀▀░▀▀▀░░░▀▀░░▀░▀░▀▀▀░▀░▀░▀▀░░▀▀▀░▀░▀░▀░▀░▀▀░

@dashboard_bp.route("/legal-documents/")
@login_required
def legal_documents_dashboard():
    """Legal documents dashboard with AI chat and analysis tools"""
    user = session.get("user")
    return render_template("legal_documents_dashboard.html", user=user)

#░█▀▀░█▀▀░█▀█░█▀▀░█▀▄░█▀█░█░░░░░█▀▄░█▀█░█▀▀░█▀▀░░░█▀▄░█▀█░█▀▀░█░█░█▀▄░█▀█░█▀█░█▀▄░█▀▄
#░█░█░█▀▀░█░█░█▀▀░█▀▄░█▀█░█░░░░░█░█░█░█░█░░░▀▀█░░░█░█░█▀█░▀▀█░█▀█░█▀▄░█░█░█▀█░█▀▄░█░█
#░▀▀▀░▀▀▀░▀░▀░▀▀▀░▀░▀░▀░▀░▀▀▀░░░▀▀░░▀▀▀░▀▀▀░▀▀▀░░░▀▀░░▀░▀░▀▀▀░▀░▀░▀▀░░▀▀▀░▀░▀░▀░▀░▀▀░

@dashboard_bp.route("/documents/")
@login_required
def general_documents_dashboard():
    """General documents dashboard with AI chat and analysis tools"""
    user = session.get("user")
    return render_template("general_documents_dashboard.html", user=user)

# =============================================================================
# END OF FILE
# =============================================================================