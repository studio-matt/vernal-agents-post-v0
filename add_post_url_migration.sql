-- Migration: Add post_url column to content table
-- This column stores the published URL for content posted to any platform
-- (WordPress permalink, LinkedIn post URL, Facebook post URL, etc.)

-- Check if column already exists before adding
SET @dbname = DATABASE();
SET @tablename = "content";
SET @columnname = "post_url";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (COLUMN_NAME = @columnname)
  ) > 0,
  "SELECT 'Column post_url already exists in content table.' AS result;",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " VARCHAR(500) NULL COMMENT 'Published URL for any platform (WordPress permalink, LinkedIn post URL, etc.)';")
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

