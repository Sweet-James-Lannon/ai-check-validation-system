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
import io
from PyPDF2 import PdfMerger
import requests

# =============================================================================
# CONFIGURATION & SETUP
# =============================================================================

api_logger = get_api_logger()
api_bp = Blueprint("api", __name__)

# =============================================================================
# PDF MERGING HELPER - FOR SALESFORCE INTEGRATION
# =============================================================================

def merge_batch_pdfs_and_upload(check_id, batch_images):
    """
    Merge all PDFs from batch_images into a single PDF and upload to Supabase Storage.
    Returns the merged PDF URL for Salesforce integration.
    
    This is critical for Salesforce - Jai's function expects a single merged PDF
    in merged_pdf_url, not individual split pages in batch_images.
    """
    try:
        if not batch_images or len(batch_images) == 0:
            api_logger.warning(f"⚠️ No batch images to merge for check {check_id}")
            return None
        
        api_logger.info(f"🔄 MERGE FUNCTION CALLED: Merging {len(batch_images)} PDFs for check {check_id}")
        
        # If there's only 1 PDF, just copy it as the "merged" PDF
        if len(batch_images) == 1:
            api_logger.info(f"📄 Only 1 PDF found - will copy it as merged PDF")
            pdf_url = batch_images[0].get('url') or batch_images[0].get('primary_url') or batch_images[0].get('download_url')
            
            if pdf_url:
                api_logger.info(f"✅ Single PDF URL will be used as merged_pdf_url: {pdf_url}")
                return pdf_url
            else:
                api_logger.error(f"❌ No URL found in single batch image: {batch_images[0]}")
                return None
        
        api_logger.info(f"🔄 Multiple PDFs detected - proceeding with merge operation")
        
        # Create PDF merger
        merger = PdfMerger()
        
        # Download and add each PDF to the merger
        for idx, img_info in enumerate(batch_images):
            pdf_url = img_info.get('url') or img_info.get('primary_url') or img_info.get('download_url')
            
            if not pdf_url:
                api_logger.warning(f"No URL found for batch image {idx} in check {check_id}")
                continue
            
            try:
                # Download PDF from Supabase Storage
                if '/check-documents/' in pdf_url:
                    storage_path = pdf_url.split('/check-documents/')[1]
                else:
                    api_logger.warning(f"Invalid PDF URL format for check {check_id}, image {idx}: {pdf_url}")
                    continue
                
                api_logger.info(f"  Downloading PDF {idx + 1}/{len(batch_images)}: {storage_path}")
                pdf_data = supabase_service.client.storage.from_('check-documents').download(storage_path)
                
                if not pdf_data:
                    api_logger.warning(f"No data returned for {storage_path}")
                    continue
                
                # Add to merger
                pdf_stream = io.BytesIO(pdf_data)
                merger.append(pdf_stream)
                api_logger.info(f"  ✅ Added PDF {idx + 1} to merger")
                
            except Exception as e:
                api_logger.error(f"Error downloading/merging PDF {idx} for check {check_id}: {str(e)}")
                continue
        
        # Write merged PDF to bytes
        merged_pdf_bytes = io.BytesIO()
        merger.write(merged_pdf_bytes)
        merger.close()
        merged_pdf_bytes.seek(0)
        
        # Generate filename for merged PDF
        merged_filename = f"merged_{check_id}.pdf"
        
        # Upload merged PDF to Supabase Storage
        # Use the same batch folder as the first split PDF
        first_pdf_url = batch_images[0].get('url', '')
        if '/check-documents/' in first_pdf_url:
            batch_folder = first_pdf_url.split('/check-documents/')[1].split('/')[0]
            storage_path = f"{batch_folder}/{merged_filename}"
        else:
            # Fallback to root if we can't determine batch folder
            storage_path = merged_filename
        
        api_logger.info(f"📤 Uploading merged PDF to: {storage_path}")
        
        # Upload to Supabase Storage
        upload_response = supabase_service.client.storage.from_('check-documents').upload(
            storage_path,
            merged_pdf_bytes.getvalue(),
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )
        
        # Get public URL
        merged_url = supabase_service.client.storage.from_('check-documents').get_public_url(storage_path)
        
        api_logger.info(f"✅ Merged PDF uploaded successfully: {merged_url}")
        return merged_url
        
    except Exception as e:
        api_logger.error(f"Error merging PDFs for check {check_id}: {str(e)}")
        import traceback
        api_logger.error(f"Full traceback:\n{traceback.format_exc()}")
        return None

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

        # Map form fields to database fields - Aligned with actual schema
        field_mapping = {
            'pay_to': 'pay_to',
            'amount': 'amount',
            'check_number': 'check_number',
            'check_type': 'check_type',
            'routing_number': 'routing_number',
            'account_number': 'account_number',
            'matter_name': 'matter_name',
            'case_type': 'case_type',
            'delivery_service': 'delivery_service',
            'tracking_number': 'tracking_number',
            'memo': 'memo',
            'policy_number': 'policy_number',
            'claim_number': 'claim_number',
            'insurance_company': 'insurance_company',
            'insurance_id': 'insurance_id',
            'matter_id': 'matter_id',
            'check_issue_date': 'check_issue_date',
            'provider_name': 'provider_name',
            'claimant': 'claimant',
            'insured_name': 'insured_name',
            'reference_number': 'reference_number',
            'date_of_loss': 'date_of_loss',
            'bank_name': 'bank_name',
            'extraction_notes': 'extraction_notes'
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
        
        # 🔥 CHECK TYPE SELECTION - Use provider OR insurance data, not both!
        check_type_selection = data.get('check_type_selection', '').strip()
        api_logger.info(f"Check type selection: '{check_type_selection}'")

        # Map form fields to database fields - Aligned with actual schema
        field_mapping = {
            'pay_to': 'pay_to',
            'amount': 'amount',
            'check_number': 'check_number',
            'check_type': 'check_type',
            'routing_number': 'routing_number',
            'account_number': 'account_number',
            'matter_name': 'matter_name',
            'case_type': 'case_type',
            'delivery_service': 'delivery_service',
            'tracking_number': 'tracking_number',
            'memo': 'memo',
            'policy_number': 'policy_number',
            'claim_number': 'claim_number',
            'insurance_company': 'insurance_company',
            'insurance_id': 'insurance_id',
            'matter_id': 'matter_id',
            'check_issue_date': 'check_issue_date',
            'provider_name': 'provider_name',
            'claimant': 'claimant',
            'insured_name': 'insured_name',
            'reference_number': 'reference_number',
            'date_of_loss': 'date_of_loss',
            'bank_name': 'bank_name',
            'extraction_notes': 'extraction_notes',
            # 🔥 SALESFORCE INSURANCE FIELDS (from right side box)
            'sf_claim_number': 'claim_number',  # Maps to same DB field as provider claim_number
            'sf_policy_number': 'policy_number'  # Maps to same DB field as provider policy_number
        }
        
        # Process form fields
        for form_field, db_field in field_mapping.items():
            if form_field in data and data[form_field] is not None:
                value = data[form_field]
                
                # 🔥 SKIP PROVIDER FIELDS if insurance was selected
                if check_type_selection == 'insurance':
                    if form_field in ['provider_name', 'claim_number', 'policy_number']:
                        api_logger.info(f"Skipping provider field '{form_field}' because insurance was selected")
                        update_data[db_field] = None  # Clear provider data
                        continue
                
                # 🔥 SKIP SALESFORCE INSURANCE FIELDS if provider was selected
                if check_type_selection == 'provider':
                    if form_field in ['insurance_company', 'insurance_id', 'sf_claim_number', 'sf_policy_number']:
                        api_logger.info(f"Skipping insurance field '{form_field}' because provider was selected")
                        update_data[db_field] = None  # Clear insurance data
                        continue
                
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
        
        # 🔥 MERGE PDFs FOR SALESFORCE - Jai's function needs merged_pdf_url, not batch_images
        # Get current check to access batch_images
        api_logger.info(f"🔍 STARTING PDF MERGE PROCESS for check {check_id}")
        check_response = supabase_service.client.table('checks').select('batch_images').eq('id', check_id).single().execute()
        
        api_logger.info(f"🔍 check_response.data: {check_response.data}")
        
        if check_response.data and check_response.data.get('batch_images'):
            batch_images = check_response.data.get('batch_images')
            api_logger.info(f"📋 Found {len(batch_images)} images to merge for check {check_id}")
            api_logger.info(f"📋 batch_images content: {batch_images}")
            
            # Merge PDFs and upload
            api_logger.info(f"🔄 CALLING merge_batch_pdfs_and_upload()...")
            merged_pdf_url = merge_batch_pdfs_and_upload(check_id, batch_images)
            api_logger.info(f"🔄 merge_batch_pdfs_and_upload() RETURNED: {merged_pdf_url}")
            
            if merged_pdf_url:
                api_logger.info(f"✅ Merged PDF URL generated: {merged_pdf_url}")
                update_data['merged_pdf_url'] = merged_pdf_url
                api_logger.info(f"🔧 Added merged_pdf_url to update_data. Will be saved to database.")
                api_logger.info(f"🔧 Current update_data keys: {list(update_data.keys())}")
            else:
                api_logger.warning(f"⚠️ PDF merge RETURNED NULL for check {check_id} - continuing with approval")
                api_logger.warning(f"⚠️ merged_pdf_url will NOT be set in database")
        else:
            api_logger.warning(f"⚠️ No batch_images found for check {check_id} - skipping PDF merge")
            api_logger.warning(f"⚠️ check_response.data: {check_response.data}")
            api_logger.warning(f"⚠️ merged_pdf_url will NOT be set in database")
        
        # Add approval metadata - THIS TRIGGERS THE EDGE FUNCTION
        approval_timestamp = datetime.utcnow().isoformat()
        update_data.update({
            'status': 'approved',
            'validated_at': approval_timestamp,  # ← THIS triggers Jai's edge function (ONLY trigger)
            'validated_by': user.get('preferred_username', 'unknown'),  # ← Capture approving user
            'n8n_sync_enabled': True,  # N8N workflow trigger 
            'updated_at': approval_timestamp,
            'reviewed_by': user.get('preferred_username', 'unknown'),
            'reviewed_at': approval_timestamp
        })
        
        # Update in Supabase
        api_logger.info(f"📝 Updating check {check_id} with {len(update_data)} fields")
        api_logger.info(f"📝 merged_pdf_url in update_data: {'merged_pdf_url' in update_data}")
        
        response = supabase_service.client.table('checks').update(update_data).eq('id', check_id).execute()
        
        if response.data and len(response.data) > 0:
            saved_merged_url = response.data[0].get('merged_pdf_url')
            api_logger.info(f"Check {check_id} APPROVED by {user.get('preferred_username')} - triggering Salesforce protocol")
            api_logger.info(f"✅ merged_pdf_url SAVED to database: {saved_merged_url if saved_merged_url else 'NOT SET'}")
            
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

@api_bp.route("/api/checks/undo-approval/<check_id>", methods=["POST"])
@login_required
def undo_approval(check_id):
    """
    Undo check approval - re-opens check for editing
    Creates duplicate in pending table and keeps original approved record
    """
    try:
        user = session.get("user")
        if not user:
            return jsonify({"status": "error", "message": "User not authenticated"}), 401

        api_logger.info(f"Undoing approval for check {check_id} by {user.get('preferred_username')}")

        # Get the current check data
        current_check_response = supabase_service.client.table('checks')\
            .select('id,file_name,batch_id,batch_id_fk,provider_name,insurance_company,claim_number,policy_number,amount,check_number,check_issue_date,pay_to,routing_number,account_number,memo,matter_name,matter_id,matter_url,case_type,delivery_service,tracking_number,claimant,insured_name,status,confidence_score,flags,validated_at,validated_by,reviewed_at,reviewed_by,created_at,updated_at,batch_images,page_count,check_type,n8n_sync_enabled,image_data,image_mime_type')\
            .eq('id', check_id)\
            .single()\
            .execute()

        if not current_check_response.data:
            return jsonify({"status": "error", "message": "Check not found"}), 404

        current_check = current_check_response.data

        # Verify the check is actually approved
        if current_check.get('status') != 'approved':
            return jsonify({"status": "error", "message": "Check is not approved"}), 400

        # Create a duplicate check with needs_review status
        # Copy all fields except id, status, validated_at, validated_by
        duplicate_data = {
            key: value for key, value in current_check.items()
            if key not in ['id', 'created_at', 'updated_at', 'validated_at', 'validated_by', 'reviewed_at', 'reviewed_by', 'n8n_sync_enabled']
        }

        # Set status to needs_review for the duplicate (not pending)
        duplicate_data['status'] = 'needs_review'
        duplicate_data['created_at'] = datetime.utcnow().isoformat()
        duplicate_data['updated_at'] = datetime.utcnow().isoformat()
        duplicate_data['n8n_sync_enabled'] = False  # Don't sync the duplicate to N8N

        # Insert the duplicate into the checks table
        duplicate_response = supabase_service.client.table('checks').insert(duplicate_data).execute()

        if not duplicate_response.data:
            api_logger.error(f"Failed to create duplicate check for {check_id}")
            return jsonify({"status": "error", "message": "Failed to create duplicate check"}), 500

        api_logger.info(f"Created duplicate check {duplicate_response.data[0]['id']} from approved check {check_id} with status=needs_review")

        # Note: We do NOT modify the original approved record
        # It stays in the approved table with its validated_at timestamp intact

        return jsonify({
            "status": "success",
            "message": "Approval undone successfully",
            "duplicate_check_id": duplicate_response.data[0]['id'],
            "new_status": "needs_review"
        })

    except Exception as e:
        api_logger.error(f"Error undoing approval for check {check_id}: {str(e)}")
        import traceback
        api_logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

@api_bp.route("/api/checks/split/<check_id>", methods=["POST"])
@login_required
def split_check(check_id):
    """
    Split a check into two separate records by moving selected pages to a new check

    Request body: {
        "selected_page_indices": [0, 1, 2]  # Array of page indices to move to new check
    }

    Returns: {
        "status": "success",
        "new_check_id": "uuid",
        "new_check_identifier": "156-D",
        "remaining_pages": 3,
        "split_pages": 2
    }
    """
    try:
        user = session.get("user")
        if not user:
            return jsonify({"status": "error", "message": "User not authenticated"}), 401

        # Get selected page indices from request
        data = request.json
        selected_indices = data.get('selected_page_indices', [])

        if not selected_indices:
            return jsonify({"status": "error", "message": "No pages selected for split"}), 400

        api_logger.info(f"Splitting check {check_id} - moving {len(selected_indices)} pages")
        api_logger.info(f"Selected page indices: {selected_indices}")

        # Fetch current check
        response = supabase_service.client.table('checks').select('id,file_name,batch_id,batch_id_fk,provider_name,insurance_company,claim_number,policy_number,amount,check_number,check_issue_date,pay_to,routing_number,account_number,memo,matter_name,matter_id,matter_url,case_type,delivery_service,tracking_number,claimant,insured_name,status,confidence_score,flags,validated_at,validated_by,reviewed_at,reviewed_by,created_at,updated_at,batch_images,page_count,check_type,n8n_sync_enabled,image_data,image_mime_type').eq('id', check_id).single().execute()

        if not response.data:
            return jsonify({"status": "error", "message": "Check not found"}), 404

        current_check = response.data
        batch_images = current_check.get('batch_images', [])

        # Validate selection
        if not batch_images:
            return jsonify({"status": "error", "message": "No pages found in current check"}), 400

        if len(selected_indices) >= len(batch_images):
            return jsonify({"status": "error", "message": "Cannot split all pages - at least one page must remain"}), 400

        # Validate all indices are valid
        if any(idx < 0 or idx >= len(batch_images) for idx in selected_indices):
            return jsonify({"status": "error", "message": "Invalid page index selected"}), 400

        # Split batch_images array - maintain order
        split_images = [batch_images[i] for i in sorted(selected_indices)]
        remaining_images = [batch_images[i] for i in range(len(batch_images)) if i not in selected_indices]

        api_logger.info(f"📄 Total pages before split: {len(batch_images)}")
        api_logger.info(f"📄 Selected indices (will be REMOVED from original): {sorted(selected_indices)}")
        api_logger.info(f"📄 Remaining indices (will STAY in original): {[i for i in range(len(batch_images)) if i not in selected_indices]}")
        api_logger.info(f"📄 Split pages (going to NEW check): {len(split_images)} pages")
        api_logger.info(f"📄 Remaining pages (staying in ORIGINAL): {len(remaining_images)} pages")

        # Log ALL pages with their filenames/URLs to verify correctsplit
        api_logger.info("📄 === ORIGINAL BATCH IMAGES ===")
        for idx, img in enumerate(batch_images):
            filename = img.get('filename') or img.get('file_name') or 'unknown'
            api_logger.info(f"   Index {idx}: {filename}")
        
        api_logger.info("📄 === SPLIT IMAGES (going to NEW check) ===")
        for idx, img in enumerate(split_images):
            filename = img.get('filename') or img.get('file_name') or 'unknown'
            api_logger.info(f"   Index {idx}: {filename}")
        
        api_logger.info("📄 === REMAINING IMAGES (staying in ORIGINAL check) ===")
        for idx, img in enumerate(remaining_images):
            filename = img.get('filename') or img.get('file_name') or 'unknown'
            api_logger.info(f"   Index {idx}: {filename}")

        # Extract check number from file_name (e.g., "156-002.pdf" -> "002")
        current_file_name = current_check.get('file_name', '')
        api_logger.info(f"Current file_name: {current_file_name}")

        # Parse the check number from file_name
        # Format is typically: {batch}-{check_num}.pdf or {batch}-{check_num}-{suffix}.pdf
        check_num = None
        current_suffix = None
        if current_file_name:
            # Remove .pdf and COMPLETE suffix
            clean_name = current_file_name.replace('.pdf', '').replace('-COMPLETE', '')
            parts = clean_name.split('-')
            if len(parts) >= 2:
                # Get the second part (check number)
                check_num = parts[1]  # e.g., "001", "002", "003"
            if len(parts) >= 3:
                # Check if there's already a suffix (main, 2, 3, etc.)
                current_suffix = parts[2]
                # 🔥 TREAT "-1" AS NO SUFFIX (it's from old upload convention)
                # When splitting a "-1" check, rename it to "-main" like any unsplit check
                if current_suffix == "1":
                    api_logger.info(f"Found '-1' suffix (old upload convention), treating as unsplit check")
                    current_suffix = None  # Treat as if it has no suffix
                else:
                    api_logger.info(f"Current check already has suffix: {current_suffix}")

        api_logger.info(f"Extracted check number: {check_num}, current suffix: {current_suffix}")

        # Determine batch prefix for searching existing splits
        batch_prefix = current_file_name.split('-')[0] if '-' in current_file_name else ''

        # Find how many splits already exist for this check number
        split_count = 2  # First split always creates 002-main and 002-2
        if check_num and batch_prefix:
            # Search for existing splits with pattern: {batch}-{check_num}-{suffix}
            # e.g., "156-002-main", "156-002-2", "156-002-3"
            search_pattern = f"{batch_prefix}-{check_num}-%"
            try:
                existing_splits_response = supabase_service.client.table('checks')\
                    .select('file_name')\
                    .like('file_name', search_pattern)\
                    .execute()

                if existing_splits_response.data:
                    # Extract numeric split suffixes from existing splits
                    split_numbers = []
                    for check in existing_splits_response.data:
                        fn = check.get('file_name', '')
                        # Extract the suffix (e.g., "156-002-2.pdf" -> 2)
                        parts = fn.replace('.pdf', '').replace('-COMPLETE', '').split('-')
                        if len(parts) >= 3:
                            suffix = parts[2]
                            # Only count numeric suffixes (not "main")
                            if suffix != "main":
                                try:
                                    split_num = int(suffix)
                                    split_numbers.append(split_num)
                                except ValueError:
                                    pass

                    if split_numbers:
                        # Use the highest split number + 1
                        split_count = max(split_numbers) + 1
                        api_logger.info(f"Found existing numeric splits: {split_numbers}, using split count: {split_count}")
                    else:
                        # Only "main" exists, so this is the second split
                        split_count = 2
            except Exception as query_error:
                api_logger.warning(f"Error querying existing splits: {query_error}, defaulting to split count 2")
                split_count = 2

        # Generate the new split check number and original check name
        if check_num:
            new_check_num = f"{check_num}-{split_count}"  # e.g., "002-2", "002-3"
            # Rename original to "main" if it doesn't already have a suffix
            if current_suffix is None:
                original_check_num = f"{check_num}-main"  # Original becomes "002-main"
            elif current_suffix == "main":
                # Already has "main" suffix, keep it
                original_check_num = f"{check_num}-main"
            else:
                # Keep the current suffix (e.g., if splitting "002-2", it stays "002-2")
                original_check_num = f"{check_num}-{current_suffix}"
        else:
            # Fallback if no check number found
            new_check_num = "SPLIT"
            original_check_num = check_num

        api_logger.info(f"Original check will be renamed to: {original_check_num}")
        api_logger.info(f"New split check number: {new_check_num}")

        # Create new check record (only copy safe fields to avoid schema errors)
        # Fields to explicitly exclude (timestamps, validation, system fields, form-only fields, and batch_images)
        exclude_fields = {
            'id', 'created_at', 'updated_at', 'validated_at', 'validated_by',
            'reviewed_at', 'reviewed_by', 'n8n_sync_enabled', 'check_type_selection',
            'batch_images', 'amount'  # Exclude batch_images (will set filtered version) and amount (will reset to 0)
        }

        new_check_data = {
            key: value for key, value in current_check.items()
            if key not in exclude_fields
        }

        # Update fields for new check
        new_check_data.update({
            'batch_images': split_images,  # Use filtered images for selected pages only
            'page_count': len(split_images),
            'amount': 0.0,  # Reset amount so user can fill it in
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'n8n_sync_enabled': False
        })

        # Set the split file_name (e.g., "156-001-2.pdf" for a split from "156-001.pdf")
        if check_num and current_file_name:
            # Generate new file_name with split suffix
            batch_part = current_file_name.split('-')[0] if '-' in current_file_name else ''
            new_file_name = f"{batch_part}-{new_check_num}.pdf" if batch_part else f"{new_check_num}.pdf"
            new_check_data['file_name'] = new_file_name
            api_logger.info(f"New check file_name: {new_file_name}")

        # Insert new check
        api_logger.info(f"Inserting new check record...")
        api_logger.info(f"New check data keys: {list(new_check_data.keys())}")

        try:
            new_check_response = supabase_service.client.table('checks').insert(new_check_data).execute()
        except Exception as insert_error:
            api_logger.error(f"Insert error: {str(insert_error)}")
            # If insert fails due to schema, try with minimal fields
            api_logger.info("Retrying with minimal field set...")
            minimal_data = {
                'batch_images': split_images,
                'page_count': len(split_images),
                'status': 'pending',
                'batch_id_fk': current_check.get('batch_id_fk'),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            # Add optional fields if they exist
            if 'check_letter' in current_check:
                minimal_data['check_letter'] = current_check.get('check_letter')
            if 'batch_id' in current_check:
                minimal_data['batch_id'] = current_check['batch_id']

            # Set the file_name for the new split check
            if check_num and batch_prefix:
                new_file_name = f"{batch_prefix}-{new_check_num}.pdf"
                minimal_data['file_name'] = new_file_name
                api_logger.info(f"Minimal data - New check file_name: {new_file_name}")

            new_check_response = supabase_service.client.table('checks').insert(minimal_data).execute()

        if not new_check_response.data:
            return jsonify({"status": "error", "message": "Failed to create new check"}), 500

        new_check = new_check_response.data[0]
        new_check_id = new_check['id']

        api_logger.info(f"✅ New check created: {new_check_id} ({new_check_num})")

        # Update current check - remove split pages and rename to -1 suffix if needed
        api_logger.info(f"📄 === BEFORE UPDATE TO ORIGINAL CHECK ===")
        api_logger.info(f"📄 Original batch_images had: {len(batch_images)} pages")
        api_logger.info(f"📄 Will update with remaining_images: {len(remaining_images)} pages")
        
        update_data = {
            'batch_images': remaining_images,
            'page_count': len(remaining_images),
            'updated_at': datetime.utcnow().isoformat()
        }

        # Rename the original check to include -main suffix only if it doesn't already have a suffix
        # (e.g., "156-002.pdf" -> "156-002-main.pdf", but "156-002-main.pdf" stays "156-002-main.pdf")
        if check_num and batch_prefix and original_check_num and current_suffix is None:
            original_file_name = f"{batch_prefix}-{original_check_num}.pdf"
            update_data['file_name'] = original_file_name
            api_logger.info(f"Renaming original check to: {original_file_name}")
        elif current_suffix is not None:
            api_logger.info(f"Original check already has suffix '{current_suffix}', keeping file_name unchanged")

        api_logger.info(f"📄 === UPDATING ORIGINAL CHECK {check_id} ===")
        api_logger.info(f"📄 Update data - page_count: {update_data['page_count']}")
        api_logger.info(f"📄 Update data - batch_images length: {len(update_data['batch_images'])}")
        
        update_response = supabase_service.client.table('checks').update(update_data).eq('id', check_id).execute()

        if not update_response.data:
            # Rollback - delete the new check we just created
            api_logger.error(f"❌ Failed to update current check - rolling back")
            supabase_service.client.table('checks').delete().eq('id', new_check_id).execute()
            return jsonify({"status": "error", "message": "Failed to update current check"}), 500

        api_logger.info(f"✅ Current check updated successfully")
        
        # Verify the update by logging what came back
        updated_check = update_response.data[0]
        api_logger.info(f"📄 === AFTER UPDATE - VERIFICATION ===")
        api_logger.info(f"📄 Updated check page_count: {updated_check.get('page_count')}")
        api_logger.info(f"📄 Updated check batch_images length: {len(updated_check.get('batch_images', []))}")
        if updated_check.get('batch_images'):
            api_logger.info(f"📄 First page of updated check: {updated_check['batch_images'][0].get('filename') or updated_check['batch_images'][0].get('file_name')}")

        # Get the actual identifier from the created check
        # Prefer file_name over check_identifier for display
        display_name = new_check.get('file_name', new_check_num)
        if display_name:
            # Clean up for display (remove .pdf)
            display_name = display_name.replace('.pdf', '')

        return jsonify({
            "status": "success",
            "message": f"Check split successfully into {display_name}",
            "new_check_id": new_check_id,
            "new_check_identifier": display_name,
            "new_check_number": new_check_num,
            "current_check_id": check_id,
            "split_pages": len(split_images),
            "remaining_pages": len(remaining_images)
        })

    except Exception as e:
        api_logger.error(f"Error splitting check {check_id}: {str(e)}")
        import traceback
        api_logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

@api_bp.route("/api/checks/delete/<check_id>", methods=["DELETE"])
@login_required
def delete_check(check_id):
    """
    Delete a check from the database
    Permanently removes the check record from Supabase
    """
    try:
        user = session.get("user")
        if not user:
            return jsonify({"status": "error", "message": "User not authenticated"}), 401

        api_logger.info(f"Deleting check {check_id} by {user.get('preferred_username')}")

        # Delete the check from Supabase
        response = supabase_service.client.table('checks')\
            .delete()\
            .eq('id', check_id)\
            .execute()

        # Check if deletion was successful
        if response.data or not response.data:  # Supabase returns empty array on successful delete
            api_logger.info(f"Successfully deleted check {check_id}")
            return jsonify({
                "status": "success",
                "message": "Check deleted successfully"
            })
        else:
            api_logger.error(f"Failed to delete check {check_id}")
            return jsonify({"status": "error", "message": "Failed to delete check"}), 500

    except Exception as e:
        api_logger.error(f"Error deleting check {check_id}: {str(e)}")
        import traceback
        api_logger.error(traceback.format_exc())
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
        
        # Include any form field updates (but exclude form-only fields that don't exist in database)
        # Date fields that need special handling (empty string -> None)
        date_fields = ['check_issue_date', 'date_of_loss']

        for field, value in form_data.items():
            if field not in ['status', 'updated_at', 'reason', 'check_type_selection', 'sf_claim_number', 'sf_policy_number']:
                # Convert empty strings to None for date fields
                if field in date_fields and value == '':
                    update_data[field] = None
                else:
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
        response = supabase_service.client.table('checks').select('id,file_name,batch_id,batch_id_fk,provider_name,insurance_company,claim_number,policy_number,amount,check_number,check_issue_date,pay_to,routing_number,account_number,memo,matter_name,matter_id,matter_url,case_type,delivery_service,tracking_number,claimant,insured_name,status,confidence_score,flags,validated_at,validated_by,reviewed_at,reviewed_by,created_at,updated_at,batch_images,page_count,check_type,n8n_sync_enabled,image_data,image_mime_type').eq('id', check_id).single().execute()
        
        if response.data:
            # Ensure provider_name is available (fallback to pay_to or claimant)
            if not response.data.get('provider_name'):
                response.data['provider_name'] = response.data.get('pay_to') or response.data.get('claimant')
            
            return jsonify({
                "status": "success",
                "check": response.data
            })
        else:
            return jsonify({"status": "error", "message": "Check not found"}), 404
            
    except Exception as e:
        api_logger.error(f"Error getting check {check_id}: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route("/api/claimants/list", methods=["GET"])
@login_required
def get_claimants_list():
    """
    FALLBACK: Get unique list of claimant names from Supabase
    Used for testing or when Salesforce is unavailable
    """
    try:
        api_logger.info("Fetching unique claimant names from Supabase (fallback)")
        
        # Get all checks with claimant data
        response = supabase_service.client.table('checks')\
            .select('claimant')\
            .not_.is_('claimant', 'null')\
            .execute()
        
        if not response.data:
            return jsonify({
                "status": "success",
                "claimants": [],
                "source": "supabase"
            })
        
        # Extract unique claimant names (filter out None, empty, "None" strings)
        claimants_set = set()
        for check in response.data:
            claimant = check.get('claimant', '').strip()
            if claimant and claimant.lower() not in ['none', 'null', '']:
                claimants_set.add(claimant)
        
        # Sort alphabetically
        unique_claimants = sorted(list(claimants_set))
        
        api_logger.info(f"Returning {len(unique_claimants)} unique claimant names from Supabase")
        
        return jsonify({
            "status": "success",
            "claimants": unique_claimants,
            "total": len(unique_claimants),
            "source": "supabase"
        })
        
    except Exception as e:
        api_logger.error(f"Error fetching claimants list: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route("/api/salesforce/claimant-lookup", methods=["POST"])
@login_required
def salesforce_claimant_lookup():
    """
    🔥 SALESFORCE: Fetch matter data from Salesforce
    Uses Jai's Salesforce endpoint to get claimant, matter_name, and matter_id
    
    POST body: {"claimant_name": "Jose Martinez"}
    
    Returns: {
        "status": "success",
        "claimant": "Jose Martinez",
        "matter_name": "Martinez v. State Farm",
        "matter_id": "500..."
    }
    
    Salesforce Endpoint (configured):
        URL: https://sweetjames--sjfull.sandbox.my.salesforce-sites.com/SmartReceptionAI/services/apexrest/AI_Flask_App_Fetch_Matter
        Method: GET
        Token: 00DEc00000H8mAZMAZ
    """
    try:
        import os
        import requests
        
        data = request.get_json()
        claimant_name = data.get('claimant_name', '').strip()
        
        if not claimant_name:
            return jsonify({
                "status": "error",
                "message": "No claimant name provided"
            }), 400
        
        api_logger.info(f"🔍 Salesforce lookup for: '{claimant_name}'")
        
        # =============================================================================
        # SALESFORCE CONFIGURATION
        # =============================================================================
        
        # Jai's Salesforce endpoint
        salesforce_url = "https://sweetjames.my.salesforce-sites.com/SmartAgent/services/apexrest/AI_Flask_App_Fetch_Matter"
        salesforce_token = "00D5f000000JpstEAC"
            
        # =============================================================================
        # Call Salesforce API
        # =============================================================================
        
        # Payload format from Jai's specs (GET request with JSON body)
        payload = {  
            'searchKey': claimant_name,
            'token': salesforce_token
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        api_logger.info(f"Calling Salesforce API with searchKey: {claimant_name}")
             
        # Note: GET request with JSON body (unusual but that's what Salesforce wants)
        response = requests.request(
            'GET',
            salesforce_url,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        response.raise_for_status()  # Raise error for bad status codes
        
        result = response.json()
        
        api_logger.info(f"✅ Salesforce API response: {result}")
        
        # Parse Salesforce response
        # Salesforce returns an array of matches with these field names:
        # - ClaimentName (note the typo - "Claiment" not "Claimant")
        # - MatterName
        # - MatterId
        
        # Take the first match if multiple results
        if isinstance(result, list) and len(result) > 0:
            first_match = result[0]

            # Extract insurance numbers from Insurances array
            insurances = first_match.get('Insurances', [])
            insurance_numbers = []

            if isinstance(insurances, list):
                api_logger.info(f"🔍 [SINGLE MATCH] Insurances is a list with {len(insurances)} items")
                for insurance in insurances:
                    api_logger.info(f"🔍 [SINGLE MATCH] Processing insurance item: {insurance}")
                    api_logger.info(f"🔑 [SINGLE MATCH] Available keys in insurance object: {list(insurance.keys())}")
                    claim_num = insurance.get('ClaimNumber')
                    policy_num = insurance.get('PolicyNumber')
                    insurance_id = insurance.get('InsuranceId', '')
                    insurance_company_name = insurance.get('InsuranceCompanyName', '')
                    insurance_company_id = insurance.get('InsuranceCompanyId', '')
                    api_logger.info(f"🔍 [SINGLE MATCH] Extracted - Claim: {claim_num}, Policy: {policy_num}, Company: {insurance_company_name}, InsuranceId: {insurance_id}")

                    if claim_num:
                        insurance_numbers.append({
                            'type': 'claim',
                            'number': claim_num,
                            'insurance_id': insurance_id,
                            'insurance_company_name': insurance_company_name,
                            'insurance_company_id': insurance_company_id
                        })

                    if policy_num:
                        insurance_numbers.append({
                            'type': 'policy',
                            'number': policy_num,
                            'insurance_id': insurance_id,
                            'insurance_company_name': insurance_company_name,
                            'insurance_company_id': insurance_company_id
                        })

            return jsonify({
                "status": "success",
                "claimant": first_match.get('ClaimentName') or claimant_name,
                "matter_name": first_match.get('MatterName') or '',
                "matter_id": first_match.get('MatterId') or '',
                "matter_url": first_match.get('matterUrl') or '',  # Field name is 'matterUrl' (camelCase)
                "date_of_birth": first_match.get('DOB') or '',  # Field name is DOB (uppercase)
                "stage": first_match.get('Stage') or '',
                "insurance_numbers": insurance_numbers  # Array of insurance objects
            })
        else:
            # No matches found
            return jsonify({
                "status": "success",
                "claimant": claimant_name,
                "matter_name": "",
                "matter_id": "",
                "matter_url": "",  # No URL when no match
                "date_of_birth": "",
                "stage": "",
                "insurance_numbers": [],  # Empty array
                "message": "No matches found in Salesforce"
            })
        
    except requests.exceptions.Timeout:
        api_logger.error("Salesforce API timeout")
        return jsonify({
            "status": "error",
            "message": "Salesforce request timed out"
        }), 504
        
    except requests.exceptions.RequestException as e:
        api_logger.error(f"Salesforce API error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Salesforce connection failed: {str(e)}"
        }), 500
        
    except Exception as e:
        api_logger.error(f"Salesforce lookup error: {str(e)}")
        import traceback
        api_logger.error(traceback.format_exc())
        
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api_bp.route("/api/salesforce/search", methods=["GET"])
@login_required
def salesforce_search_claimants():
    """
    🔥 REAL-TIME SEARCH: Search Salesforce as user types
    Returns full matter data for each match
    
    =============================================================================
    🚨 JAI: UPDATE SOQL TO SEARCH MATTER NAME FIELD! 🚨
    =============================================================================
    Current SOQL: Searches ClaimentName field
    Needed SOQL: Search MatterName field (or BOTH ClaimentName AND MatterName)
    
    Example SOQL:
    SELECT ClaimentName__c, MatterName__c, Id 
    FROM Matter__c 
    WHERE MatterName__c LIKE '%{searchKey}%' 
    OR ClaimentName__c LIKE '%{searchKey}%'
    
    Frontend is ALREADY set up to handle this! No frontend changes needed!
    =============================================================================
    
    Query params: ?q=auto accident
    
    Returns: {
        "status": "success",
        "results": [
            {
                "claimant": "Rebecca Smith",
                "matter_name": "Rebecca Smith | CA | 1/1/24 | Auto",
                "matter_id": "a0L5f0000058N4j"
            }
        ],
        "total": 5
    }
    """
    try:
        import requests
        
        search_query = request.args.get('q', '').strip()
        
        # Minimum 2 characters
        if len(search_query) < 2:
            return jsonify({
                "status": "success",
                "results": [],
                "total": 0,
                "message": "Type at least 2 characters"
            })
        
        api_logger.info(f"🔍 Real-time Salesforce search: '{search_query}'")
        
        # Salesforce configuration
        salesforce_url = "https://sweetjames.my.salesforce-sites.com/SmartAgent/services/apexrest/AI_Flask_App_Fetch_Matter"
        salesforce_token = "00D5f000000JpstEAC"
        
        # Call Salesforce
        payload = {
            'searchKey': search_query,
            'token': salesforce_token
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        response = requests.request(
            'GET',
            salesforce_url,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        response.raise_for_status()
        result = response.json()
        
        # 📦 LOG FULL SALESFORCE RESPONSE PAYLOAD
        api_logger.info(f"📦 FULL Salesforce Response Payload:")
        api_logger.info(f"   Type: {type(result)}")
        api_logger.info(f"   Length: {len(result) if isinstance(result, list) else 'N/A'}")
        import json
        api_logger.info(f"   Complete JSON:\n{json.dumps(result, indent=2)}")
        
        # 🔥 Extract from jsonResponse array
        # Salesforce returns: {jsonResponse: [{...data...}]}
        results = []
        if isinstance(result, dict) and 'jsonResponse' in result:
            json_response = result.get('jsonResponse', [])
            if isinstance(json_response, list) and len(json_response) > 0:
                results = json_response  # Array of Salesforce records
        
        api_logger.info(f"✅ Returning {len(results)} Salesforce records for '{search_query}'")
        
        return jsonify({
            "status": "success",
            "results": results,
            "total": len(results),
            "source": "salesforce"
        })
        
    except Exception as e:
        api_logger.error(f"Salesforce search error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "claimants": [],
            "total": 0
        }), 500
        
    except requests.exceptions.Timeout:
        api_logger.error("Salesforce API timeout")
        return jsonify({
            "status": "error",
            "message": "Salesforce request timed out"
        }), 504
        
    except requests.exceptions.RequestException as e:
        api_logger.error(f"Salesforce API error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Salesforce connection failed: {str(e)}"
        }), 500
        
    except Exception as e:
        api_logger.error(f"Salesforce lookup error: {str(e)}")
        import traceback
        api_logger.error(traceback.format_exc())
              
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

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

@api_bp.route("/api/batches/<batch_id>/checks", methods=["GET"])
def get_batch_checks(batch_id):
    """Get all checks for a specific batch - AJAX endpoint (no auth required, page is already protected)"""
    try:
        api_logger.info(f"API: Loading checks for batch {batch_id}")
        
        response = supabase_service.client.table('checks')\
            .select('id,file_name,batch_id,batch_id_fk,provider_name,insurance_company,claim_number,policy_number,amount,check_number,check_issue_date,pay_to,routing_number,account_number,memo,matter_name,matter_id,matter_url,case_type,delivery_service,tracking_number,claimant,insured_name,status,confidence_score,flags,validated_at,validated_by,reviewed_at,reviewed_by,created_at,updated_at,batch_images,page_count')\
            .eq('batch_id', batch_id)\
            .order('created_at', desc=True)\
            .execute()
        
        # Format checks for display
        formatted_checks = []
        for check in response.data:
            formatted_check = check.copy()
            confidence_score = check.get('confidence_score', 0)
            formatted_check['confidence_percentage'] = round(confidence_score * 100, 1) if confidence_score else 0
            formatted_checks.append(formatted_check)
        
        api_logger.info(f"API: Returning {len(formatted_checks)} checks for batch {batch_id}")
        
        return jsonify({
            "status": "success",
            "checks": formatted_checks,
            "total": len(formatted_checks),
            "batch_id": batch_id
        })
        
    except Exception as e:
        api_logger.error(f"Error getting batch checks: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route("/api/checks/<check_id>/pages", methods=["GET"])
@login_required
def get_check_pages(check_id):
    """Get all pages for a specific check - AJAX endpoint"""
    try:
        api_logger.info(f"API: Loading pages for check {check_id}")
        
        response = supabase_service.client.table('check_pages')\
            .select('*')\
            .eq('check_id', check_id)\
            .order('page_number')\
            .execute()
        
        api_logger.info(f"API: Returning {len(response.data) if response.data else 0} pages for check {check_id}")
        
        return jsonify({
            "status": "success",
            "pages": response.data,
            "total": len(response.data) if response.data else 0,
            "check_id": check_id
        })
        
    except Exception as e:
        api_logger.error(f"Error getting check pages: {str(e)}")
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
        
        # Generate sub-batch labels using 3-digit numeric format (001, 002, 003, etc.)
        sub_batches = [f"{i+1:03d}" for i in range(len(splits))]
        
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

@api_bp.route("/api/batch/split-pages", methods=["POST"]) 
def split_pages():
    """
    Splits PDF into individual pages AND creates COMPLETE PDFs for each batch
    n8n will handle the folder creation and uploads
    """
    try:
        api_logger.info("=== Split Pages endpoint called ===")
        
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400
        
        pdf_file = request.files['pdf_file']
        batch_number = request.form.get('batch_number')
        batches_json = request.form.get('batches')
        
        if not all([batch_number, batches_json]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        import json
        import base64
        batches = json.loads(batches_json)
        
        # Read PDF
        pdf_bytes = pdf_file.read()
        import fitz
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        pages_data = []
        
        # Process each batch
        for batch_info in batches:
            batch_letter = batch_info['batch'] 
            start_page = batch_info['start_page'] - 1
            end_page = batch_info['end_page'] - 1
            
            # Create COMPLETE PDF first (all pages in this check combined)
            complete_pdf = fitz.open()
            for page_num in range(start_page, end_page + 1):
                complete_pdf.insert_pdf(pdf_document, from_page=page_num, to_page=page_num)
            
            complete_pdf_bytes = complete_pdf.tobytes()
            complete_pdf.close()
            
            complete_file_name = f"{batch_number}-{batch_letter}-COMPLETE.pdf"
            
            pages_data.append({
                'batch': batch_letter,
                'batch_folder': f"Batch {batch_number}-{batch_letter}",
                'file_name': complete_file_name,
                'page_number': 'COMPLETE',
                'data': base64.b64encode(complete_pdf_bytes).decode('utf-8')
            })
            
            # Extract each individual page in this batch        
            for page_num in range(start_page, end_page + 1):
                # Create single-page PDF
                single_page_pdf = fitz.open()
                single_page_pdf.insert_pdf(pdf_document, from_page=page_num, to_page=page_num)
                pdf_bytes_output = single_page_pdf.tobytes()
                single_page_pdf.close()
                
                page_number_in_batch = (page_num - start_page) + 1
                file_name = f"{batch_number}-{batch_letter}-{page_number_in_batch}.pdf"
                
                pages_data.append({
                    'batch': batch_letter,
                    'batch_folder': f"Batch {batch_number}-{batch_letter}",
                    'file_name': file_name,
                    'page_number': page_number_in_batch,
                    'data': base64.b64encode(pdf_bytes_output).decode('utf-8')
                })
        
        pdf_document.close()
        
        return jsonify({
            'success': True,
            'batch_number': batch_number,
            'total_pages': len(pages_data),
            'pages': pages_data
        })
        
    except Exception as e:
        api_logger.error(f"ERROR in split-pages: {str(e)}")
        import traceback
        api_logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@api_bp.route("/api/batch/ingest", methods=["POST"])
def ingest_batch():
    """
    Receives batch metadata from n8n and stores in Supabase
    
    Expected JSON payload:
    {
      "batch_number": "156",
      "batch_date": "2025-10-01",
      "folder_name": "2025_10_01-BATCH-156",
      "onedrive_folder_id": "xyz123",
      "checks": [
        {
          "letter": "A",
          "subfolder_name": "Batch 156-A",
          "onedrive_folder_id": "abc456",
          "pages": [
            {"page_number": 1, "file_name": "156-A-1.pdf", "onedrive_file_id": "file1"},
            {"page_number": 2, "file_name": "156-A-2.pdf", "onedrive_file_id": "file2"}
          ]
        }
      ]
    }
    """
    try:
        data = request.get_json()
        api_logger.info(f"=== Ingesting batch: {data.get('batch_number')} ===")
        
        # 1. Check if batch already exists
        existing_batch = supabase_service.client.table('batches')\
            .select('id')\
            .eq('folder_name', data['folder_name'])\
            .execute()
        
        if existing_batch.data:
            api_logger.info(f"Batch {data['folder_name']} already exists, skipping")
            return jsonify({
                'success': True,
                'message': 'Batch already exists',
                'batch_id': existing_batch.data[0]['id']
            }), 200
        
        # 2. Create batch record
        batch_result = supabase_service.client.table('batches').insert({
            'batch_number': data['batch_number'],
            'batch_date': data['batch_date'],
            'folder_name': data['folder_name'],
            'onedrive_folder_id': data['onedrive_folder_id'],
            'total_checks': len(data['checks'])
        }).execute()
        
        batch_id = batch_result.data[0]['id']
        api_logger.info(f"Created batch record: {batch_id}")
        
        # 3. Create check records
        checks_created = 0
        pages_created = 0
        
        for check_data in data['checks']:
            check_identifier = f"{data['batch_number']}-{check_data['letter']}"
            
            # Insert check
            check_result = supabase_service.client.table('checks').insert({
                'batch_id_fk': batch_id,
                'check_letter': check_data['letter'],
                'check_identifier': check_identifier,
                'subfolder_name': check_data['subfolder_name'],
                'onedrive_folder_id': check_data['onedrive_folder_id'],
                'page_count': len(check_data['pages']),
                'status': 'pending',
                'check_view_status': 'pending'
            }).execute()
            
            check_id = check_result.data[0]['id']
            checks_created += 1
            api_logger.info(f"Created check: {check_identifier}")
            
            # 4. Create check_pages records
            pages_to_insert = [
                {
                    'check_id': check_id,
                    'page_number': page['page_number'],
                    'file_name': page['file_name'],
                    'onedrive_file_id': page['onedrive_file_id']
                }
                for page in check_data['pages']
            ] 
            
            if pages_to_insert:
                supabase_service.client.table('check_pages').insert(pages_to_insert).execute()
                pages_created += len(pages_to_insert)
        
        api_logger.info(f"✅ Batch ingestion complete: {checks_created} checks, {pages_created} pages")
        
        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'checks_created': checks_created,
            'pages_created': pages_created
        }), 201
        
    except Exception as e:
        api_logger.error(f"ERROR in batch ingestion: {str(e)}")
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