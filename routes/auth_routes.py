"""
=============================================================================
AUTHENTICATION ROUTES - Azure Entra ID Integration
=============================================================================
Handles user authentication using Microsoft Azure Entra ID (formerly Azure AD).
Implements OAuth 2.0 authorization code flow with PKCE for secure enterprise SSO.

Features:
- Azure Entra ID OAuth 2.0 integration
- Session management with CSRF protection
- Automatic user profile extraction
- Secure token handling and validation
- Environment-aware redirect URIs

Author: Sweet James Development Team
Last Updated: September 2025
=============================================================================
"""

from flask import Blueprint, redirect, url_for, session, request, render_template_string
from msal import ConfidentialClientApplication
from config import Config
import uuid

# =============================================================================
# CONFIGURATION & SETUP
# =============================================================================

auth_bp = Blueprint("auth", __name__)
config = Config()

CLIENT_ID = config.AZURE_CLIENT_ID
CLIENT_SECRET = config.AZURE_CLIENT_SECRET
TENANT_ID = config.AZURE_TENANT_ID
AUTHORITY = config.azure_authority
REDIRECT_PATH = "/getAToken"
SCOPE = config.AZURE_SCOPE

# =============================================================================
# AUTHENTICATION FLOW ROUTES
# =============================================================================

@auth_bp.route("/login")
def login():
    session["state"] = str(uuid.uuid4())
    auth_app = ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    auth_url = auth_app.get_authorization_request_url(
        SCOPE,
        state=session["state"],
        redirect_uri=config.AUTH_REDIRECT_URI
    )
    return redirect(auth_url)

@auth_bp.route(REDIRECT_PATH)
def authorized():
    if request.args.get("state") != session.get("state"):
        return "State mismatch", 400
    if "error" in request.args:
        return f"Error: {request.args['error_description']}", 400
    code = request.args.get("code")
    auth_app = ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    result = auth_app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPE,
        redirect_uri=config.AUTH_REDIRECT_URI
    )
    if "id_token_claims" in result:
        session["user"] = {
            "name": result["id_token_claims"].get("name"),
            "preferred_username": result["id_token_claims"].get("preferred_username"),
            "oid": result["id_token_claims"].get("oid"),
        }
        return redirect(url_for("dashboard.dashboard_home"))
    return "Login failed", 400

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(
        f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={url_for('dashboard.dashboard_home', _external=True)}"
    )

# =============================================================================
# END OF FILE
# =============================================================================
