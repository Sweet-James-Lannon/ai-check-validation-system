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
            'memo': 'memo',
            'policy_number': 'policy_number',
            'claim_number': 'claim_number',
            'insurance_company': 'insurance_company',
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
            'memo': 'memo',
            'policy_number': 'policy_number',
            'claim_number': 'claim_number',
            'insurance_company': 'insurance_company',
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
            'n8n_sync_enabled': True,  # N8N workflow trigger 
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
        response = supabase_service.client.table('checks').select('*, provider_name, pay_to, claimant').eq('id', check_id).single().execute()
        
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
        salesforce_url = "https://sweetjames--sjfull.sandbox.my.salesforce-sites.com/SmartReceptionAI/services/apexrest/AI_Flask_App_Fetch_Matter"
        salesforce_token = "00DEc00000H8mAZMAZ"
        
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
            
            return jsonify({
                "status": "success",
                "claimant": first_match.get('ClaimentName', claimant_name),
                "matter_name": first_match.get('MatterName', ''),
                "matter_id": first_match.get('MatterId', '')
            })
        else:
            # No matches found
            return jsonify({
                "status": "success",
                "claimant": claimant_name,
                "matter_name": "",
                "matter_id": "",
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
        salesforce_url = "https://sweetjames--sjfull.sandbox.my.salesforce-sites.com/SmartReceptionAI/services/apexrest/AI_Flask_App_Fetch_Matter"
        salesforce_token = "00DEc00000H8mAZMAZ"
        
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
        
        # Extract full matter data with unique claimant names
        results = []
        seen = set()
        
        if isinstance(result, list):
            for item in result:
                claimant_name = item.get('ClaimentName', '').strip()
                matter_name = item.get('MatterName', '').strip()
                matter_id = item.get('MatterId', '').strip()
                
                # Only add unique claimants with complete data
                if claimant_name and claimant_name not in seen:
                    results.append({
                        'claimant': claimant_name,
                        'matter_name': matter_name,
                        'matter_id': matter_id
                    })
                    seen.add(claimant_name)
        
        api_logger.info(f"✅ Found {len(results)} Salesforce matches for '{search_query}'")
        
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
            .select('*')\
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