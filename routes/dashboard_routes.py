from flask import Blueprint, render_template, session, redirect, url_for
from utils.decorators import (
    login_required,
)
from utils.logger import get_api_logger
from services.supabase_service import supabase_service

api_logger = get_api_logger()

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def dashboard_home():
    user = session.get("user")
    return render_template("dashboard.html", user=user)

@dashboard_bp.route("/checks/queue")
@login_required
def check_queue():
    """Check queue page showing all pending checks from Supabase"""
    try:
        user = session.get("user")
        
        # Get pending checks from Supabase - using your actual table name
        response = supabase_service.client.table('checks').select('*').order('created_at', desc=True).execute()

        # Format data for frontend
        formatted_checks = []
        for check in response.data:
            formatted_check = {
                'id': check.get('id'),
                'check_number': check.get('check_number', ''),
                'payee_name': check.get('payee_name', ''),
                'pay_to': check.get('pay_to', ''),
                'amount': check.get('amount', ''),
                'check_date': check.get('check_date', ''),
                'memo': check.get('memo', ''),
                'routing_number': check.get('routing_number', ''),
                'account_number': check.get('account_number', ''),
                'micr_line': check.get('micr_line', ''),
                'matter_name': check.get('matter_name', ''),
                'case_type': check.get('case_type', ''),
                'delivery_service': check.get('delivery_service', ''),
                'confidence_score': check.get('confidence_score', 0),
                'status': check.get('status', 'unknown'),
                'flags': check.get('flags', []),
                'file_name': check.get('file_name', ''),
                'file_id': check.get('file_id', ''),
                'raw_ocr_content': check.get('raw_ocr_content', ''),
                'salesforce_id': check.get('salesforce_id', ''),
                'created_at': check.get('created_at', ''),
                'confidence_percentage': round((check.get('confidence_score', 0) * 100), 1) if check.get('confidence_score') else 0,
                'image_data': check.get('image_data', ''),
                'image_mime_type': check.get('image_mime_type', '')
            }
            formatted_checks.append(formatted_check)
        
        api_logger.info(f"Retrieved {len(formatted_checks)} pending checks for queue view")

        # Add this debug line before return render_template
        print(f"DEBUG: image_data length: {len(formatted_checks[0].get('image_data', ''))}")
        print(f"DEBUG: image_mime_type: {formatted_checks[0].get('image_mime_type')}")

        
        return render_template("check_queue.html", 
                             user=user, 
                             checks=formatted_checks,
                             total_count=len(formatted_checks))
        
    except Exception as e:
        api_logger.error(f"Error loading check queue: {str(e)}")
        user = session.get("user")
        return render_template("check_queue.html", 
                             user=user, 
                             checks=[], 
                             total_count=0,
                             error_message="Failed to load checks from database")
    

@dashboard_bp.route("/checks/detail/<check_id>")
@login_required
def check_detail(check_id):
    """Individual check detail page for validation"""
    try:
        user = session.get("user")
        
        # Get specific check from Supabase
        response = supabase_service.client.table('checks').select('*').eq('id', check_id).single().execute()
        
        if not response.data:
            api_logger.warning(f"Check {check_id} not found")
            return render_template("error.html", 
                                 user=user,
                                 error_message=f"Check {check_id} not found"), 404
        
        check = response.data
        
        # Format check data for template
        formatted_check = {
            'id': check.get('id'),
            'check_number': check.get('check_number', ''),
            'payee_name': check.get('payee_name', ''),
            'pay_to': check.get('pay_to', ''),
            'amount': check.get('amount', ''),
            'check_date': check.get('check_date', ''),
            'memo': check.get('memo', ''),
            'routing_number': check.get('routing_number', ''),
            'account_number': check.get('account_number', ''),
            'micr_line': check.get('micr_line', ''),
            'matter_name': check.get('matter_name', ''),
            'case_type': check.get('case_type', ''),
            'delivery_service': check.get('delivery_service', ''),
            'confidence_score': check.get('confidence_score', 0),
            'status': check.get('status', 'unknown'),
            'flags': check.get('flags', []),
            'file_name': check.get('file_name', ''),
            'file_id': check.get('file_id', ''),
            'raw_ocr_content': check.get('raw_ocr_content', ''),
            'salesforce_id': check.get('salesforce_id', ''),
            'created_at': check.get('created_at', ''),
            'confidence_percentage': round((check.get('confidence_score', 0) * 100), 1) if check.get('confidence_score') else 0,
            'image_data': check.get('image_data', ''),
            'image_mime_type': check.get('image_mime_type', '')
        }
        
        api_logger.info(f"Loading check detail for {check_id}")
        
        return render_template("check_detail.html", 
                             user=user, 
                             check=formatted_check)
        
    except Exception as e:
        api_logger.error(f"Error loading check detail {check_id}: {str(e)}")
        user = session.get("user")
        return render_template("error.html", 
                             user=user,
                             error_message=f"Failed to load check {check_id}"), 500


@dashboard_bp.route("/checks/review")
@login_required
def check_review():
    """Check review queue page for manual validation"""
    user = session.get("user")
    return render_template("check_review.html", user=user)

