-- Migration: Add WordPress-specific fields to content table
-- Date: 2025-01-XX
-- Description: Adds post_title, post_excerpt, and permalink columns for WordPress post type

USE vernalcontentum_contentMachine;

-- Check if content table exists first
SET @table_exists = (
    SELECT COUNT(*) 
    FROM information_schema.tables 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content'
);

-- Only proceed if table exists
SET @sql = IF(@table_exists > 0, 
    'ALTER TABLE `content` 
    ADD COLUMN IF NOT EXISTS `post_title` VARCHAR(255) NULL COMMENT ''WordPress post title (SEO-optimized)'' AFTER `landing_page_url`,
    ADD COLUMN IF NOT EXISTS `post_excerpt` TEXT NULL COMMENT ''WordPress post excerpt'' AFTER `post_title`,
    ADD COLUMN IF NOT EXISTS `permalink` VARCHAR(255) NULL COMMENT ''Optimized WordPress permalink/slug'' AFTER `post_excerpt`;',
    'SELECT ''ERROR: content table does not exist in database'' AS error;'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add indexes only if columns exist (MySQL doesn't support IF NOT EXISTS for indexes, so we check first)
-- Check if post_title column exists and add index
SET @col_exists = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND column_name = 'post_title'
);

SET @index_exists = (
    SELECT COUNT(*) 
    FROM information_schema.statistics 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND index_name = 'idx_content_post_title'
);

SET @sql = IF(@col_exists > 0 AND @index_exists = 0,
    'CREATE INDEX `idx_content_post_title` ON `content`(`post_title`(100));',
    'SELECT ''Index idx_content_post_title already exists or column does not exist'' AS info;'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check if permalink column exists and add index
SET @col_exists = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND column_name = 'permalink'
);

SET @index_exists = (
    SELECT COUNT(*) 
    FROM information_schema.statistics 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND index_name = 'idx_content_permalink'
);

SET @sql = IF(@col_exists > 0 AND @index_exists = 0,
    'CREATE INDEX `idx_content_permalink` ON `content`(`permalink`);',
    'SELECT ''Index idx_content_permalink already exists or column does not exist'' AS info;'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

