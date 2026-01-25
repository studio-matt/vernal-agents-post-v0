-- Migration: Add cornerstone_platform column to campaigns table
-- This column stores the platform (WordPress, Facebook, or LinkedIn) designated as cornerstone
-- The cornerstone content can be referenced in writing agents via {cornerstone} placeholder

-- Check if column exists before adding
SET @dbname = DATABASE();
SET @tablename = "campaigns";
SET @columnname = "cornerstone_platform";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  "SELECT 'Column cornerstone_platform already exists in campaigns table.' AS result;",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " VARCHAR(50) NULL COMMENT 'Platform designated as cornerstone (WordPress, Facebook, or LinkedIn) - used to reference cornerstone content in writing agents via {cornerstone} placeholder';")
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

