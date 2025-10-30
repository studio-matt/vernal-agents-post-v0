-- Clear all campaign records from database
-- Safe to run - campaigns are not referenced by other tables

-- First, verify what we're about to delete
SELECT COUNT(*) as campaign_count FROM campaigns;

-- Show campaign details before deletion (optional)
SELECT id, campaign_id, campaign_name, user_id, created_at FROM campaigns ORDER BY created_at DESC;

-- Delete all campaigns
DELETE FROM campaigns;

-- Verify deletion
SELECT COUNT(*) as remaining_campaigns FROM campaigns;

-- Should return 0

