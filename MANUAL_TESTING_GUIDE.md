# Manual Testing Guide - All 4 Fixes

This guide provides step-by-step instructions for manually testing each of the 4 fixes.

---

## ✅ Issue 1: Domain/Platform Marker for Writing Samples

### What to Test
- Domain detection from filename
- Domain detection from URLs in text
- Domain badge display
- Backend receives domain in sample_metadata

### Step-by-Step Instructions

#### Test 1.1: Filename-Based Detection
1. Navigate to **Author Personality** section
2. Click **"Upload"** for Writing Sample #1
3. Create a test file named `linkedin_post.txt` with any text content
4. Upload the file
5. **Expected**: 
   - File name appears with checkmark
   - Domain badge shows "linkedin" next to the sample
   - File content appears in text area

#### Test 1.2: URL-Based Detection
1. In Writing Sample #2, paste text containing:
   ```
   Check out this great article: https://twitter.com/user/status/123456
   ```
2. Click the checkmark to submit
3. **Expected**: Domain badge shows "twitter"

#### Test 1.3: Multiple Domain Detection
1. Upload `facebook_update.txt` → Should show "facebook" badge
2. Upload `instagram_story.txt` → Should show "instagram" badge
3. Upload `blog_post.txt` → Should show "blog" badge
4. Upload `general_content.txt` → Should show "general" or no badge

#### Test 1.4: Backend Verification
1. After uploading samples with domains, click **"Analyze Writing Samples"**
2. Open browser DevTools → Network tab
3. Find the `/author-personalities/analyze` request
4. Check the request payload for `sample_metadata`
5. **Expected**: Each sample should have a `domain` field (linkedin, twitter, etc.)

#### Test 1.5: Backend Logs (Server-Side)
```bash
# SSH to server and check logs
sudo journalctl -u vernal-agents -f | grep -i domain
```
**Expected**: Logs should show domain being used in analysis

---

## ✅ Issue 2: Image Generation Modal

### What to Test
- Modal appears when image generation starts
- Progress is displayed (50% → 100%)
- Modal can be minimized/expanded
- Modal closes when complete

### Step-by-Step Instructions

#### Test 2.1: Basic Image Generation Modal
1. Navigate to **The Plan** step in content creation
2. Ensure you have at least one article/content item
3. Click **"Generate Image"** button for an article
4. **Expected**:
   - Modal appears immediately
   - Shows "Image Generation" as current agent
   - Shows progress (starts at ~50%)
   - Shows task: "Generating image for: [article title]"

#### Test 2.2: Modal Interaction
1. While image is generating, click the minimize button (if available)
2. **Expected**: Modal minimizes but stays visible
3. Click to expand again
4. **Expected**: Modal expands to full view

#### Test 2.3: Multiple Image Generation
1. Click "Generate Image" for 2-3 different articles
2. **Expected**: 
   - Multiple modals appear (stacked)
   - Each shows progress for its respective article
   - Each can be minimized independently

#### Test 2.4: Completion
1. Wait for image generation to complete
2. **Expected**:
   - Progress reaches 100%
   - Status changes to "completed"
   - Modal closes automatically (or can be closed manually)
   - Generated image appears in the article

---

## ✅ Issue 3: Research Assistant Appending (Not Replacing)

### What to Test
- New articles APPEND to existing content
- No articles are replaced
- Content persists after refresh
- Queue items are cleared after conversion

### Step-by-Step Instructions

#### Test 3.1: Initial Content Setup
1. Navigate to **The Plan** step
2. Note how many content items you currently have (e.g., 5 items)
3. Remember the titles of existing items

#### Test 3.2: Add Articles from Research Assistant
1. Navigate to **Research Assistant** tab
2. Select 2-3 articles/recommendations
3. Click **"Add to Content Queue"** or similar button
4. Navigate back to **The Plan** step
5. **Expected**:
   - New articles appear in The Plan
   - **ALL** previous articles are still present
   - Total count = previous count + new count
   - No articles were replaced

