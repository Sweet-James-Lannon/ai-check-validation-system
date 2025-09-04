from flask import Blueprint, request, jsonify
import secrets
import os
import json
from datetime import datetime
from utils.logger import get_api_logger
from config import Config



automation_bp = Blueprint("automation", __name__)
api_logger = get_api_logger()
config = Config()

# Secure API key for n8n automation (set this in your environment variables)
N8N_API_KEY = os.getenv('N8N_API_KEY', 'your-generated-secret-key-here')

# In-memory storage for pending checks (replace with Supabase later)
pending_checks = {}
processed_checks = {}

@automation_bp.route('/api/automation/checks', methods=['POST'])
def process_check_from_n8n():
    """
    Dedicated endpoint for n8n check processing automation
    Enhanced with review routing logic
    """
    try:
        # Verify automation request
        api_key = request.headers.get('X-Automation-Key')
        
        if not api_key or api_key != N8N_API_KEY:
            api_logger.warning(f"Unauthorized automation request from {request.remote_addr}")
            return {'error': 'Unauthorized automation request'}, 401
        
        # Debug: Log the raw request data
        api_logger.info(f"Raw request data type: {type(request.json)}")
        api_logger.info(f"Raw request data: {str(request.json)[:500]}")
        
        # Handle both JSON object and JSON string from n8n
        raw_data = request.json
        
        try:
            if isinstance(raw_data, str):
                data = json.loads(raw_data)
            else:
                data = raw_data
        except (json.JSONDecodeError, TypeError) as e:
            api_logger.error(f"Invalid JSON data: {str(e)}")
            return {'error': 'Invalid JSON data'}, 400
        
        if not data:
            return {'error': 'No data provided'}, 400
        
        # Extract check information safely
        extracted_data = {}
        business_validation = {}
        validation_score = 0
        
        if isinstance(data, dict):
            extracted_data = data.get('extractedData', {})
            business_validation = data.get('businessValidation', {})
            validation_score = data.get('validationScore', 0)
        
        # Log the automation request
        amount = 'Unknown'
        payee = 'Unknown'
        date = 'Unknown'
        check_number = 'Unknown'
        
        if isinstance(extracted_data, dict):
            amount = extracted_data.get('amountNumeric', 'Unknown')
            payee = extracted_data.get('payee', 'Unknown')
            date = extracted_data.get('date', 'Unknown')
            check_number = extracted_data.get('checkNumber', 'Unknown')
        
        api_logger.info(f"n8n automation check received - Amount: {amount}, Payee: {payee}")
        
        # Generate unique transaction ID
        transaction_id = f"AUTO-{secrets.token_hex(8)}"
        
        # Create check record
        check_record = {
            'id': transaction_id,
            'amount': amount,
            'payee': payee,
            'date': date,
            'check_number': check_number,
            'validation_score': validation_score,
            'raw_data': extracted_data,
            'received_at': datetime.utcnow().isoformat(),
            'status': 'pending',  # Will be updated based on confidence
            'flags': []
        }
        
        # Add flags based on validation issues
        if validation_score < 0.8:
            check_record['flags'].append('low_confidence_overall')
        if amount == 'Unknown' or not amount:
            check_record['flags'].append('no_amount_detected')
        if payee == 'Unknown' or not payee:
            check_record['flags'].append('no_payee_detected')
        if date == 'Unknown' or not date:
            check_record['flags'].append('no_date_detected')
            
        # Decision logic: Auto-approve vs Manual Review
        confidence_threshold = 0.85
        requires_review = (
            validation_score < confidence_threshold or 
            len(check_record['flags']) > 1 or
            amount == 'Unknown' or 
            payee == 'Unknown'
        )
        
        if requires_review:
            # Store for manual review
            check_record['status'] = 'pending_review'
            pending_checks[transaction_id] = check_record
            
            api_logger.info(f"Check {transaction_id} queued for manual review (confidence: {validation_score:.2f})")
            
            # Return response that tells n8n to route to "needs review" path
            result = {
                'status': 'needs_review',
                'action': 'queued_for_manual_review',
                'transaction_id': transaction_id,
                'message': 'Check queued for manual validation',
                'processed_at': datetime.utcnow().isoformat(),
                'confidence_score': validation_score,
                'flags': check_record['flags'],
                'check_data': {
                    'amount': amount,
                    'payee': payee,
                    'date': date,
                    'check_number': check_number
                }
            }
            
            return jsonify(result), 200
            
        else:
            # Auto-approve high confidence checks
            check_record['status'] = 'approved'
            check_record['approved_at'] = datetime.utcnow().isoformat()
            check_record['approved_by'] = 'system_auto'
            processed_checks[transaction_id] = check_record
            
            api_logger.info(f"Check {transaction_id} auto-approved (confidence: {validation_score:.2f})")
            
            # Return response that tells n8n to route to "approved" path
            result = {
                'status': 'auto_approved',
                'action': 'processed_automatically', 
                'transaction_id': transaction_id,
                'message': 'Check automatically validated and approved',
                'processed_at': datetime.utcnow().isoformat(),
                'confidence_score': validation_score,
                'check_data': {
                    'amount': amount,
                    'payee': payee,
                    'date': date,
                    'check_number': check_number
                }
            }
            
            return jsonify(result), 200
        
    except Exception as e:
        api_logger.error(f"Automation check processing failed: {str(e)}")
        import traceback
        api_logger.error(f"Full traceback: {traceback.format_exc()}")
        
        return jsonify({
            'error': 'Processing failed',
            'details': str(e),
            'status': 'error'
        }), 500


