"""
Quick test to verify merged_pdf_url column exists in checks table
"""
from services.supabase_service import supabase_service

# Try to select merged_pdf_url field
try:
    response = supabase_service.client.table('checks').select('id,merged_pdf_url').limit(1).execute()
    
    if response.data:
        print("✅ SUCCESS: merged_pdf_url column EXISTS in checks table")
        print(f"Sample data: {response.data}")
    else:
        print("⚠️ Query succeeded but no data returned")
        
except Exception as e:
    print(f"❌ ERROR: merged_pdf_url column might NOT exist in checks table")
    print(f"Error: {str(e)}")
    print("\n🔧 SOLUTION: You need to add the merged_pdf_url column to your Supabase checks table:")
    print("   ALTER TABLE checks ADD COLUMN merged_pdf_url TEXT;")
