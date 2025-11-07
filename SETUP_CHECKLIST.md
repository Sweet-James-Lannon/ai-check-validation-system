# ✅ Setup Checklist - Salesforce Webhook Integration

## For Jai (N8N Webhook Creator)

- [ ] Create N8N webhook endpoint
- [ ] Configure webhook to receive POST requests with JSON body
- [ ] Add SOQL query to search Salesforce for claimant data
- [ ] Return 3 fields: `claimant`, `matter_name`, `matter_id`
- [ ] Test webhook with curl command (see SALESFORCE_WEBHOOK_SETUP.md)
- [ ] Send webhook URL to Lannon
- [ ] Send security token to Lannon (optional but recommended)

### Example N8N Workflow:

**1. Webhook Trigger Node**
- Method: POST
- Path: `/webhook/salesforce-claimant-lookup`
- Authentication: Bearer token (optional)

**2. Salesforce Query Node**
- SOQL: `SELECT Name, Matter_Name__c, Id FROM Contact WHERE Name = '{{ $json.claimant_name }}' LIMIT 1`

**3. Response Node**
- JSON:
  ```json
  {
    "claimant": "{{ $json.Name }}",
    "matter_name": "{{ $json.Matter_Name__c }}",
    "matter_id": "{{ $json.Id }}"
  }
  ```

---

## For Lannon (You!)

- [ ] Receive webhook URL from Jai
- [ ] Receive security token from Jai (optional)
- [ ] Add to `.env` file:
  ```bash
  SALESFORCE_WEBHOOK_URL=https://jais-webhook-url
  SALESFORCE_SECURITY_TOKEN=his-token  # Optional
  ```
- [ ] Restart Flask app
- [ ] Test in UI: Select claimant → Watch console logs
- [ ] Verify 3 fields auto-populate
- [ ] Celebrate! 🎉

---

## Testing Steps

### 1. Test Jai's Webhook (Jai does this):
```bash
curl -X POST https://jais-webhook-url \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer his-token" \
  -d '{"claimant_name": "Test Name"}'
```

**Expected response:**
```json
{
  "claimant": "Test Name",
  "matter_name": "Test Matter",
  "matter_id": "500ABC"
}
```

### 2. Test End-to-End (You do this):
1. Open check detail page
2. Click "Claimant" dropdown
3. Select any claimant name
4. Open browser console (F12)
5. Look for: `🔍 Calling Salesforce webhook...`
6. Look for: `✅ Salesforce data received:`
7. Verify 3 fields auto-populated!

---

## What We Send to Jai's Webhook

```json
{
  "claimant_name": "Jose Martinez"
}
```

## What Jai Returns

```json
{
  "claimant": "Jose Martinez",
  "matter_name": "Martinez v. State Farm",
  "matter_id": "500ABC123"
}
```

## What Gets Auto-Filled

- **Claimant** field → `"Jose Martinez"`
- **Matter Name** field → `"Martinez v. State Farm"`
- **Matter ID** field → `"500ABC123"`

---

## Files Changed

✅ `/routes/api_routes.py` - New endpoint `/api/salesforce/claimant-lookup`  
✅ `/templates/check_detail.html` - Auto-fill on claimant selection  
✅ `SALESFORCE_WEBHOOK_SETUP.md` - Complete guide for Jai  
✅ `IMPLEMENTATION_COMPLETE.md` - Summary of what was built  
✅ This checklist!

---

**Ready to go! Just waiting for Jai's 2 values! 🚀**
