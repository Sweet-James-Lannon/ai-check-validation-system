# 🚨 SALESFORCE INTEGRATION ISSUE - merged_pdf_url Not Showing in Closing Documents

## Problem Statement
- ✅ Flask app successfully merges PDFs and saves `merged_pdf_url` to database
- ✅ Database query confirms `merged_pdf_url` field is populated with correct URL
- ❌ Salesforce Closing Documents section is EMPTY - PDF not appearing

## Root Cause
**Jai's edge function (Supabase Edge Function or N8N workflow) is NOT reading the `merged_pdf_url` field.**

It's likely still reading from the OLD `batch_images[]` field instead of the NEW `merged_pdf_url` field.

## Evidence
Check `3c9a0bcc-e9ef-4db2-ac71-d93578b62e0a` (002-3):
- ✅ `validated_at`: "2025-11-19 17:21:15.040266+00" (Salesforce trigger fired)
- ✅ `merged_pdf_url`: "https://eofjofthxbzopcbtsxbr.supabase.co/storage/v1/object/public/check-documents/batch-1763572335844/157-002-2.pdf"
- ❌ Salesforce Closing Documents: EMPTY

## Where to Fix

### Option 1: Supabase Edge Function (if using Edge Functions)
Location: Supabase Dashboard → Edge Functions

Look for code that reads check data when `validated_at` is set:

```typescript
// WRONG (old code):
const checkImages = checkData.batch_images; // ❌ Array of individual PDFs

// CORRECT (new code):
const pdfUrl = checkData.merged_pdf_url; // ✅ Single merged PDF URL
```

### Option 2: N8N Workflow (if using N8N)
Location: N8N Dashboard → Workflows → Salesforce Check Integration

Look for the field mapping when sending to Salesforce:

```javascript
// WRONG (old mapping):
"ClosingDocuments": "{{$node["Supabase"].json["batch_images"][0]["url"]}}"

// CORRECT (new mapping):
"ClosingDocuments": "{{$node["Supabase"].json["merged_pdf_url"]}}"
```

### Option 3: Database Trigger (if using Supabase Database Functions)
Location: Supabase Dashboard → Database → Functions

SQL function triggered by `validated_at`:

```sql
-- WRONG (old code):
SELECT (batch_images->0->>'url') as pdf_url FROM checks WHERE id = NEW.id;

-- CORRECT (new code):
SELECT merged_pdf_url as pdf_url FROM checks WHERE id = NEW.id;
```

## How to Test

1. **Check Supabase Edge Function Logs**:
   - Go to: Supabase Dashboard → Edge Functions → Logs
   - Filter by timestamp: 2025-11-19 17:21:15
   - Look for the request that fired when check was approved
   - See what data was sent to Salesforce

2. **Check N8N Execution Logs**:
   - Go to: N8N Dashboard → Executions
   - Find execution at: 2025-11-19 17:21:15
   - Inspect the data sent to Salesforce
   - Check if `merged_pdf_url` is in the payload

3. **Verify Database Trigger**:
   ```sql
   -- Check if any triggers exist on checks table
   SELECT 
       trigger_name,
       event_manipulation,
       action_statement
   FROM information_schema.triggers
   WHERE event_object_table = 'checks'
   AND trigger_name LIKE '%salesforce%' OR trigger_name LIKE '%validate%';
   ```

## Next Steps

1. **Ask Jai to check his edge function/workflow code**
2. **Share this check ID with him**: `3c9a0bcc-e9ef-4db2-ac71-d93578b62e0a`
3. **Tell him**: "The merged_pdf_url field is populated correctly with the PDF URL. Your function needs to read from `merged_pdf_url` instead of `batch_images[]`. Here's the URL that should be sent to Salesforce: https://eofjofthxbzopcbtsxbr.supabase.co/storage/v1/object/public/check-documents/batch-1763572335844/157-002-2.pdf"

## Flask App Status
✅ **Flask app is working perfectly**:
- PDF merging: ✅ Working
- Database update: ✅ Working  
- merged_pdf_url field: ✅ Populated correctly

🔴 **Issue is in Salesforce integration code** (Jai's responsibility)
