from flask import Flask
from config import Config

# Import blueprints
from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.debug_routes import debug_bp

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

if __name__ == "__main__":
    # app.run(host='localhost', port=5000, debug=True)
    app.run(host='0.0.0.0', port=5000, debug=not is_production)