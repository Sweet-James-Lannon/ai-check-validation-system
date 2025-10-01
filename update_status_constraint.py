#!/usr/bin/env python3
"""
Script to update the status constraint to allow needs_review
"""

from services.supabase_service import SupabaseService
import sys

def update_status_constraint():
    """Update the status constraint to allow needs_review"""
    
    # Initialize Supabase service
    supabase_service = SupabaseService()
    
    if not supabase_service.client:
        print("ERROR: Could not initialize Supabase client")
        return False
    
    # SQL to update the constraint
    sql_commands = [
        "ALTER TABLE checks DROP CONSTRAINT IF EXISTS checks_status_check;",
        "ALTER TABLE checks ADD CONSTRAINT checks_status_check CHECK (status IN ('pending', 'needs_review', 'approved', 'rejected'));"
    ]
    
    try:
        print("Updating status constraint to allow 'needs_review'...")
        
        for sql in sql_commands:
            print(f"Executing: {sql}")
            # Try to execute the SQL directly
            response = supabase_service.client.rpc('execute_sql', {'sql': sql}).execute()
            
            if hasattr(response, 'error') and response.error:
                print(f"Error executing SQL: {response.error}")
                # This might fail if execute_sql RPC doesn't exist, which is normal
                print("Note: Direct SQL execution failed. You'll need to run this manually in Supabase Dashboard.")
        
        print("✅ Constraint update commands prepared!")
        print("\nIf the above failed, please run this SQL manually in Supabase Dashboard:")
        for sql in sql_commands:
            print(f"  {sql}")
        
        return True
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nPlease run this SQL manually in Supabase Dashboard:")
        for sql in sql_commands:
            print(f"  {sql}")
        return False

if __name__ == "__main__":
    success = update_status_constraint()
    sys.exit(0 if success else 1)
