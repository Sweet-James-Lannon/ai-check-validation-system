from flask import Blueprint
import os
from config import Config
import datetime
from flask import request, jsonify


debug_bp = Blueprint("debug", __name__)
config = Config()

@debug_bp.route("/debug")
def debug():
    return {
        "AZURE_CLIENT_ID": os.getenv('AZURE_CLIENT_ID', 'NOT_SET'),
        "AZURE_TENANT_ID": os.getenv('AZURE_TENANT_ID', 'NOT_SET'), 
        "SECRET_SET": bool(os.getenv('AZURE_CLIENT_SECRET')),
        "ENVIRONMENT": os.getenv('ENVIRONMENT', 'NOT_SET'),
        "auth_enabled": config.auth_enabled
    }

@automation_bp.route('/api/debug/no-auth-test', methods=['POST'])
def debug_no_auth():
    """Test endpoint without authentication"""
    api_logger.info("DEBUG: Received request without auth check!")
    api_logger.info(f"Headers: {dict(request.headers)}")
    api_logger.info(f"Body: {request.get_json()}")
    return jsonify({'message': 'Flask received the request!', 'timestamp': datetime.utcnow().isoformat()})