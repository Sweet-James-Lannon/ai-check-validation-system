# services/supabase_service.py
from supabase import create_client, Client
from config import Config
from utils.logger import get_db_logger
from typing import List, Dict, Optional

class SupabaseService:
    def __init__(self):
        self.logger = get_db_logger()
        self.config = Config()
        self.client = self._initialize_client()
        
    def _initialize_client(self) -> Optional[Client]:
        """Initialize Supabase client"""
        try:
            url = self.config.SUPABASE_URL
            key = self.config.SUPABASE_ANON_KEY
            
            if not url or not key:
                self.logger.warning("Supabase credentials not found in environment")
                return None
                
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
            # We'll figure out your table name in the next step
            response = self.client.table('checks').select('id').limit(1).execute()
            return {
                "status": "healthy",
                "connected": True,
                "tables_accessible": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }
    
    def get_all_tables(self):
        """Debug function to see what tables exist"""
        try:
            if not self.client:
                return {"error": "No client"}
            
            # This will help us see what's in your database
            response = self.client.table('information_schema.tables').select('table_name').execute()
            return response.data
            
        except Exception as e:
            self.logger.error(f"Failed to get tables: {str(e)}")
            return {"error": str(e)}

# Singleton instance
supabase_service = SupabaseService()