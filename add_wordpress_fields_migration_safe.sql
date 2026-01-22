-- Migration: Add WordPress-specific fields to content table (Safe Version)
-- Date: 2025-01-XX
-- Description: Adds post_title, post_excerpt, and permalink columns for WordPress post type
-- This version checks if columns exist before adding them

USE vernalcontentum_contentMachine;

-- Check if post_title column exists, if not add it
SET @col_exists = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND column_name = 'post_title'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `content` ADD COLUMN `post_title` VARCHAR(255) NULL COMMENT ''WordPress post title (SEO-optimized)'' AFTER `landing_page_url`;',
    'SELECT ''Column post_title already exists'' AS info;'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check if post_excerpt column exists, if not add it
SET @col_exists = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND column_name = 'post_excerpt'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `content` ADD COLUMN `post_excerpt` TEXT NULL COMMENT ''WordPress post excerpt'' AFTER `post_title`;',
    'SELECT ''Column post_excerpt already exists'' AS info;'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check if permalink column exists, if not add it
SET @col_exists = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND column_name = 'permalink'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `content` ADD COLUMN `permalink` VARCHAR(255) NULL COMMENT ''Optimized WordPress permalink/slug'' AFTER `post_excerpt`;',
    'SELECT ''Column permalink already exists'' AS info;'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add indexes (only if they don't exist)
-- Check and add idx_content_permalink
SET @index_exists = (
    SELECT COUNT(*) 
    FROM information_schema.statistics 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND index_name = 'idx_content_permalink'
);

SET @sql = IF(@index_exists = 0,
    'CREATE INDEX `idx_content_permalink` ON `content`(`permalink`);',
    'SELECT ''Index idx_content_permalink already exists'' AS info;'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check and add idx_content_post_title
SET @index_exists = (
    SELECT COUNT(*) 
    FROM information_schema.statistics 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND index_name = 'idx_content_post_title'
);

SET @sql = IF(@index_exists = 0,
    'CREATE INDEX `idx_content_post_title` ON `content`(`post_title`(100));',
    'SELECT ''Index idx_content_post_title already exists'' AS info;'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT 'Migration completed. Check messages above for any issues.' AS status;

