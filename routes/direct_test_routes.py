from flask import Blueprint, jsonify
import requests
import os

direct_test_bp = Blueprint("direct_test", __name__)

@direct_test_bp.route("/test-supabase-direct")
def test_supabase_direct():
    """Test Supabase using direct HTTP calls - bypasses library issues"""
    try:
        base_url = os.getenv('SUPABASE_URL')
        api_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not base_url or not api_key:
            return jsonify({"error": "Missing Supabase credentials"}), 500
        
        headers = {
            'apikey': api_key,
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Test 1: Basic connection
        test_url = f"{base_url}/rest/v1/"
        response = requests.get(test_url, headers=headers, timeout=10)
        
        results = {
            "base_connection": {
                "status_code": response.status_code,
                "success": response.status_code == 200
            }
        }
        
        # Test 2: Try to access checks table
        checks_url = f"{base_url}/rest/v1/checks?select=id&limit=1"
        checks_response = requests.get(checks_url, headers=headers, timeout=10)
        
        results["checks_table"] = {
            "status_code": checks_response.status_code,
            "success": checks_response.status_code == 200,
            "response": checks_response.text[:200] if checks_response.text else "No response"
        }
        
        # Test 3: List all tables
        tables_url = f"{base_url}/rest/v1/"
        tables_response = requests.get(tables_url, headers=headers, timeout=10)
        
        results["available_endpoints"] = {
            "status_code": tables_response.status_code,
            "content_length": len(tables_response.text) if tables_response.text else 0
        }
        
        return jsonify(results), 200
        
    except Exception as e:
        return jsonify({
            "error": "Direct test failed",
            "details": str(e)
        }), 500