#### Test 3.3: Add More Articles
1. Go back to **Research Assistant**
2. Add 2 more articles
3. Return to **The Plan**
4. **Expected**:
   - All previous articles still present
   - New articles added
   - Total = original + first batch + second batch

#### Test 3.4: Persistence Test
1. Refresh the page (F5 or Cmd+R)
2. **Expected**:
   - All articles persist
   - Nothing is lost
   - Count remains the same

#### Test 3.5: Database Verification (Optional)
```bash
# Check database directly
mysql -u [user] -p [database] -e "SELECT id, title FROM content WHERE campaign_id = [your_campaign_id];"
```
**Expected**: All content items are in database

#### Test 3.6: Queue Clearing
1. Add items to queue from Research Assistant
2. Navigate to The Plan
3. Check browser console for logs
4. **Expected**: Console shows "Converting X queue items to content items"
5. Check that `content_queue_items_json` is empty after conversion

---

## ✅ Issue 4: Writing Sample Text Upload

### What to Test
- `.txt` files are properly read
- File content appears in text area
- Delete functionality works
- "Re-Analyze" button appears when samples are modified

### Step-by-Step Instructions

#### Test 4.1: Basic File Upload
1. Navigate to **Author Personality** section
2. Click **"Upload"** for Writing Sample #1
3. Select a `.txt` file (create one with test content if needed)
4. **Expected**:
   - File name appears with checkmark
   - File content appears in the text area (scroll to verify)
   - No error messages

#### Test 4.2: File Content Verification
1. Create a test file `test_sample.txt` with:
   ```
   This is a test writing sample.
   It has multiple lines.
   Line 3 of the sample.
   ```
2. Upload the file
3. **Expected**: All three lines appear in the text area

#### Test 4.3: Analyze Writing Samples
1. Upload 2-3 `.txt` files
2. Click **"Analyze Writing Samples"**
3. **Expected**:
   - Analysis starts
   - No "no valid samples provided" error
   - Analysis completes successfully

#### Test 4.4: Delete Sample
1. After analysis, find a sample with a delete/trash icon
2. Click the delete icon
3. **Expected**:
   - Sample is removed from the list
   - Button text changes to **"Re-Analyze Writing Samples"**

#### Test 4.5: Re-Analyze Button
1. After deleting a sample, add a new sample
2. **Expected**: Button still shows "Re-Analyze Writing Samples"
3. Click "Re-Analyze Writing Samples"
4. **Expected**: Re-analysis completes successfully

#### Test 4.6: Multiple File Types
1. Try uploading a `.md` file (should work)
2. Try uploading a `.doc` file (should be rejected)
3. **Expected**: Only `.txt` and `.md` files are accepted

---

## 🐛 Troubleshooting

### If Domain Badges Don't Appear
- Check browser console for errors
- Verify `detectDomainFromText()` function is called
- Check that `domain` field is set in sample state

### If Image Modal Doesn't Appear
- Check that `activeImageTasks` Set has items
- Verify `AgentStatusModal` component is imported
- Check browser console for errors

### If Articles Are Replaced Instead of Appended
- Check `ThePlanStep.tsx` line 275-287 (queue conversion)
- Verify it uses spread operator: `[...existingContent, ...newContent]`
- Check browser console for "Converting queue items" log

### If File Content Doesn't Appear
- Check that `FileReader.readAsText()` is called
- Verify `reader.onload` handler is executed
- Check browser console for FileReader errors
- Ensure file is valid UTF-8 text

---

## ✅ Success Criteria Checklist

- [ ] Domain badges appear for all detected platforms
- [ ] Image generation modal appears and shows progress
- [ ] Research Assistant articles append (don't replace)
- [ ] Content persists after page refresh
- [ ] `.txt` files upload and content appears
- [ ] Delete sample works
- [ ] Re-analyze button appears when samples are modified
- [ ] No console errors in browser
- [ ] All features work as expected

---

## 📝 Notes

- Some features require backend to be running
- CORS must be properly configured (already fixed)
- Database must be accessible
- Browser DevTools helpful for debugging

