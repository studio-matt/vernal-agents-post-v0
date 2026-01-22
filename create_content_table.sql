-- Create content table if it doesn't exist
-- This matches the SQLAlchemy Content model definition

USE vernalcontentum_contentMachine;

-- Check if table exists
SET @table_exists = (
    SELECT COUNT(*) 
    FROM information_schema.tables 
    WHERE table_schema = 'vernalcontentum_contentMachine' 
    AND table_name = 'content'
);

-- Create table if it doesn't exist
CREATE TABLE IF NOT EXISTS `content` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `week` INT NOT NULL,
    `day` VARCHAR(20) NOT NULL,
    `content` TEXT NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `status` VARCHAR(20) DEFAULT 'pending',
    `date_upload` DATETIME NOT NULL,
    `platform` VARCHAR(50) NOT NULL,
    `file_name` VARCHAR(255) NOT NULL,
    `file_type` VARCHAR(10) NOT NULL,
    `platform_post_no` VARCHAR(50) NOT NULL,
    `schedule_time` DATETIME NOT NULL,
    `image_url` TEXT NULL,
    `campaign_id` VARCHAR(255) NULL,
    `is_draft` BOOLEAN DEFAULT TRUE,
    `can_edit` BOOLEAN DEFAULT TRUE,
    `knowledge_graph_location` TEXT NULL,
    `parent_idea` TEXT NULL,
    `landing_page_url` VARCHAR(500) NULL,
    `post_title` VARCHAR(255) NULL COMMENT 'WordPress post title (SEO-optimized)',
    `post_excerpt` TEXT NULL COMMENT 'WordPress post excerpt',
    `permalink` VARCHAR(255) NULL COMMENT 'Optimized WordPress permalink/slug',
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_campaign_id` (`campaign_id`),
    INDEX `idx_platform` (`platform`),
    INDEX `idx_status` (`status`),
    INDEX `idx_schedule_time` (`schedule_time`),
    INDEX `idx_content_permalink` (`permalink`),
    INDEX `idx_content_post_title` (`post_title`(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT 'Content table created or already exists' AS status;

