-- Migration: Add WordPress category_id and author_id columns to content table
-- Date: 2026-01-28
-- Description: Adds category_id and author_id columns for WordPress post category and author assignment

USE vernalcontentum_contentMachine;

-- Check if category_id column exists, if not add it
SET @col_exists = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND column_name = 'category_id'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `content` ADD COLUMN `category_id` INT NULL COMMENT ''WordPress category ID for this post'' AFTER `permalink`;',
    'SELECT ''Column category_id already exists'' AS info;'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check if author_id column exists, if not add it
SET @col_exists = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND column_name = 'author_id'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `content` ADD COLUMN `author_id` INT NULL COMMENT ''WordPress author ID for this post'' AFTER `category_id`;',
    'SELECT ''Column author_id already exists'' AS info;'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT 'Migration completed. Check messages above for any issues.' AS status;
