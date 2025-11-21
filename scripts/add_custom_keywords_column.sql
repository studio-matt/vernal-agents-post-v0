-- Add custom_keywords_json column to campaigns table
-- This stores custom keywords/ideas per campaign

ALTER TABLE campaigns 
ADD COLUMN custom_keywords_json TEXT NULL;

