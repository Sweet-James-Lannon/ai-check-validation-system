from functools import wraps
from flask import session, redirect
from utils.logger import get_auth_logger

auth_logger = get_auth_logger()

def login_required(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Import here to avoid circular imports
        from config import Config
        config = Config()
        auth_enabled = config.auth_enabled
        
        if not auth_enabled:
            # If auth is disabled, allow access but warn
            auth_logger.warning("Authentication disabled - allowing access")
            return f(*args, **kwargs)
        
        if not session.get("user"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function