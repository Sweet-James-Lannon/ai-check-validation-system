"""
=============================================================================
DASHBOARD ROUTES - Check Validation System
=============================================================================
Primary routes for check validation dashboard and document management.
Handles main UI, check queues, validation workflows, and document dashboards.

Author: Sweet James Development Team  
Last Updated: September 2025
=============================================================================
"""

from flask import Blueprint, render_template, session, redirect, url_for
from utils.decorators import (
    login_required,
)
from utils.logger import get_api_logger
from services.supabase_service import supabase_service

# =============================================================================
# CONFIGURATION & SETUP
# =============================================================================

api_logger = get_api_logger()

dashboard_bp = Blueprint("dashboard", __name__)

# =============================================================================
# MAIN DASHBOARD ROUTES
# =============================================================================

@dashboard_bp.route("/")
@login_required
def dashboard_home():
    """Universal Document Ingestion RAG System - Main Dashboard"""
    user = session.get("user")
    
    # Get system-wide metrics across all document types
    try:
        # Get checks metrics
        checks_response = supabase_service.client.table('checks').select('*').execute()
        total_checks = len(checks_response.data) if checks_response.data else 0
        
        # TODO: Add other document type metrics when tables are created
        # contracts_response = supabase_service.client.table('contracts').select('*').execute()
        # legal_docs_response = supabase_service.client.table('legal_documents').select('*').execute()
        
        document_metrics = {
            'checks': {
                'total': total_checks,
                'processed_today': 23,  # TODO: Calculate from database
                'pending': 8,           # TODO: Calculate from database
                'success_rate': 94.2    # TODO: Calculate from database
            },
            'contracts': {
                'total': 156,          # TODO: Get from database
                'processed_today': 12,
                'pending': 3,
                'success_rate': 97.1
            },
            'legal_documents': {
                'total': 89,           # TODO: Get from database
                'processed_today': 7,
                'pending': 2,
                'success_rate': 95.8
            },
            'general_documents': {
                'total': 234,          # TODO: Get from database
                'processed_today': 18,
                'pending': 5,
                'success_rate': 93.4
            }
        }
        
        api_logger.info("Loading universal document dashboard")
        return render_template("main_dashboard.html", user=user, metrics=document_metrics)
        
    except Exception as e:
        api_logger.error(f"Error loading main dashboard: {str(e)}")
        # Fallback metrics if database fails
        document_metrics = {
            'checks': {'total': 0, 'processed_today': 0, 'pending': 0, 'success_rate': 0},
            'contracts': {'total': 0, 'processed_today': 0, 'pending': 0, 'success_rate': 0},
            'legal_documents': {'total': 0, 'processed_today': 0, 'pending': 0, 'success_rate': 0},
            'general_documents': {'total': 0, 'processed_today': 0, 'pending': 0, 'success_rate': 0}
        }
        return render_template("main_dashboard.html", user=user, metrics=document_metrics, error_message="Failed to load system metrics")

# =============================================================================
# CHECK VALIDATION ROUTES
# =============================================================================

@dashboard_bp.route("/checks/")
@login_required
def checks_dashboard():
    """Check-specific dashboard with AI chat and validation tools"""
    user = session.get("user")
    return render_template("checks_dashboard.html", user=user)

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
                'check_issue_date': check.get('check_issue_date', ''),
                'memo': check.get('memo', ''),
                'routing_number': check.get('routing_number', ''),
                'account_number': check.get('account_number', ''),
                'micr_line': check.get('micr_line', ''),
                'matter_name': check.get('matter_name', ''),
                'matter_id': check.get('matter_id', ''),
                'case_type': check.get('case_type', ''),
                'delivery_service': check.get('delivery_service', ''),
                'insurance_company_name': check.get('insurance_company_name', ''),
                'claim_number': check.get('claim_number', ''),
                'policy_number': check.get('policy_number', ''),
                'confidence_score': check.get('confidence_score', 0),
                'status': check.get('status', 'unknown'),
                'flags': check.get('flags', []),
                'file_name': check.get('file_name', ''),
                'file_id': check.get('file_id', ''),
                'raw_ocr_content': check.get('raw_ocr_content', ''),
                'forward_reason': check.get('forward_reason', ''),  # RENAMED
                'created_at': check.get('created_at', ''),
                'confidence_percentage': round((check.get('confidence_score', 0) * 100), 1) if check.get('confidence_score') else 0,
                'image_data': check.get('image_data', ''),
                'image_mime_type': check.get('image_mime_type', '')
            }
            formatted_checks.append(formatted_check)
        
        api_logger.info(f"Retrieved {len(formatted_checks)} pending checks for queue view")
        
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
            'check_issue_date': check.get('check_issue_date', ''),
            'memo': check.get('memo', ''),
            'routing_number': check.get('routing_number', ''),
            'account_number': check.get('account_number', ''),
            'micr_line': check.get('micr_line', ''),
            'matter_name': check.get('matter_name', ''),
            'matter_id': check.get('matter_id', ''),
            'case_type': check.get('case_type', ''),
            'delivery_service': check.get('delivery_service', ''),
            'insurance_company_name': check.get('insurance_company_name', ''),
            'claim_number': check.get('claim_number', ''),
            'policy_number': check.get('policy_number', ''),
            'confidence_score': check.get('confidence_score', 0),
            'status': check.get('status', 'unknown'),
            'flags': check.get('flags', []),
            'file_name': check.get('file_name', ''),
            'file_id': check.get('file_id', ''),
            'raw_ocr_content': check.get('raw_ocr_content', ''),
            'forward_reason': check.get('forward_reason', ''),  # RENAMED
            'created_at': check.get('created_at', ''),
            'validated_at': check.get('validated_at', ''),
            'validated_by': check.get('validated_by', ''),
            'validated_by_name': check.get('validated_by_name', ''),
            'flagged_at': check.get('flagged_at', ''),
            'flagged_by': check.get('flagged_by', ''),
            'flagged_by_name': check.get('flagged_by_name', ''),
            'updated_at': check.get('updated_at', ''),
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

# =============================================================================
# DOCUMENT MANAGEMENT ROUTES
# =============================================================================

@dashboard_bp.route("/contracts/")
@login_required
def contracts_dashboard():
    """Contracts-specific dashboard with AI chat and analysis tools"""
    user = session.get("user")
    return render_template("contracts_dashboard.html", user=user)

@dashboard_bp.route("/legal-documents/")
@login_required
def legal_documents_dashboard():
    """Legal documents dashboard with AI chat and analysis tools"""
    user = session.get("user")
    return render_template("legal_documents_dashboard.html", user=user)

@dashboard_bp.route("/documents/")
@login_required
def general_documents_dashboard():
    """General documents dashboard with AI chat and analysis tools"""
    user = session.get("user")
    return render_template("general_documents_dashboard.html", user=user)

# =============================================================================
# END OF FILE
# =============================================================================