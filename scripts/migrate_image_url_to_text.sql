-- Migration script to change image_url column from VARCHAR(255) to TEXT
-- This is needed because DALL·E image URLs with SAS tokens can exceed 255 characters

-- Run this on your MySQL database:
-- mysql -u your_user -p your_database < scripts/migrate_image_url_to_text.sql

USE your_database_name;

ALTER TABLE content MODIFY COLUMN image_url TEXT NULL;

-- Verify the change
DESCRIBE content;

