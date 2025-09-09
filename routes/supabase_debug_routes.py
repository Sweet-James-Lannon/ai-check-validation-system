from flask import Blueprint, jsonify
import os
from config import Config
from utils.logger import get_api_logger

supabase_debug_bp = Blueprint("supabase_debug", __name__)
api_logger = get_api_logger()

@supabase_debug_bp.route("/supabase-debug")
def supabase_debug():
    """Debug Supabase connection specifically"""
    try:
        config = Config()
        
        # Step 1: Check environment variables
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')
        
        debug_info = {
            "step_1_env_vars": {
                "SUPABASE_URL": url[:50] + "..." if url and len(url) > 50 else url,
                "SUPABASE_ANON_KEY": key[:30] + "..." if key and len(key) > 30 else key,
                "url_length": len(url) if url else 0,
                "key_length": len(key) if key else 0
            }
        }
        
        # Step 2: Test Supabase import
        try:
            from supabase import create_client, Client
            debug_info["step_2_import"] = "✅ Supabase import successful"
        except Exception as e:
            debug_info["step_2_import"] = f"❌ Import failed: {str(e)}"
            return jsonify(debug_info), 500
        
        # Step 3: Test client creation
        try:
            if not url or not key:
                debug_info["step_3_client"] = "❌ Missing URL or KEY"
                return jsonify(debug_info), 500
                
            client = create_client(url, key)
            debug_info["step_3_client"] = "✅ Client created successfully"
        except Exception as e:
            debug_info["step_3_client"] = f"❌ Client creation failed: {str(e)}"
            return jsonify(debug_info), 500
        
        # Step 4: Test simple query
        try:
            # Try the simplest possible query
            response = client.table('checks').select('id').limit(1).execute()
            debug_info["step_4_query"] = f"✅ Query successful - Found {len(response.data)} records"
        except Exception as e:
            debug_info["step_4_query"] = f"❌ Query failed: {str(e)}"
            debug_info["step_4_error_type"] = type(e).__name__
        
        # Step 5: Test if table exists
        try:
            # Try to get table schema/info
            tables_response = client.table('information_schema.tables').select('table_name').eq('table_name', 'checks').execute()
            debug_info["step_5_table_exists"] = f"Table check result: {len(tables_response.data)} matches"
        except Exception as e:
            debug_info["step_5_table_exists"] = f"❌ Table check failed: {str(e)}"
        
        return jsonify(debug_info), 200
        
    except Exception as e:
        api_logger.error(f"Supabase debug failed: {str(e)}")
        return jsonify({
            "error": "Debug endpoint failed",
            "details": str(e),
            "type": type(e).__name__
        }), 500

@supabase_debug_bp.route("/test-simple-client")
def test_simple_client():
    """Test the absolute simplest Supabase client creation"""
    try:
        from supabase import create_client
        
        url = "https://eofjoftlixbzopcbtsxbrsupabase.co"  # Your actual URL
        key = os.getenv('SUPABASE_ANON_KEY')
        
        if not key:
            return jsonify({"error": "No anon key found"}), 500
            
        # Create client with minimal parameters
        client = create_client(url, key)
        
        # Test connection
        result = client.table('checks').select('count', count='exact').execute()
        
        return jsonify({
            "status": "success",
            "client_created": True,
            "connection_test": "passed",
            "count_result": result.count if hasattr(result, 'count') else "no count"
        })
        
    except Exception as e:
        return jsonify({
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__
        }), 500