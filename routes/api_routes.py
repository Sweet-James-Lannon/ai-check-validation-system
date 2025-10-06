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
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400
        
        pdf_file = request.files['pdf_file']
        pdf_bytes = pdf_file.read()
        
        import fitz
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(pdf_document)
        
        separator_page_indices = []
        
        for page_num in range(total_pages):
            page = pdf_document[page_num]
            text = page.get_text().upper()
            
            # Count how many separator keywords exist (with OCR tolerance)
            keyword_score = 0
            
            # "AUTOMATICALLY" or variants
            if any(variant in text for variant in ["AUTOMATIC", "AUTOMATICA"]):
                keyword_score += 1
            
            # "SEPARATED" or variants  
            if any(variant in text for variant in ["SEPARAT", "SEPERAT"]):
                keyword_score += 1
            
            # "SORTED"
            if "SORT" in text:
                keyword_score += 1
            
            # "INDEXED" or variants
            if any(variant in text for variant in ["INDEX", "!NDEX", "1NDEX"]):
                keyword_score += 1
            
            # "FOUNDATION" or variants
            if any(variant in text for variant in ["FOUNDATION", "FIUNDATION", "FUUNDATION"]):
                keyword_score += 1
            
            # "EXTRACT"
            if "EXTRACT" in text:
                keyword_score += 1
            
            # If page has at least 4 of the 6 keywords, it's a separator
            if keyword_score >= 4:
                separator_page_indices.append(page_num)
        
        # Build sub-batches: content between separator pairs
        # Pairs: (3,4), (8,9), (13,14), etc.
        splits = []
        current_pos = 0
        
        i = 0
        while i < len(separator_page_indices):
            sep_start = separator_page_indices[i]
            
            # Content from current position to separator start
            if current_pos < sep_start:
                splits.append({
                    'start': current_pos,
                    'end': sep_start - 1,
                    'page_count': sep_start - current_pos
                })
            
            # Skip separator pair (assume consecutive pages are pairs)
            if i + 1 < len(separator_page_indices) and separator_page_indices[i + 1] == sep_start + 1:
                current_pos = sep_start + 2  # Skip both separator pages
                i += 2
            else:
                current_pos = sep_start + 1  # Skip single separator
                i += 1
        
        # Add final batch if there's content after last separator
        if current_pos < total_pages:
            splits.append({
                'start': current_pos,
                'end': total_pages - 1,
                'page_count': total_pages - current_pos
            })
        
        # Generate sub-batch labels
        sub_batches = [chr(65 + i) for i in range(len(splits))]
        
        # Add 1 to all page numbers for human-readable 1-based indexing
        separator_pages_display = [p + 1 for p in separator_page_indices]
        splits_display = [
            {
                'batch': sub_batches[i],
                'start_page': s['start'] + 1,  # Convert to 1-based
                'end_page': s['end'] + 1,      # Convert to 1-based
                'page_count': s['page_count']
            }
            for i, s in enumerate(splits)
        ]
        
        pdf_document.close()
        
        return jsonify({
            'success': True,
            'total_pages': total_pages,
            'separator_pages_0based': separator_page_indices,
            'separator_pages_display': separator_pages_display,
            'batches': splits_display,
            'batch_count': len(splits)
        })
        
    except Exception as e:
        api_logger.error(f"ERROR: {str(e)}")
        import traceback
        api_logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@api_bp.route("/api/batch/split-and-save", methods=["POST"])
def split_and_save_batches():

    """
    Splits PDF into batches and saves to OneDrive
    Expects: pdf_file, batch_folder_id, batch_number, batches (JSON)
    """
    try:
        import os 
        import requests
        api_logger.info("=== Split and Save endpoint called ===")        
        # Get inputs
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400
        
        pdf_file = request.files['pdf_file']
        batch_folder_id = request.form.get('batch_folder_id')  # The Batch-156 folder ID from Node 3
        batch_number = request.form.get('batch_number')  # "156"
        batches_json = request.form.get('batches')  # JSON array from Node 6
        drive_id = request.form.get('drive_id')  # ADD THIS LINE
        
        if not all([batch_folder_id, batch_number, batches_json]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        import json
        batches = json.loads(batches_json)
        
        api_logger.info(f"Processing {len(batches)} batches for Batch-{batch_number}")
        
        # Read PDF
        pdf_bytes = pdf_file.read()
        import fitz
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Get access token for Microsoft Graph API
        import msal
        from datetime import datetime
        import io
        
        # Azure AD token acquisition
        authority = f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}"
        app = msal.ConfidentialClientApplication(
            os.getenv('AZURE_CLIENT_ID'),
            authority=authority,
            client_credential=os.getenv('AZURE_CLIENT_SECRET')
        )
        
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        
        if "access_token" not in result:
            raise Exception(f"Failed to acquire token: {result.get('error_description')}")
        
        access_token = result['access_token']
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        created_folders = []
        created_files = []
        
        # Process each batch
        for batch_info in batches:
            batch_letter = batch_info['batch']
            start_page = batch_info['start_page'] - 1  # Convert to 0-based
            end_page = batch_info['end_page'] - 1      # Convert to 0-based
            
            # Create sub-batch folder name: "Batch 156-A"
            sub_batch_folder_name = f"Batch {batch_number}-{batch_letter}"
            api_logger.info(f"Creating folder: {sub_batch_folder_name}")
            
            # Create folder in OneDrive
            folder_payload = {
                "name": sub_batch_folder_name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "rename"
            }
            
            folder_response = requests.post(
                f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{batch_folder_id}/children"
                headers=headers,
                json=folder_payload
            )
            
            if folder_response.status_code not in [200, 201]:
                api_logger.error(f"Failed to create folder: {folder_response.text}")
                continue
            
            sub_folder_id = folder_response.json()['id']
            created_folders.append(sub_batch_folder_name)
            api_logger.info(f"Created folder ID: {sub_folder_id}")
            
            # Extract and save individual pages
            for page_num in range(start_page, end_page + 1):
                # Create new PDF with single page
                single_page_pdf = fitz.open()
                single_page_pdf.insert_pdf(pdf_document, from_page=page_num, to_page=page_num)
                
                # Convert to bytes
                pdf_bytes_output = single_page_pdf.tobytes()
                single_page_pdf.close()
                
                # File name: "156-A-1.pdf"
                page_number_in_batch = (page_num - start_page) + 1
                file_name = f"{batch_number}-{batch_letter}-{page_number_in_batch}.pdf"
                
                api_logger.info(f"Uploading: {file_name}")
                
                # Upload to OneDrive
                upload_headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/pdf'
                }
                
                upload_response = requests.put(
                    f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{sub_folder_id}:/{file_name}:/content",
                    headers=upload_headers,
                    data=pdf_bytes_output
                ) 
                 
                if upload_response.status_code in [200, 201]:
                    created_files.append(file_name)
                    api_logger.info(f"✓ Uploaded: {file_name}")
                else:
                    api_logger.error(f"Failed to upload {file_name}: {upload_response.text}")
                            
        pdf_document.close()
        
        return jsonify({
            'success': True,
            'batch_number': batch_number,
            'folders_created': len(created_folders),
            'folder_names': created_folders,
            'files_created': len(created_files),
            'total_batches': len(batches)
        })
        
    except Exception as e:
        api_logger.error(f"ERROR in split-and-save: {str(e)}")
        import traceback
        api_logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500



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