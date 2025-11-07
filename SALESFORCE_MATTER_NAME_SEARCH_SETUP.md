# 🔥 SALESFORCE MATTER NAME SEARCH - Setup Instructions for Jai

## 📋 Overview
The frontend is **ALREADY CONFIGURED** to search by Matter Name instead of Claimant Name! 

**All we need:** Update the Salesforce SOQL query to search the `MatterName` field.

---

## 🎯 What Needs to Change (Backend SOQL Only)

### Current SOQL Query:
```sql
SELECT ClaimentName__c, MatterName__c, Id 
FROM Matter__c 
WHERE ClaimentName__c LIKE '%{searchKey}%'
```

### New SOQL Query (Option 1 - Matter Name Only):
```sql
SELECT ClaimentName__c, MatterName__c, Id 
FROM Matter__c 
WHERE MatterName__c LIKE '%{searchKey}%'
```

### New SOQL Query (Option 2 - BEST - Search Both Fields):
```sql
SELECT ClaimentName__c, MatterName__c, Id 
FROM Matter__c 
WHERE MatterName__c LIKE '%{searchKey}%' 
   OR ClaimentName__c LIKE '%{searchKey}%'
```

**Recommendation:** Use Option 2 for maximum flexibility!

---

## 🔧 Where to Make the Change

**Salesforce Apex Class:** `AI_Flask_App_Fetch_Matter`

**Endpoint:** 
```
https://sweetjames--sjfull.sandbox.my.salesforce-sites.com/SmartReceptionAI/services/apexrest/AI_Flask_App_Fetch_Matter
```

**Method:** Update the SOQL WHERE clause in the `fetchMatter` method

---

## ✅ Frontend Changes (ALREADY DONE!)

✅ Dropdown displays **Matter Name** as primary field  
✅ Claimant name shown as secondary info  
✅ Search placeholder updated: "Search by matter name or claimant..."  
✅ All 3 fields auto-populate (claimant, matter_name, matter_id)  
✅ Code is **future-proof** - will work immediately after SOQL update!

---

## 🚀 Example Flow (After Your Update)

**User types:** `"auto accident"`

**Salesforce searches:** MatterName field for "auto accident"

**Returns:**
```json
[
  {
    "ClaimentName": "Ryan Powers",
    "MatterName": "Ryan Powers | CA | 10/24/25 | Auto",
    "MatterId": "a0L5f0000058N4j"
  },
  {
    "ClaimentName": "Maria Garcia", 
    "MatterName": "Maria Garcia | TX | 09/15/24 | Auto",
    "MatterId": "a0L5f0000058N5k"
  }
]
```

**Dropdown shows:**
```
Ryan Powers | CA | 10/24/25 | Auto (Ryan Powers)
Maria Garcia | TX | 09/15/24 | Auto (Maria Garcia)
```

**User selects matter → All 3 fields auto-populate instantly!**

---

## 🧪 Testing

After you update the SOQL:

1. Open Check Detail page
2. Click the Claimant dropdown
3. Type "auto" (or any matter-related keyword)
4. Should see matters with "auto" in the name
5. Select a matter → all 3 fields populate

---

## 📞 Questions?

Hit up Kannon if you need clarification!

**The frontend is LOCKED AND LOADED - just waiting on that SOQL update! 🔥**
