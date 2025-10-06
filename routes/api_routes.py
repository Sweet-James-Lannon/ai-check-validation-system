"""
=============================================================================
API ROUTES - Check Validation System
=============================================================================
RESTful API endpoints for check validation operations.
Handles CRUD operations, approval workflows, and data persistence.

Author: Sweet James Development Team  
Last Updated: September 2025
=============================================================================
"""

from flask import Blueprint, request, jsonify, session
from utils.decorators import login_required
from utils.logger import get_api_logger
from services.supabase_service import supabase_service
from datetime import datetime

# =============================================================================
# CONFIGURATION & SETUP
# =============================================================================

api_logger = get_api_logger()
api_bp = Blueprint("api", __name__)

# =============================================================================
# CHECK VALIDATION API ENDPOINTS
# =============================================================================

@api_bp.route("/api/checks/save/<check_id>", methods=["POST"])
@login_required
def save_check(check_id):
    """
    Save check modifications without triggering validation
    Updates Supabase record but does NOT set validated_at timestam p
    """
    try:
        user = session.get("user")
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        # Prepare update data - only include fields that exist in schema
        update_data = {}
        
        # Map form fields to database fields - Updated for new schema
        field_mapping = {
            'payee_name': 'payee_name',
            'pay_to': 'pay_to', 
            'amount': 'amount',
            'check_date': 'check_date',
            'check_number': 'check_number',
            'check_type': 'check_type',
            'routing_number': 'routing_number',
            'account_number': 'account_number',
            'micr_line': 'micr_line',
            'matter_name': 'matter_name',
            'case_type': 'case_type',
            'delivery_service': 'delivery_service',
            'memo': 'memo',
            'policy_number': 'policy_number',
            'claim_number': 'claim_number',
            'insurance_company_name': 'insurance_company_name',
            'matter_id': 'matter_id',
            'check_issue_date': 'check_issue_date',
            'insurance_record_id': 'insurance_record_id'
        }
        
        # Process each field from the form
        for form_field, db_field in field_mapping.items():
            if form_field in data and data[form_field] is not None:
                value = data[form_field]
                
                # Handle amount conversion
                if form_field == 'amount':
                    try:
                        # Remove currency symbols and convert to float
                        if isinstance(value, str):
                            value = value.replace('$', '').replace(',', '').strip()
                        update_data[db_field] = float(value) if value else 0.0
                    except (ValueError, TypeError):
                        update_data[db_field] = 0.0
                else:
                    update_data[db_field] = str(value).strip() if value else None
        
        # Add metadata (but NOT validated_at - that's only for approval)
        update_data.update({
            'updated_at': datetime.utcnow().isoformat(),
            'reviewed_by': user.get('preferred_username', 'unknown'),
            'reviewed_at': datetime.utcnow().isoformat()
        })
        
        # Update in Supabase
        response = supabase_service.client.table('checks').update(update_data).eq('id', check_id).execute()
        
        if response.data and len(response.data) > 0:
            api_logger.info(f"Check {check_id} saved by {user.get('preferred_username')}")
            return jsonify({
                "status": "success", 
                "message": "Check saved successfully",
                "updated_at": response.data[0].get('updated_at'),
                "reviewed_by": response.data[0].get('reviewed_by')
            })
        else:
            api_logger.error(f"No data returned when saving check {check_id}")
            return jsonify({"status": "error", "message": "Failed to save check - no data returned"}), 500
            
    except Exception as e:
        api_logger.error(f"Error saving check {check_id}: {str(e)}")
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

