import os
from datetime import timedelta

# Only load dotenv in development
if os.getenv('ENVIRONMENT') != 'production':
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

class Config:
    """Centralized configuration management"""
    
    # Core Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-12345')
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
    # Smart environment detection
    @property
    def ENVIRONMENT(self):
        # Check multiple indicators for environment
        env_var = os.getenv('ENVIRONMENT', 'development')
        
        # If running on Azure App Service, it's production
        if os.getenv('WEBSITE_SITE_NAME'):  # Azure App Service indicator
            return 'production'
        
        # If PORT is set (common in cloud deployments), likely production
        if os.getenv('PORT') and env_var == 'development':
            return 'production'
        
        return env_var
    
    @property
    def IS_PRODUCTION(self):
        return self.ENVIRONMENT == 'production'
    
    # Session configuration
    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = "/tmp/flask_session"
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = "azure_auth_"
    SESSION_FILE_THRESHOLD = 500
    SESSION_FILE_MODE = 0o600
    SESSION_SERIALIZATION_FORMAT = 'json'
    
    @property
    def SESSION_COOKIE_SECURE(self):
        return self.IS_PRODUCTION
    
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # Supabase configuration (same for both environments)
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
    
    # Azure AD configuration
    AZURE_CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
    AZURE_CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
    AZURE_TENANT_ID = os.getenv('AZURE_TENANT_ID')
    AZURE_SCOPE = ["User.Read"]
    
    # Smart redirect URI detection
    @property
    def AUTH_REDIRECT_URI(self):
        # If explicitly set in environment, use that
        env_uri = os.getenv('AUTH_REDIRECT_URI')
        if env_uri:
            return env_uri
        
        # Auto-detect based on environment
        if self.IS_PRODUCTION:
            return 'https://sj-recordingstream-dash-ffbbegamh8eybxfp.westus3-01.azurewebsites.net/auth/callback'
        else:
            return 'http://localhost:5051/auth/callback'
    
    @property
    def azure_authority(self):
        if self.AZURE_TENANT_ID:
            return f'https://login.microsoftonline.com/{self.AZURE_TENANT_ID}'
        return None
    
    @property
    def auth_enabled(self):
        return all([
            self.AZURE_CLIENT_ID,
            self.AZURE_CLIENT_SECRET,
            self.AZURE_TENANT_ID,
            self.AUTH_REDIRECT_URI
        ])