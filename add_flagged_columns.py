#!/usr/bin/env python3
"""
Script to add missing flagged_* columns to the checks table in Supabase
"""

from services.supabase_service import SupabaseService
import sys

def add_flagged_columns():
    """Add the missing flagged columns to the checks table"""
    
    # Initialize Supabase service
    supabase_service = SupabaseService()
    
    if not supabase_service.client:
        print("ERROR: Could not initialize Supabase client")
        return False
    
    # SQL to add the missing columns
    sql_commands = [
        "ALTER TABLE checks ADD COLUMN IF NOT EXISTS flagged_at timestamptz;",
        "ALTER TABLE checks ADD COLUMN IF NOT EXISTS flagged_by text;", 
        "ALTER TABLE checks ADD COLUMN IF NOT EXISTS flagged_by_name text;",
        "COMMENT ON COLUMN checks.flagged_at IS 'Timestamp when check was flagged for manual review';",
        "COMMENT ON COLUMN checks.flagged_by IS 'Username of person who flagged the check';",
        "COMMENT ON COLUMN checks.flagged_by_name IS 'Display name of person who flagged the check';"
    ]
    
    try:
        print("Adding flagged_* columns to checks table...")
        
        for sql in sql_commands:
            print(f"Executing: {sql}")
            # Use RPC call to execute SQL
            response = supabase_service.client.rpc('execute_sql', {'sql': sql}).execute()
            
            if hasattr(response, 'error') and response.error:
                print(f"Error executing SQL: {response.error}")
                return False
        
        print("✅ Successfully added flagged columns!")
        
        # Verify the columns were added
        print("\nVerifying columns were added...")
        response = supabase_service.client.table('checks').select('flagged_at, flagged_by, flagged_by_name').limit(1).execute()
        
        if hasattr(response, 'error') and response.error:
            print(f"❌ Verification failed: {response.error}")
            return False
        else:
            print("✅ Verification successful - columns are accessible!")
            return True
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nNote: You may need to run the SQL manually in Supabase Dashboard:")
        print("\n".join(sql_commands))
        return False

if __name__ == "__main__":
    success = add_flagged_columns()
    sys.exit(0 if success else 1)