@api_bp.route("/api/checks/approve/<check_id>", methods=["POST"])
@login_required  
def approve_check(check_id):
    """
    Approve check and trigger Salesforce protocol
    Sets validated_at timestamp which triggers Jai's edge function
    """
    try:
        user = session.get("user")
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        # Prepare update data with all current form values
        update_data = {}
        
        # Map form fields to database fields (same as save) - Updated for new schema
        field_mapping = {
            'payee_name': 'payee_name',
            'pay_to': 'pay_to', 
            'amount': 'amount',
            'check_date': 'check_date',
            'check_number': 'check_number',
            'check_type': 'check_type',
            'routing_number': 'routing_number',
            'account_number': 'account_number',
            'micr_line': 'micr_line',
            'matter_name': 'matter_name',
            'case_type': 'case_type',
            'delivery_service': 'delivery_service',
            'memo': 'memo',
            'policy_number': 'policy_number',
            'claim_number': 'claim_number',
            'insurance_company_name': 'insurance_company_name',
            'matter_id': 'matter_id',
            'check_issue_date': 'check_issue_date',
            'insurance_record_id': 'insurance_record_id'
        }
        
        # Process form fields
        for form_field, db_field in field_mapping.items():
            if form_field in data and data[form_field] is not None:
                value = data[form_field]
                
                # Handle amount conversion
                if form_field == 'amount':
                    try:
                        if isinstance(value, str):
                            value = value.replace('$', '').replace(',', '').strip()
                        update_data[db_field] = float(value) if value else 0.0
                    except (ValueError, TypeError):
                        update_data[db_field] = 0.0
                else:
                    update_data[db_field] = str(value).strip() if value else None
        
        # Add approval metadata - THIS TRIGGERS THE EDGE FUNCTION
        approval_timestamp = datetime.utcnow().isoformat()
        update_data.update({
            'status': 'approved',
            'validated_at': approval_timestamp,  # ← THIS triggers Jai's edge function
            'validated_by': user.get('preferred_username', 'unknown'),  # ← Capture approving user
            'updated_at': approval_timestamp,
            'reviewed_by': user.get('preferred_username', 'unknown'),
            'reviewed_at': approval_timestamp
        })
        
        # Update in Supabase
        response = supabase_service.client.table('checks').update(update_data).eq('id', check_id).execute()
        
        if response.data and len(response.data) > 0:
            api_logger.info(f"Check {check_id} APPROVED by {user.get('preferred_username')} - triggering Salesforce protocol")
            return jsonify({
                "status": "success", 
                "message": "Check approved successfully - Salesforce protocol initiated",
                "validated_at": response.data[0].get('validated_at'),
                "validated_by": response.data[0].get('validated_by'),
                "validated_by_name": user.get('name', user.get('preferred_username', 'Unknown')),
                "new_status": "approved"
            })
        else:
            api_logger.error(f"No data returned when approving check {check_id}")
            return jsonify({"status": "error", "message": "Failed to approve check - no data returned"}), 500
            
    except Exception as e:
        api_logger.error(f"Error approving check {check_id}: {str(e)}")
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

@api_bp.route("/api/checks/needs-review/<check_id>", methods=["POST"])
@login_required
def flag_needs_review(check_id):
    """Change check status to needs_review"""
    try:
        user = session.get("user")
        if not user:
            return jsonify({"status": "error", "message": "User not authenticated"}), 401
        
        # Get form data from request
        form_data = request.get_json() or {}
        reason = form_data.get('reason', 'No reason provided')
        api_logger.info(f"Setting check {check_id} to needs_review by {user.get('preferred_username')} - Reason: {reason}")
        
        # Update timestamp 
        timestamp = datetime.utcnow().isoformat()
        
        # Update the check in Supabase with needs_review status
        update_data = {
            'status': 'needs_review',
            'updated_at': timestamp
        }
        
        # Include any form field updates (but exclude reason as it's not a database column)
        for field, value in form_data.items():
            if field not in ['status', 'updated_at', 'reason']:
                update_data[field] = value
        
        response = supabase_service.client.table('checks').update(update_data).eq('id', check_id).execute()
        
        if response.data:
            api_logger.info(f"Check {check_id} STATUS CHANGED TO NEEDS_REVIEW by {user.get('preferred_username')}")
            return jsonify({
                "status": "success", 
                "message": "Check status changed to needs review",
                "new_status": "needs_review"
            })
        else:
            api_logger.error(f"No data returned when updating check {check_id} to needs_review")
            return jsonify({"status": "error", "message": "Failed to update check status"}), 500
            
    except Exception as e:
        api_logger.error(f"Error flagging check {check_id} for review: {str(e)}")
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

