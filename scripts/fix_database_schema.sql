-- Fix database schema for campaign_raw_data table
-- This fixes the "Data too long for column 'raw_html'" error

-- Make raw_html column larger to store large HTML content
ALTER TABLE vernalcontentum_contentMachine.campaign_raw_data
MODIFY COLUMN raw_html MEDIUMTEXT;

-- Verify the change
DESCRIBE vernalcontentum_contentMachine.campaign_raw_data;