@automation_bp.route('/api/automation/health', methods=['GET'])
def automation_health():
    """Health check for automation endpoints"""
    return jsonify({
        'status': 'healthy',
        'service': 'n8n automation endpoints',
        'timestamp': datetime.utcnow().isoformat(),
        'pending_checks': len(pending_checks),
        'processed_checks': len(processed_checks)
    })

# NEW ENDPOINTS FOR CHECK REVIEW INTERFACE

@automation_bp.route('/api/checks/pending', methods=['GET'])
def get_pending_checks():
    """Get all checks awaiting manual review"""
    try:
        # Convert pending_checks dict to list for frontend
        checks_list = []
        for check_id, check_data in pending_checks.items():
            if check_data['status'] == 'pending_review':
                checks_list.append({
                    'id': check_id,
                    'amount': check_data['amount'],
                    'payee': check_data['payee'], 
                    'date': check_data['date'],
                    'check_number': check_data['check_number'],
                    'confidence': check_data['validation_score'],
                    'flags': check_data['flags'],
                    'received_at': check_data['received_at']
                })
        
        # Sort by received time (newest first)
        checks_list.sort(key=lambda x: x['received_at'], reverse=True)
        
        api_logger.info(f"Retrieved {len(checks_list)} pending checks for review")
        return jsonify({
            'checks': checks_list,
            'count': len(checks_list)
        }), 200
        
    except Exception as e:
        api_logger.error(f"Failed to get pending checks: {str(e)}")
        return jsonify({'error': 'Failed to retrieve pending checks'}), 500

@automation_bp.route('/api/checks/approve/<check_id>', methods=['POST'])
def approve_check(check_id):
    """Approve a specific check (manual override)"""
    try:
        if check_id not in pending_checks:
            return jsonify({'error': 'Check not found'}), 404
        
        # Move from pending to processed
        check_data = pending_checks[check_id]
        check_data['status'] = 'approved'
        check_data['approved_at'] = datetime.utcnow().isoformat()
        check_data['approved_by'] = 'manual_review'
        
        # Move to processed checks
        processed_checks[check_id] = check_data
        del pending_checks[check_id]
        
        api_logger.info(f"Check {check_id} manually approved - Amount: {check_data['amount']}, Payee: {check_data['payee']}")
        
        return jsonify({
            'status': 'approved',
            'check_id': check_id,
            'message': 'Check approved successfully'
        }), 200
        
    except Exception as e:
        api_logger.error(f"Failed to approve check {check_id}: {str(e)}")
        return jsonify({'error': 'Failed to approve check'}), 500

@automation_bp.route('/api/checks/reject/<check_id>', methods=['POST']) 
def reject_check(check_id):
    """Reject a specific check with reason"""
    try:
        if check_id not in pending_checks:
            return jsonify({'error': 'Check not found'}), 404
        
        data = request.get_json() or {}
        reason = data.get('reason', 'No reason provided')
        
        # Move from pending to processed (rejected)
        check_data = pending_checks[check_id]
        check_data['status'] = 'rejected'
        check_data['rejected_at'] = datetime.utcnow().isoformat()
        check_data['rejected_by'] = 'manual_review'
        check_data['rejection_reason'] = reason
        
        # Move to processed checks
        processed_checks[check_id] = check_data
        del pending_checks[check_id]
        
        api_logger.info(f"Check {check_id} manually rejected - Reason: {reason}")
        
        return jsonify({
            'status': 'rejected',
            'check_id': check_id,
            'reason': reason,
            'message': 'Check rejected successfully'
        }), 200
        
    except Exception as e:
        api_logger.error(f"Failed to reject check {check_id}: {str(e)}")
        return jsonify({'error': 'Failed to reject check'}), 500

