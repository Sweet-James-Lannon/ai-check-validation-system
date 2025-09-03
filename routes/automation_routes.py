from flask import Blueprint, request, jsonify
import secrets
import os
from datetime import datetime
from utils.logger import get_api_logger
from config import Config

automation_bp = Blueprint("automation", __name__)
api_logger = get_api_logger()
config = Config()

# Secure API key for n8n automation (set this in your environment variables)
N8N_API_KEY = os.getenv('N8N_API_KEY', 'your-generated-secret-key-here')

@automation_bp.route('/api/automation/checks', methods=['POST'])
def process_check_from_n8n():
    """
    Dedicated endpoint for n8n check processing automation
    Separate from user-facing routes - bypasses Entra ID for automation only
    """
    try:
        # Verify automation request
        api_key = request.headers.get('X-Automation-Key')
        
        if not api_key or api_key != N8N_API_KEY:
            api_logger.warning(f"Unauthorized automation request from {request.remote_addr}")
            return {'error': 'Unauthorized automation request'}, 401
        
        # Optional: IP whitelist for extra security
        # allowed_ips = ['your-n8n-server-ip']
        # if request.remote_addr not in allowed_ips:
        #     return {'error': 'Request from unauthorized IP'}, 403
        
        # Get the check data from n8n
        data = request.json
        
        if not data:
            return {'error': 'No data provided'}, 400
        
        # Extract check information
        extracted_data = data.get('extractedData', {})
        business_validation = data.get('businessValidation', {})
        
        # Log the automation request
        api_logger.info(f"n8n automation check received - Amount: {extracted_data.get('amountNumeric')}, Payee: {extracted_data.get('payee')}")
        
        # Process the check data (add your business logic here)
        result = {
            'status': 'success',
            'transaction_id': f"AUTO-{secrets.token_hex(8)}",
            'message': 'Check processed successfully via n8n automation',
            'processed_at': datetime.utcnow().isoformat(),
            'check_data': {
                'amount': extracted_data.get('amountNumeric'),
                'payee': extracted_data.get('payee'),
                'date': extracted_data.get('date'),
                'check_number': extracted_data.get('checkNumber'),
                'validation_score': data.get('validationScore')
            }
        }
        
        # You can add database storage here:
        # save_check_to_database(extracted_data, business_validation)
        
        api_logger.info(f"Check processed successfully: {result['transaction_id']}")
        return jsonify(result), 200
        
    except Exception as e:
        api_logger.error(f"Automation check processing failed: {str(e)}")
        return {
            'error': 'Processing failed',
            'details': str(e),
            'status': 'error'
        }, 500

@automation_bp.route('/api/automation/health', methods=['GET'])
def automation_health():
    """Health check for automation endpoints"""
    return {
        'status': 'healthy',
        'service': 'n8n automation endpoints',
        'timestamp': datetime.utcnow().isoformat()
    }