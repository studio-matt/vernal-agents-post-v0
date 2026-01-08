-- Migration script to change writing_samples_json column from TEXT to LONGTEXT
-- This fixes the "Data too long for column" error when storing large writing samples
-- 
-- Run this SQL directly on your MySQL database:
--   mysql -u your_user -p your_database < scripts/migrate_writing_samples_to_longtext.sql
-- 
-- Or execute via Python:
--   python3 scripts/migrate_writing_samples_to_longtext.py

-- Check current column type (optional, for verification)
-- SELECT COLUMN_TYPE 
-- FROM INFORMATION_SCHEMA.COLUMNS 
-- WHERE TABLE_SCHEMA = DATABASE() 
-- AND TABLE_NAME = 'author_personalities' 
-- AND COLUMN_NAME = 'writing_samples_json';

-- Alter column to LONGTEXT (supports up to 4GB)
ALTER TABLE author_personalities 
MODIFY COLUMN writing_samples_json LONGTEXT NULL;

-- Verify the change (optional)
-- SELECT COLUMN_TYPE 
-- FROM INFORMATION_SCHEMA.COLUMNS 
-- WHERE TABLE_SCHEMA = DATABASE() 
-- AND TABLE_NAME = 'author_personalities' 
-- AND COLUMN_NAME = 'writing_samples_json';







