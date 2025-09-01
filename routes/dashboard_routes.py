from flask import Blueprint, render_template, session, redirect, url_for
from utils.decorators import (
    login_required,
)
dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def dashboard_home():
    user = session.get("user")
    return render_template("dashboard.html", user=user)

@dashboard_bp.route("/validation-chat") 
@login_required
def validation_chat():
    user = session.get("user")
    return render_template("validation_chat.html", user=user)