
"""
=============================================================================
MAIN APPLICATION ENTRY POINT - Check Validation System
=============================================================================
Flask application factory and configuration for the AI-powered check validation
system. Handles blueprint registration, session management, and environment
configuration for both development and production deployments.

System Overview:
- AI-powered financial check validation
- Azure Entra ID enterprise authentication
- Supabase database integration
- OpenAI/Azure AI model flexibility
- n8n automation pipeline integration

Deployment Targets:
- Development: Local Flask server
- Production: Azure Web App with GitHub Actions CI/CD

Author: Sweet James Development Teamsdedddrdfdefdefrfreedfrtd
Last Updated: September 2025
=============================================================================
"""

from flask import Flask
from config import Config

# =============================================================================
# BLUEPRINT IMPORTS - Route Module Registration
# =============================================================================

# Import blueprints
from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.debug_routes import debug_bp
from routes.supabase_debug_routes import supabase_debug_bp
from routes.direct_test_routes import direct_test_bp
from routes.api_routes import api_bp

# === AI Service Integration - With Error Handling ===

try:
    from routes.chat_routes import chat_bp
    CHAT_ROUTES_AVAILABLE = True
    print("✅ Chat routes imported successfully")
except ImportError as e:
    print(f"❌ Failed to import chat routes: {e}")
    CHAT_ROUTES_AVAILABLE = False

# =============================================================================
# FLASK APPLICATION SETUP
# =============================================================================

app = Flask(__name__)
config = Config()

# =============================================================================
# SECURITY & SESSION CONFIGURATION
# =============================================================================

app.secret_key = config.SECRET_KEY
app.config.update(
    PERMANENT_SESSION_LIFETIME=config.PERMANENT_SESSION_LIFETIME,
    SESSION_COOKIE_SECURE=config.SESSION_COOKIE_SECURE,
    SESSION_COOKIE_HTTPONLY=config.SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE=config.SESSION_COOKIE_SAMESITE,
    
    SESSION_TYPE=config.SESSION_TYPE,
    SESSION_FILE_DIR=config.SESSION_FILE_DIR,
    SESSION_PERMANENT=config.SESSION_PERMANENT,
    SESSION_USE_SIGNER=config.SESSION_USE_SIGNER,
    SESSION_KEY_PREFIX=config.SESSION_KEY_PREFIX,
    SESSION_FILE_THRESHOLD=config.SESSION_FILE_THRESHOLD,
    SESSION_FILE_MODE=config.SESSION_FILE_MODE,
    SESSION_SERIALIZATION_FORMAT=config.SESSION_SERIALIZATION_FORMAT,
)

# =============================================================================
# ENVIRONMENT DETECTION & CONFIGURATION
# =============================================================================

# Update your configuration variables
is_production = config.IS_PRODUCTION

# =============================================================================
# BLUEPRINT REGISTRATION - Route Module Activation
# =============================================================================

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(debug_bp)
app.register_blueprint(supabase_debug_bp)
app.register_blueprint(direct_test_bp)
app.register_blueprint(api_bp)

# Only register chat routes if import was successful
if CHAT_ROUTES_AVAILABLE:
    app.register_blueprint(chat_bp)
    print("✅ Chat routes registered")
else:
    print("⚠️ Chat routes NOT registered - check services/ai_service.py")

# =============================================================================
# CUSTOM TEMPLATE FILTERS
# =============================================================================

from datetime import datetime

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    """Format a datetime string or object for template display."""
    if isinstance(value, str):
        try:
            # Try to parse ISO format datetime string
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.strftime(format)
        except (ValueError, AttributeError):
            return value
    elif isinstance(value, datetime):
        return value.strftime(format)
    else:
        return value

# =============================================================================
# SYSTEM DIAGNOSTICS & DEBUGGING
# =============================================================================

# Add a debug route to check what's registered
@app.route("/debug/routes")
def debug_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': rule.rule
        })
    return {"routes": routes}

# =============================================================================
# APPLICATION STARTUP & DEVELOPMENT SERVER
# =============================================================================

if __name__ == "__main__":
    print(f"🚀 Starting Flask app in {'production' if is_production else 'development'} mode")
    app.run(host='localhost', port=5000, debug=True)