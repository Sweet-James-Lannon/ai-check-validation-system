# Check Split Bug Fix - Cache Busting Implementation

## Problem
When splitting a check (e.g., 4-page check → split off page 1), the split worked correctly in the database, but when viewing the original check again, it showed **stale/cached pages**:
- **Expected**: Original check should show Pages 2, 3, 4
- **Actual**: Original check showed Pages 1, 2, (Page 3 missing - Page 1 duplicated)

## Root Cause
**Aggressive PDF caching** at multiple levels:
1. **Server-side cache** (Python in-memory): Used `{check_id}_{page_index}` as key → didn't change after split
2. **HTTP cache headers**: `Cache-Control: public, max-age=86400` (24 hours) → browser cached old PDFs
3. **Frontend PDF.js cache**: Map keyed by URL → didn't invalidate after database updates

## Solution Implemented

### 1. Server-Side Cache Busting (dashboard_routes.py)
- **Added `updated_at` to cache key**: `{check_id}_{page_index}_{updated_at}`
- **Removed aggressive browser caching**: Changed from `max-age=86400` to `no-cache, no-store, must-revalidate`
- **Added validation logging**: Checks if requested page index is within bounds of updated batch_images array

### 2. Frontend Cache Busting (check_detail.html)
- **Added timestamp to PDF URLs**: `/checks/pdf/{id}/{index}?t={updated_at}`
- **Stored check metadata**: Added `checkUpdatedAt` variable from `{{ check.updated_at }}`
- **Updated all PDF URL constructions**:
  - Main PDF rendering function
  - Background preload function
  - Thumbnail rendering function
- **Clear cache on page load**: `pdfCache.clear()` ensures fresh start

### 3. Enhanced Split Logging (api_routes.py)
Added detailed logging to track exactly what pages go where:
```python
📄 === ORIGINAL BATCH IMAGES ===
   Index 0: file1.pdf
   Index 1: file2.pdf
   Index 2: file3.pdf
   
📄 === SPLIT IMAGES (going to NEW check) ===
   Index 0: file1.pdf
   
📄 === REMAINING IMAGES (staying in ORIGINAL check) ===
   Index 0: file2.pdf
   Index 1: file3.pdf
```

## Files Modified

### `/routes/dashboard_routes.py`
- Line ~640: Updated `serve_check_pdf()` function
  - Fetch `updated_at` from database
  - Use `updated_at` in cache key
  - Set `no-cache` headers to prevent browser caching

### `/templates/check_detail.html`
- Line ~1843: Added `checkId` and `checkUpdatedAt` global variables
- Line ~3117: Updated `preloadPDF()` - added `?t=` parameter
- Line ~3195: Updated `renderPDF()` - added `?t=` parameter  
- Line ~4917: Updated `renderThumbnail()` - added `?t=` parameter
- Line ~3062: Added `pdfCache.clear()` on page load

### `/routes/api_routes.py`
- Line ~354-380: Enhanced split logging with detailed page tracking
- Line ~517: Fixed undefined `next_letter` variable bug

## How It Works Now

1. **User splits a check**:
   - Backend updates `batch_images` array
   - Backend updates `updated_at` timestamp
   - New check created with selected pages
   - Original check updated with remaining pages

2. **User navigates back to original check**:
   - Template renders with NEW `updated_at` value
   - PDF URLs include `?t={new_timestamp}` parameter
   - Browser sees different URL → bypasses cache
   - Server cache uses `{check_id}_{page_index}_{new_timestamp}` → cache miss
   - Server fetches fresh data from Supabase
   - Correct pages are displayed!

## Testing Instructions

1. **Start Flask app** and navigate to a check with multiple pages
2. **Select page 1** and split it off
3. **Verify new check** (e.g., 002-2) contains ONLY page 1
4. **Navigate back to original check** (002-1)
5. **Verify original check** contains ONLY pages 2, 3, 4 (NO page 1, NO missing pages)
6. **Check browser dev tools Network tab**: Should see `?t=` parameter in PDF URLs
7. **Check Flask logs**: Should see detailed split logging with page filenames

## Expected Log Output

```
📄 Total pages before split: 4
📄 Selected indices (will be REMOVED from original): [0]
📄 Remaining indices (will STAY in original): [1, 2, 3]
📄 Split pages (going to NEW check): 1 pages
📄 Remaining pages (staying in ORIGINAL): 3 pages

📄 === ORIGINAL BATCH IMAGES ===
   Index 0: 002-page1.pdf
   Index 1: 002-page2.pdf
   Index 2: 002-page3.pdf
   Index 3: 002-page4.pdf

📄 === SPLIT IMAGES (going to NEW check) ===
   Index 0: 002-page1.pdf

📄 === REMAINING IMAGES (staying in ORIGINAL check) ===
   Index 0: 002-page2.pdf
   Index 1: 002-page3.pdf
   Index 2: 002-page4.pdf

✅ New check created: {uuid} (002-2)
📄 === UPDATING ORIGINAL CHECK {uuid} ===
✅ Current check updated successfully
📄 === AFTER UPDATE - VERIFICATION ===
📄 Updated check page_count: 3
📄 Updated check batch_images length: 3
📄 First page of updated check: 002-page2.pdf
```

## Bonus Fix
Fixed undefined variable `next_letter` in line 517 of api_routes.py (pre-existing bug).
