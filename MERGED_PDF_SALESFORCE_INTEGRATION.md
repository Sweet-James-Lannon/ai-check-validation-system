# Merged PDF for Salesforce Integration

## Problem Statement
After implementing the check splitting feature, we discovered that Jai's Salesforce integration function expects a **single merged PDF** in the `merged_pdf_url` field, not individual split pages in `batch_images[]`.

- **What we had**: Individual split PDFs in `batch_images[]` array
- **What Salesforce needs**: A single merged PDF containing all split pages in `merged_pdf_url`

## Solution Implemented

### 1. PDF Merging Helper Function
Created `merge_batch_pdfs_and_upload()` in `routes/api_routes.py`:
- Downloads all PDFs from `batch_images[]`
- Merges them into a single PDF using PyPDF2
- Uploads the merged PDF to Supabase Storage (same batch folder)
- Returns the public URL for the merged PDF

### 2. Integration with Approval Workflow
Modified `/api/checks/approve/<check_id>` endpoint:
- **BEFORE** setting `validated_at` (Salesforce trigger):
  - Fetches current check's `batch_images[]`
  - Calls `merge_batch_pdfs_and_upload()`
  - Sets `merged_pdf_url` in update_data
- **THEN** sets `validated_at` to trigger Jai's edge function
- Salesforce webhook now gets the merged PDF URL

### 3. Why This Approach Works
✅ **No additional API calls** - happens automatically on approval
✅ **Timing is perfect** - PDF merges BEFORE Salesforce trigger fires
✅ **Uses existing data** - leverages batch_images[] already in database
✅ **Single source of truth** - merged_pdf_url contains the complete check
✅ **Efficient** - only runs once when check is approved

## Technical Flow

```
1. User clicks "Approve" on check
   ↓
2. Backend receives approval request
   ↓
3. Fetch check's batch_images[] from database
   ↓
4. Download each PDF from Supabase Storage
   ↓
5. Merge PDFs using PyPDF2.PdfMerger
   ↓
6. Upload merged PDF to Supabase Storage
   ↓
7. Set merged_pdf_url in update_data
   ↓
8. Set validated_at timestamp (triggers Salesforce)
   ↓
9. Update check in database
   ↓
10. Jai's edge function fires, pulls from merged_pdf_url
```

## File Structure

### Merged PDF Location
- **Bucket**: `check-documents`
- **Path**: `{batch_folder}/merged_{check_id}.pdf`
- **Example**: `batch-1762471297198/merged_check-uuid.pdf`

### Database Fields
- `batch_images[]` - Array of individual split PDFs (still exists for UI/navigation)
- `merged_pdf_url` - Single merged PDF URL (NEW - for Salesforce)

## Dependencies
- **PyPDF2**: Already in requirements.txt
- **Supabase Storage**: Already configured
- **No new packages needed**

## Testing Checklist
- [ ] Test approval of single-page check (1 PDF in batch_images)
- [ ] Test approval of multi-page check (3+ PDFs in batch_images)
- [ ] Verify merged PDF contains all pages in correct order
- [ ] Confirm merged_pdf_url is set in database
- [ ] Test Salesforce webhook receives merged_pdf_url
- [ ] Verify Jai's function can download and process merged PDF

## Benefits
1. **Salesforce Integration**: Jai's function gets exactly what it needs
2. **Maintains UI Functionality**: batch_images[] still used for page navigation/preview
3. **Automatic**: No manual steps or separate API calls
4. **Efficient**: Only merges when needed (at approval time)
5. **Reliable**: Error handling - approval continues even if merge fails

## Future Enhancements
- Add progress indicator for PDF merging (if slow for large batches)
- Cache merged PDFs to avoid re-merging on re-approval
- Add merged PDF preview in UI before approval
