-- Migration: Add WordPress-specific fields to content table
-- Date: 2025-01-XX
-- Description: Adds post_title, post_excerpt, and permalink columns for WordPress post type

-- Add WordPress-specific columns to content table
ALTER TABLE `content` 
ADD COLUMN `post_title` VARCHAR(255) NULL COMMENT 'WordPress post title (SEO-optimized)' AFTER `landing_page_url`,
ADD COLUMN `post_excerpt` TEXT NULL COMMENT 'WordPress post excerpt' AFTER `post_title`,
ADD COLUMN `permalink` VARCHAR(255) NULL COMMENT 'Optimized WordPress permalink/slug' AFTER `post_excerpt`;

-- Add indexes for better query performance (optional but recommended)
CREATE INDEX `idx_content_permalink` ON `content`(`permalink`);
CREATE INDEX `idx_content_post_title` ON `content`(`post_title`(100)); -- Prefix index for VARCHAR

