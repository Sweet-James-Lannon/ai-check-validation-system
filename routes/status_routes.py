"""
=============================================================================
ENVIRONMENT STATUS ROUTES - Deployment Verification
=============================================================================
Quick sanity check to verify environment variables are properly configured.
Useful for troubleshooting deployment issues.

=============================================================================
"""

from flask import Blueprint
import os
from config import Config

status_bp = Blueprint("status", __name__)  # Renamed from debug_bp
config = Config()


#░█▀▀░█▀█░█▀█░█▀▀░▀█▀░█▀▀░░░█▀▀░█░█░█▀▀░█▀▀░█░█
#░█░░░█░█░█░█░█▀▀░░█░░█░█░░░█░░░█▀█░█▀▀░█░░░█▀▄
#░▀▀▀░▀▀▀░▀░▀░▀░░░▀▀▀░▀▀▀░░░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀
@status_bp.route("/status/config")
def config_check():
    """
    Environment configuration status - verifies all required 
    env vars are set. Disabled in production for security.
    """
    # Block in production
    if config.IS_PRODUCTION:
        return {"error": "Status endpoint disabled in production"}, 403
    
    return {
        # Auth Config
        "azure_auth": {
            "client_id_set": bool(os.getenv('AZURE_CLIENT_ID')),
            "tenant_id_set": bool(os.getenv('AZURE_TENANT_ID')),
            "secret_set": bool(os.getenv('AZURE_CLIENT_SECRET')),
            "auth_enabled": config.auth_enabled
        },
        
        # Database Config
        "supabase": {
            "url_set": bool(os.getenv('SUPABASE_URL')),
            "key_set": bool(os.getenv('SUPABASE_ANON_KEY'))
        },
        
        # AI Config
        "ai_services": {
            "openai_key_set": bool(os.getenv('OPENAI_API_KEY'))
        },
        
        # Environment
        "environment": os.getenv('ENVIRONMENT', 'NOT_SET'),
        "is_production": config.IS_PRODUCTION
    }