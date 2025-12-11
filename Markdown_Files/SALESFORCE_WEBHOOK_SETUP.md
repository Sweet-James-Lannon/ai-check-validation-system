# 🔥 Salesforce Integration - CONFIGURED & READY!

## ✅ Configuration Complete

The Salesforce endpoint is **already configured** and ready to use! No `.env` setup needed.

---

## How It Works

When a user selects a claimant name from the dropdown, we'll send it to Salesforce and auto-populate **3 fields**:

1. **Claimant** - The claimant name (already selected)
2. **Matter Name** - From Salesforce SOQL query
3. **Matter ID** - From Salesforce SOQL query

---

## Salesforce Configuration (Hardcoded)

### Endpoint:
```
https://sweetjames--sjfull.sandbox.my.salesforce-sites.com/SmartReceptionAI/services/apexrest/AI_Flask_App_Fetch_Matter
```

### Method:
```
GET
```

### Token:
```
00DEc00000H8mAZMAZ
```

---

## Request Format

We send a **GET request** with query parameters:

```
GET /SmartReceptionAI/services/apexrest/AI_Flask_App_Fetch_Matter?searchKey=Jose%20Martinez&token=00DEc00000H8mAZMAZ
```

**Query Parameters:**
- `searchKey` - The claimant name to search for
- `token` - The Salesforce org token (hardcoded)

---

## Expected Response

**We need Jai to tell us the response format!**

Expected JSON response (pending confirmation from Jai):
```json
{
  "claimant": "Jose Martinez",
  "matter_name": "Martinez v. State Farm",
  "matter_id": "500ABC123"
}
```

Or it might be:
```json
{
  "matterName": "Martinez v. State Farm",
  "matterId": "500ABC123"
}
```

**TODO: Ask Jai for the exact field names in the response!**

---

## User Experience

### Flow:
1. User opens check detail page
2. User clicks "Claimant" dropdown
3. User types "Jos" in search box
4. User sees list of claimants from Supabase (our local data)
5. User clicks "**Jose Martinez**"
6. **🔥 SALESFORCE MAGIC HAPPENS:**
   - We call Salesforce API with `searchKey=Jose Martinez`
   - Salesforce runs SOQL query
   - Salesforce returns matter_name and matter_id
   - We auto-fill all 3 fields!
7. User sees all fields populated - saves time! 🎉

---

## Technical Flow

```
User selects "Jose Martinez"
    ↓
POST /api/salesforce/claimant-lookup
    ↓
Flask sends GET request to Salesforce
    ↓
GET https://...AI_Flask_App_Fetch_Matter?searchKey=Jose%20Martinez&token=00DEc00000H8mAZMAZ
    ↓
Salesforce runs SOQL query
    ↓
Salesforce returns JSON with matter data
    ↓
Flask sends to frontend
    ↓
JavaScript auto-fills 3 input fields
    ↓
User sees populated form!
```

---

## Testing

### 1. Test Salesforce API Directly:

```bash
curl -X GET 'https://sweetjames--sjfull.sandbox.my.salesforce-sites.com/SmartReceptionAI/services/apexrest/AI_Flask_App_Fetch_Matter?searchKey=test&token=00DEc00000H8mAZMAZ'
```

**Expected:** JSON response with matter data

### 2. Test Flask Endpoint:

```bash
curl -X POST http://localhost:5000/api/salesforce/claimant-lookup \
  -H "Content-Type: application/json" \
  -d '{"claimant_name": "Jose Martinez"}'
```

**Expected:**
```json
{
  "status": "success",
  "claimant": "Jose Martinez",
  "matter_name": "Martinez v. State Farm",
  "matter_id": "500ABC123"
}
```

### 3. Test in UI:

1. Open check detail page
2. Click "Claimant" dropdown
3. Select any claimant name
4. Open browser console (F12)
5. Look for: `🔍 Calling Salesforce webhook...`
6. Look for: `✅ Salesforce data received:`
7. Verify 3 fields auto-populated!

---

## Next Steps

- [x] Salesforce endpoint configured
- [x] Flask API endpoint created
- [x] Frontend auto-fill implemented
- [ ] **Ask Jai:** What are the exact field names in the Salesforce response?
- [ ] Test with real claimant data
- [ ] Verify auto-fill works end-to-end

---

## Questions for Jai

**Q: What does the Salesforce API return?**

Please provide an example response for:
```
GET /AI_Flask_App_Fetch_Matter?searchKey=John%20Doe&token=00DEc00000H8mAZMAZ
```

Expected format:
```json
{
  "field_name_here": "value",
  "another_field": "value"
}
```

---

**Ready to test! Just need Jai to confirm the response format! 🚀**
