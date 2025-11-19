"""
Test script to verify merged_pdf_url is in database for approved check
"""
import sys
sys.path.append('/Users/lannonk/Documents/Sweet_James_Repos/ai-check-validation-system')

from services.supabase_service import supabase_service

# Check that was just approved
check_id = "3c9a0bcc-e9ef-4db2-ac71-d93578b62e0a"

print(f"\n{'='*80}")
print(f"CHECKING DATABASE FOR APPROVED CHECK: {check_id}")
print(f"{'='*80}\n")

try:
    response = supabase_service.client.table('checks').select(
        'id, file_name, status, validated_at, validated_by, merged_pdf_url, batch_images'
    ).eq('id', check_id).single().execute()
    
    if response.data:
        check = response.data
        
        print(f"✅ CHECK FOUND IN DATABASE\n")
        print(f"📄 File: {check.get('file_name')}")
        print(f"📊 Status: {check.get('status')}")
        print(f"✅ Validated At: {check.get('validated_at')}")
        print(f"👤 Validated By: {check.get('validated_by')}")
        print(f"\n{'='*80}")
        print(f"🔥 CRITICAL FIELD - merged_pdf_url:")
        print(f"{'='*80}")
        
        merged_url = check.get('merged_pdf_url')
        if merged_url:
            print(f"✅ MERGED PDF URL EXISTS IN DATABASE:")
            print(f"   {merged_url}")
        else:
            print(f"❌ MERGED PDF URL IS NULL!")
        
        print(f"\n{'='*80}")
        print(f"📋 OLD FIELD - batch_images (for comparison):")
        print(f"{'='*80}")
        batch_images = check.get('batch_images', [])
        if batch_images:
            print(f"Found {len(batch_images)} image(s) in batch_images array:")
            for idx, img in enumerate(batch_images):
                print(f"  [{idx}] {img.get('url', 'NO URL')}")
        else:
            print(f"❌ No batch_images found")
        
        print(f"\n{'='*80}")
        print(f"🎯 CONCLUSION:")
        print(f"{'='*80}")
        
        if merged_url:
            print(f"✅ Flask app is working correctly - merged_pdf_url is saved!")
            print(f"❌ Salesforce integration issue - Jai's edge function not reading merged_pdf_url")
            print(f"\n📧 MESSAGE TO JAI:")
            print(f"   'Check {check_id} was approved and merged_pdf_url is populated.'")
            print(f"   'URL: {merged_url}'")
            print(f"   'Please verify your edge function/N8N workflow reads from merged_pdf_url field.'")
        else:
            print(f"❌ merged_pdf_url is NULL - Flask app issue!")
            
    else:
        print(f"❌ Check not found in database!")
        
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