@automation_bp.route('/api/checks/stats', methods=['GET'])
def get_check_stats():
    """Get check processing statistics"""
    try:
        total_pending = len([c for c in pending_checks.values() if c['status'] == 'pending_review'])
        total_approved = len([c for c in processed_checks.values() if c['status'] == 'approved'])
        total_rejected = len([c for c in processed_checks.values() if c['status'] == 'rejected'])
        auto_approved = len([c for c in processed_checks.values() if c['status'] == 'approved' and c.get('approved_by') == 'system_auto'])
        
        return jsonify({
            'pending_review': total_pending,
            'total_approved': total_approved,
            'total_rejected': total_rejected,
            'auto_approved': auto_approved,
            'manual_approved': total_approved - auto_approved,
            'total_processed': len(processed_checks)
        }), 200
        
    except Exception as e:
        api_logger.error(f"Failed to get check stats: {str(e)}")
        return jsonify({'error': 'Failed to get statistics'}), 500

# TESTING ENDPOINTS (Remove in production)
@automation_bp.route('/api/test/add-mock-check', methods=['GET'])
def add_mock_check():
    """Add a mock check for testing the review interface"""
    mock_check_id = f"TEST-{secrets.token_hex(4)}"
    
    mock_check = {
        'id': mock_check_id,
        'amount': '$2,450.00',
        'payee': 'Sweet James Legal Services',
        'date': '12/15/2024', 
        'check_number': '1001',
        'validation_score': 0.72,  # Low confidence to trigger review
        'raw_data': {
            'amountNumeric': '$2,450.00',
            'payee': 'Sweet James Legal Services',
            'date': '12/15/2024',
            'checkNumber': '1001'
        },
        'received_at': datetime.utcnow().isoformat(),
        'status': 'pending_review',
        'flags': ['low_confidence_overall', 'signature_unclear']
    }
    
    pending_checks[mock_check_id] = mock_check
    api_logger.info(f"Added mock check {mock_check_id} for testing")
    
    return jsonify({
        'message': 'Mock check added successfully!',
        'check_id': mock_check_id,
        'redirect': '/checks/review'
    })

@automation_bp.route('/api/test/add-multiple-checks', methods=['GET'])
def add_multiple_mock_checks():
    """Add multiple mock checks for testing"""
    mock_checks = [
        {
            'amount': '$1,250.00',
            'payee': 'ABC Corporation',
            'date': '11/28/2024',
            'check_number': '0987',
            'validation_score': 0.68,
            'flags': ['low_confidence_overall', 'no_signature_detected']
        },
        {
            'amount': '$850.50',
            'payee': 'Johnson & Associates',
            'date': '12/01/2024',
            'check_number': '0988',
            'validation_score': 0.79,
            'flags': ['date_unclear']
        },
        {
            'amount': '$5,000.00',
            'payee': 'Medical Center LLC',
            'date': '12/10/2024',
            'check_number': '0989',
            'validation_score': 0.83,
            'flags': ['amount_suspicious']
        }
    ]
    
    added_ids = []
    for mock_data in mock_checks:
        check_id = f"TEST-{secrets.token_hex(4)}"
        
        check_record = {
            'id': check_id,
            'amount': mock_data['amount'],
            'payee': mock_data['payee'],
            'date': mock_data['date'],
            'check_number': mock_data['check_number'],
            'validation_score': mock_data['validation_score'],
            'raw_data': mock_data,
            'received_at': datetime.utcnow().isoformat(),
            'status': 'pending_review',
            'flags': mock_data['flags']
        }
        
        pending_checks[check_id] = check_record
        added_ids.append(check_id)
    
    api_logger.info(f"Added {len(added_ids)} mock checks for testing")
    
    return jsonify({
        'message': f'{len(added_ids)} mock checks added successfully!',
        'check_ids': added_ids,
        'redirect': '/checks/review'
    })