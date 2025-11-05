-- Add settings columns to campaigns table
-- These columns store JSON strings for campaign settings

ALTER TABLE campaigns 
ADD COLUMN extraction_settings_json TEXT NULL,
ADD COLUMN preprocessing_settings_json TEXT NULL,
ADD COLUMN entity_settings_json TEXT NULL,
ADD COLUMN modeling_settings_json TEXT NULL;

