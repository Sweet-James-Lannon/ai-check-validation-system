from flask import Blueprint
import os
from config import Config

debug_bp = Blueprint("debug", __name__)
config = Config()

@debug_bp.route("/debug")
def debug():
    return {
        "AZURE_CLIENT_ID": os.getenv('AZURE_CLIENT_ID', 'NOT_SET'),
        "AZURE_TENANT_ID": os.getenv('AZURE_TENANT_ID', 'NOT_SET'), 
        "SECRET_SET": bool(os.getenv('AZURE_CLIENT_SECRET')),
        "SUPABASE_URL": os.getenv('SUPABASE_URL', 'NOT_SET'),
        "SUPABASE_ANON_KEY": os.getenv('SUPABASE_ANON_KEY', 'NOT_SET'),
        "OPENAI_API_KEY": bool(os.getenv('OPENAI_API_KEY')),
        "ENVIRONMENT": os.getenv('ENVIRONMENT', 'NOT_SET'),
        "auth_enabled": config.auth_enabled
    }

