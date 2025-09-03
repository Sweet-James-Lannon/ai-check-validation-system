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
    """
    try:
        # Verify automation request
        api_key = request.headers.get('X-Automation-Key')
        
        if not api_key or api_key != N8N_API_KEY:
            api_logger.warning(f"Unauthorized automation request from {request.remote_addr}")
            return {'error': 'Unauthorized automation request'}, 401
        
        # Handle both JSON object and JSON string from n8n
        try:
            if isinstance(request.json, str):
                import json
                data = json.loads(request.json)
            else:
                data = request.json
        except (json.JSONDecodeError, TypeError) as e:
            api_logger.error(f"Invalid JSON data: {str(e)}")
            return {'error': 'Invalid JSON data'}, 400
        
        if not data:
            return {'error': 'No data provided'}, 400
        
        # Extract check information (with safe defaults)
        extracted_data = data.get('extractedData', {}) if isinstance(data, dict) else {}
        business_validation = data.get('businessValidation', {}) if isinstance(data, dict) else {}
        
        # Log the automation request
        amount = extracted_data.get('amountNumeric', 'Unknown') if extracted_data else 'Unknown'
        payee = extracted_data.get('payee', 'Unknown') if extracted_data else 'Unknown'
        api_logger.info(f"n8n automation check received - Amount: {amount}, Payee: {payee}")
        
        # Process the check data
        result = {
            'status': 'success',
            'transaction_id': f"AUTO-{secrets.token_hex(8)}",
            'message': 'Check processed successfully via n8n automation',
            'processed_at': datetime.utcnow().isoformat(),
            'check_data': {
                'amount': amount,
                'payee': payee,
                'date': extracted_data.get('date', 'Unknown') if extracted_data else 'Unknown',
                'check_number': extracted_data.get('checkNumber', 'Unknown') if extracted_data else 'Unknown',
                'validation_score': data.get('validationScore', 0) if isinstance(data, dict) else 0
            },
            'received_data_type': type(data).__name__,
            'debug_info': str(data)[:200]  # First 200 chars for debugging
        }
        
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