@api_bp.route("/api/checks/<check_id>", methods=["GET"])
@login_required
def get_check_details(check_id):
    """Get detailed information for a specific check"""
    try:
        response = supabase_service.client.table('checks').select('*').eq('id', check_id).single().execute()
        
        if response.data:
            return jsonify({
                "status": "success",
                "check": response.data
            })
        else:
            return jsonify({"status": "error", "message": "Check not found"}), 404
            
    except Exception as e:
        api_logger.error(f"Error getting check {check_id}: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route("/api/checks/stats", methods=["GET"])
@login_required

def get_check_stats():
    """Get check processing statistics"""
    try:
        # Get all checks
        response = supabase_service.client.table('checks').select('status, confidence_score, created_at').execute()
        
        if not response.data:
            return jsonify({
                "status": "success",
                "stats": {
                    "total": 0,
                    "pending": 0,
                    "approved": 0,
                    "rejected": 0,
                    "high_confidence": 0,
                    "low_confidence": 0
                }
            })
        
        checks = response.data
        total = len(checks)
        
        # Calculate statistics
        stats = {
            "total": total,
            "pending": len([c for c in checks if c.get('status') == 'pending']),
            "approved": len([c for c in checks if c.get('status') == 'approved']),
            "rejected": len([c for c in checks if c.get('status') == 'rejected']),
            "high_confidence": len([c for c in checks if (c.get('confidence_score') or 0) > 0.8]),
            "low_confidence": len([c for c in checks if (c.get('confidence_score') or 0) < 0.7])
        }
        
        return jsonify({
            "status": "success",
            "stats": stats
        })
        
    except Exception as e:
        api_logger.error(f"Error getting check stats: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# =============================================================================
# n8n for pink page detection API ENDPOINTS
# =============================================================================

@api_bp.route("/api/batch/split-analysis", methods=["POST"])
def analyze_batch_splits():
    try:
        api_logger.info("=== Split analysis endpoint called ===")
        
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400
        
        pdf_file = request.files['pdf_file']
        pdf_bytes = pdf_file.read()
        
        import fitz
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(pdf_document)
        
        separator_page_indices = []
        page_text_samples = {}  # NEW: Store text samples for debugging
        
        for page_num in range(total_pages):
            page = pdf_document[page_num]
            text = page.get_text().upper()
            
            # Store first 100 chars of each page for debugging
            page_text_samples[page_num] = text[:100] if text else "(empty)"
            
            # More flexible detection - check for key words
            has_automatically = "AUTOMATICALLY" in text
            has_separated = "SEPARATED" in text
            has_sorted = "SORTED" in text
            has_indexed = "INDEXED" in text
            
            # Consider it a separator if it has at least 3 of the 4 keywords
            keyword_count = sum([has_automatically, has_separated, has_sorted, has_indexed])
            
            if keyword_count >= 3:
                separator_page_indices.append(page_num)
                api_logger.info(f"Page {page_num}: Separator detected (keywords: {keyword_count}/4)")
        
        # Generate splits (pages AFTER separators start new batches)
        splits = [0]
        for sep_page in separator_page_indices:
            if sep_page + 1 < total_pages:
                splits.append(sep_page + 1)
        
        sub_batches = [chr(65 + i) for i in range(len(splits))]
        
        page_counts = []
        for i in range(len(splits)):
            start = splits[i]
            end = splits[i + 1] if i + 1 < len(splits) else total_pages
            count = end - start
            for sep in separator_page_indices:
                if start <= sep < end:
                    count -= 1
            page_counts.append(count)
        
        pdf_document.close()
        
        result = {
            'success': True,
            'total_pages': total_pages,
            'separator_pages': separator_page_indices,
            'splits': splits,
            'sub_batches': sub_batches,
            'page_counts': page_counts,
            'debug_text_samples': page_text_samples  # NEW: Include for debugging
        }
        
        return jsonify(result)
        
    except Exception as e:
        api_logger.error(f"ERROR: {str(e)}")
        import traceback
        api_logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@api_bp.route("/api/test-imports", methods=["GET"])
def test_imports():
    try:
        import fitz
        from PIL import Image
        import numpy as np
        return jsonify({
            'status': 'success',
            'pymupdf_version': fitz.VersionBind,
            'fitz_file': fitz.__file__,
            'imports_working': True
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__
        }), 500

# =============================================================================
# SYSTEM HEALTH API ENDPOINTS
# =============================================================================

@api_bp.route("/api/health", methods=["GET"])
def api_health():
    """Health check for API endpoints"""
    try:
        # Test Supabase connection
        supabase_health = supabase_service.health_check()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "supabase": supabase_health
            }
        })
        
    except Exception as e:
        api_logger.error(f"API health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503