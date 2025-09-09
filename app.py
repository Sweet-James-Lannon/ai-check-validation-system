from flask import Flask
from config import Config

# Import blueprints
from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.debug_routes import debug_bp
from routes.automation_routes import automation_bp        


# Try to import chat routes with error handling
try:
    from routes.chat_routes import chat_bp
    CHAT_ROUTES_AVAILABLE = True
    print("✅ Chat routes imported successfully")
except ImportError as e:
    print(f"❌ Failed to import chat routes: {e}")
    CHAT_ROUTES_AVAILABLE = False

app = Flask(__name__)
config = Config()
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

# Update your configuration variables
is_production = config.IS_PRODUCTION

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(debug_bp)
app.register_blueprint(automation_bp)

# Only register chat routes if import was successful
if CHAT_ROUTES_AVAILABLE:
    app.register_blueprint(chat_bp)
    print("✅ Chat routes registered")
else:
    print("⚠️ Chat routes NOT registered - check services/ai_service.py")

# Add a debug route to check what's registered
@app.route("/debug/routes")
def debug_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': rule.ruleç
        })
    return {"routes": routes}

if __name__ == "__main__":
    print(f"🚀 Starting Flask app in {'production' if is_production else 'development'} mode")
    app.run(host='localhost', port=5000, debug=True)