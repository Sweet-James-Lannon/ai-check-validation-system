from flask import Blueprint, request, jsonify
import os
from config import Config
from datetime import datetime
from utils.logger import get_api_logger

debug_bp = Blueprint("debug", __name__)
config = Config()
api_logger = get_api_logger()  # Add this line

@debug_bp.route("/debug")
def debug():
    return {
        "AZURE_CLIENT_ID": os.getenv('AZURE_CLIENT_ID', 'NOT_SET'),
        "AZURE_TENANT_ID": os.getenv('AZURE_TENANT_ID', 'NOT_SET'), 
        "SECRET_SET": bool(os.getenv('AZURE_CLIENT_SECRET')),
        "ENVIRONMENT": os.getenv('ENVIRONMENT', 'NOT_SET'),
        "auth_enabled": config.auth_enabled,
        "N8N_API_KEY": os.getenv('N8N_API_KEY', 'NOT_SET')  # Add this to check n8n key
    }

@debug_bp.route('/api/debug/no-auth-test', methods=['POST'])
def debug_no_auth():
    """Test endpoint without authentication"""
    api_logger.info("DEBUG: Received request without auth check!")
    api_logger.info(f"Headers: {dict(request.headers)}")
    api_logger.info(f"Body: {request.get_json()}")
    return jsonify({
        'message': 'Flask received the request!', 
        'timestamp': datetime.utcnow().isoformat(),
        'received_headers': dict(request.headers),
        'received_body': request.get_json()
    })