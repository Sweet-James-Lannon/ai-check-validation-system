"""
Migration Script: Update Check Naming Convention
=================================================
This script migrates checks from the old naming convention to the new one:

OLD CONVENTION:
- 001-1.pdf (first split)
- 001-2.pdf (second split)

NEW CONVENTION:
- 001.pdf (unsplit check)
- 001-main.pdf (original after split)
- 001-2.pdf (first split)
- 001-3.pdf (subsequent splits)

This script will:
1. Find all checks with "-1" suffix that have NO corresponding "-2" sibling
   → These are unsplit checks, remove the "-1" (e.g., 001-1.pdf → 001.pdf)

2. Find all checks with "-1" suffix that HAVE a corresponding "-2" sibling
   → These are split originals, rename to "-main" (e.g., 002-1.pdf → 002-main.pdf)

Author: Sweet James Development Team
Date: November 2025
"""

from services.supabase_service import supabase_service
from utils.logger import get_api_logger
import sys

logger = get_api_logger()

def migrate_check_naming():
    """Migrate all checks from old naming convention to new convention"""
    try:
        logger.info("=" * 80)
        logger.info("STARTING CHECK NAMING MIGRATION")
        logger.info("=" * 80)
        
        # Get all checks with their file names
        response = supabase_service.client.table('checks')\
            .select('id, file_name, batch_id')\
            .execute()
        
        if not response.data:
            logger.info("No checks found in database")
            return
        
        checks = response.data
        logger.info(f"Found {len(checks)} total checks to analyze")
        
        # Group checks by batch and check number
        check_groups = {}
        for check in checks:
            file_name = check.get('file_name', '')
            if not file_name:
                continue
                
            # Parse file_name (e.g., "156-001-1.pdf" -> batch: 156, num: 001, suffix: 1)
            clean_name = file_name.replace('.pdf', '').replace('-COMPLETE', '')
            parts = clean_name.split('-')
            
            if len(parts) < 2:
                continue
                
            batch = parts[0]
            check_num = parts[1]
            suffix = parts[2] if len(parts) >= 3 else None
            
            key = f"{batch}-{check_num}"
            
            if key not in check_groups:
                check_groups[key] = []
            
            check_groups[key].append({
                'id': check['id'],
                'file_name': file_name,
                'batch': batch,
                'check_num': check_num,
                'suffix': suffix
            })
        
        # Process each group
        migration_count = 0
        
        for key, group in check_groups.items():
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Analyzing group: {key}")
            logger.info(f"Checks in group: {[c['file_name'] for c in group]}")
            
            # Find checks with "-1" suffix
            check_with_1 = next((c for c in group if c['suffix'] == '1'), None)
            # Find checks with "-2" suffix
            check_with_2 = next((c for c in group if c['suffix'] == '2'), None)
            # Find checks with no suffix
            check_without_suffix = next((c for c in group if c['suffix'] is None), None)
            
            if check_with_1:
                if check_with_2:
                    # Case 2: Has both -1 and -2, so -1 should become -main
                    logger.info(f"✅ Found split pair: {check_with_1['file_name']} and {check_with_2['file_name']}")
                    logger.info(f"   Action: Rename {check_with_1['file_name']} → {check_with_1['batch']}-{check_with_1['check_num']}-main.pdf")
                    
                    new_file_name = f"{check_with_1['batch']}-{check_with_1['check_num']}-main.pdf"
                    
                    # Update in database
                    update_response = supabase_service.client.table('checks')\
                        .update({'file_name': new_file_name})\
                        .eq('id', check_with_1['id'])\
                        .execute()
                    
                    if update_response.data:
                        logger.info(f"   ✅ Successfully updated to {new_file_name}")
                        migration_count += 1
                    else:
                        logger.error(f"   ❌ Failed to update {check_with_1['file_name']}")
                        
                elif not check_without_suffix:
                    # Case 1: Has -1 but no -2 and no unsuffixed version
                    # This is an unsplit check with wrong suffix
                    logger.info(f"✅ Found unsplit check with wrong suffix: {check_with_1['file_name']}")
                    logger.info(f"   Action: Rename {check_with_1['file_name']} → {check_with_1['batch']}-{check_with_1['check_num']}.pdf")
                    
                    new_file_name = f"{check_with_1['batch']}-{check_with_1['check_num']}.pdf"
                    
                    # Update in database
                    update_response = supabase_service.client.table('checks')\
                        .update({'file_name': new_file_name})\
                        .eq('id', check_with_1['id'])\
                        .execute()
                    
                    if update_response.data:
                        logger.info(f"   ✅ Successfully updated to {new_file_name}")
                        migration_count += 1
                    else:
                        logger.error(f"   ❌ Failed to update {check_with_1['file_name']}")
                else:
                    logger.info(f"⏭️  Skipping - already has correct unsuffixed version: {check_without_suffix['file_name']}")
            else:
                logger.info(f"ℹ️  No checks with '-1' suffix in this group")
        
        logger.info("\n" + "=" * 80)
        logger.info(f"MIGRATION COMPLETE: Updated {migration_count} checks")
        logger.info("=" * 80)
        
        return migration_count
        
    except Exception as e:
        logger.error(f"Migration error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("CHECK NAMING MIGRATION SCRIPT")
    print("=" * 80)
    print("\nThis will update check file names in the database:")
    print("  • Unsplit checks with '-1' → Remove '-1' suffix")
    print("  • Split originals with '-1' → Change to '-main'")
    print("\n" + "=" * 80)
    
    confirm = input("\nProceed with migration? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        count = migrate_check_naming()
        print(f"\n✅ Migration complete! Updated {count} checks.")
    else:
        print("\n❌ Migration cancelled.")
        sys.exit(0)
