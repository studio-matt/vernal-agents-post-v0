-- Check and add WordPress columns to content table
-- This script checks if columns exist before adding them

USE vernalcontentum_contentMachine;

-- Check if post_title column exists
SET @col_exists = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND column_name = 'post_title'
);

-- Add post_title if it doesn't exist
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `content` ADD COLUMN `post_title` VARCHAR(255) NULL COMMENT ''WordPress post title (SEO-optimized)'' AFTER `landing_page_url`;',
    'SELECT ''Column post_title already exists'' AS info;'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check if post_excerpt column exists
SET @col_exists = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND column_name = 'post_excerpt'
);

-- Add post_excerpt if it doesn't exist
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `content` ADD COLUMN `post_excerpt` TEXT NULL COMMENT ''WordPress post excerpt'' AFTER `post_title`;',
    'SELECT ''Column post_excerpt already exists'' AS info;'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check if permalink column exists
SET @col_exists = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content' 
    AND column_name = 'permalink'
);

-- Add permalink if it doesn't exist
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `content` ADD COLUMN `permalink` VARCHAR(255) NULL COMMENT ''Optimized WordPress permalink/slug'' AFTER `post_excerpt`;',
    'SELECT ''Column permalink already exists'' AS info;'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check and add indexes
-- Check if idx_content_permalink exists
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

-- Check if idx_content_post_title exists
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

-- Show final status
SELECT 'Migration check completed. Check messages above for any issues.' AS status;

