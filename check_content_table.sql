-- Check if content table exists and show its structure
USE vernalcontentum_contentMachine;

-- List all tables
SHOW TABLES;

-- Check if content table exists (case-insensitive check)
SHOW TABLES LIKE 'content';
SHOW TABLES LIKE 'Content';
SHOW TABLES LIKE 'CONTENT';

-- If content table exists, show its structure
SHOW CREATE TABLE content;

-- Show columns if table exists
SHOW COLUMNS FROM content;

