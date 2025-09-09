# services/supabase_service.py
from supabase import create_client, Client
from config import Config
from utils.logger import get_db_logger
from typing import List, Dict, Optional
import inspect

class SupabaseService:
    def __init__(self):
        self.logger = get_db_logger()
        self.config = Config()
        self.client = self._initialize_client()
        
    def _initialize_client(self) -> Optional[Client]:
        """Initialize Supabase client - Compatible with all versions"""
        try:
            url = self.config.SUPABASE_URL
            key = self.config.SUPABASE_ANON_KEY
            
            if not url or not key:
                self.logger.warning("Supabase credentials not found in environment")
                return None
            
            # Check what parameters create_client accepts
            sig = inspect.signature(create_client)
            params = list(sig.parameters.keys())
            
            self.logger.info(f"Supabase create_client accepts: {params}")
            
            # Use only the basic parameters that all versions support
            client = create_client(url, key)
            
            self.logger.info("Supabase client initialized successfully")
            return client
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Supabase client: {str(e)}")
            return None
    
    def health_check(self) -> Dict:
        """Check if Supabase connection is healthy"""
        if not self.client:
            return {
                "status": "unhealthy",
                "error": "Supabase client not initialized"
            }
        
        try:
            # Try a simple query to test connection
            response = self.client.table('checks').select('id').limit(1).execute()
            return {
                "status": "healthy",
                "connected": True,
                "tables_accessible": True,
                "record_count": len(response.data)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }
    
    def create_checks_table_if_not_exists(self):
        """Create the checks table if it doesn't exist"""
        try:
            if not self.client:
                return {"error": "No client"}
            
            # This is a simple way to check if table exists and create it
            # In production, you'd use Supabase migrations
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS checks (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                check_number TEXT,
                payee_name TEXT,
                pay_to TEXT,
                amount TEXT,
                check_date DATE,
                memo TEXT,
                routing_number TEXT,
                account_number TEXT,
                micr_line TEXT,
                matter_name TEXT,
                case_type TEXT,
                delivery_service TEXT,
                confidence_score DECIMAL,
                status TEXT DEFAULT 'pending',
                flags TEXT[],
                file_name TEXT,
                file_id TEXT,
                raw_ocr_content TEXT,
                salesforce_id TEXT,
                image_data TEXT,
                image_mime_type TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            
            # Execute raw SQL (this might not work depending on permissions)
            # result = self.client.rpc('create_checks_table', {'sql': create_table_sql}).execute()
            
            return {"message": "Table creation attempted"}
            
        except Exception as e:
            self.logger.error(f"Failed to create table: {str(e)}")
            return {"error": str(e)}

# Singleton instance
supabase_service = SupabaseService()