-- Add campaign planning and content pre-population fields
-- Adds fields to campaigns and content tables

-- Campaign table: Add scheduling, planning, and queue fields
ALTER TABLE campaigns 
ADD COLUMN scheduling_settings_json TEXT NULL,
ADD COLUMN campaign_plan_json TEXT NULL,
ADD COLUMN content_queue_items_json TEXT NULL;

-- Content table: Add campaign linking and editing fields
ALTER TABLE content
ADD COLUMN campaign_id VARCHAR(255) NULL,
ADD COLUMN is_draft BOOLEAN DEFAULT TRUE,
ADD COLUMN can_edit BOOLEAN DEFAULT TRUE,
ADD COLUMN knowledge_graph_location TEXT NULL,
ADD COLUMN parent_idea TEXT NULL,
ADD COLUMN landing_page_url VARCHAR(500) NULL;


