-- Create system_settings table for storing system-wide configuration
-- This table stores settings like LLM prompts, system configuration, etc.

CREATE TABLE IF NOT EXISTS system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(255) NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    description TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_setting_key (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default topic extraction prompt if it doesn't exist
INSERT INTO system_settings (setting_key, setting_value, description)
VALUES (
    'topic_extraction_prompt',
    'You are an expert in topic modeling. Your task is to review the scraped information and extract a list of salient topic names as short, descriptive phrases.\n\nCRITICAL REQUIREMENTS:\n- Each topic MUST be a short, descriptive phrase (2-4 words) that captures a distinct concept\n- Each topic name should be a multi-word phrase if that improves clarity\n- Examples of good topics: ''football offense'', ''public health policy'', ''gun violence'', ''vietnam war history'', ''military strategy analysis''\n- NEVER return single words (e.g., "war", "vietnam", "football", "health" are INVALID)\n- Each phrase must be meaningful, descriptive, and stand alone as an important theme\n- Phrases should reflect specific concepts found in the scraped content, not vague terms\n- Ensure topics are distinct and capture different aspects of the content\n- Prioritize topics that are most relevant to the scraped texts, query, keywords, and URLs\n\nSTRICTLY FORBIDDEN - DO NOT EXTRACT:\n- UI instructions or commands (e.g., "press ctrl", "place your cursor", "enter number", "duplicate pages")\n- Software interface elements (e.g., "blank page", "page break", "min read", "want to duplicate")\n- Keyboard shortcuts or commands (e.g., "press ctrl +", "windows or command")\n- Tutorial step instructions (e.g., "how to duplicate", "select all", "copy paste")\n- Technical identifiers or file extensions (e.g., "press.isbn", "document.pdf", URLs)\n- Generic action phrases without context (e.g., "open file", "save document", "close window")\n\nFocus on EXTRACTING THEMES AND CONCEPTS, not the instructions for how to use software.\n\nReturn EXACTLY {num_topics} topics as a JSON array of strings. Each string must be a 2-4 word descriptive phrase. Do not include explanations, additional text, or markdown formatting (e.g., ```json), just the JSON array.\n\nExample VALID output:\n["vietnam war history", "military strategy analysis", "cold war politics", "southeast asia conflict", "combat operations planning"]\n\nExample INVALID output (DO NOT DO THIS):\n["war", "vietnam", "history", "military", "strategy"]  ← These are single words, NOT valid\n["press ctrl", "place cursor", "duplicate pages", "blank page"]  ← These are UI instructions, NOT valid topics\n\nContext:\n{context}',
    'LLM prompt template for topic extraction. Use {num_topics} and {context} as placeholders.'
)
ON DUPLICATE KEY UPDATE setting_value = setting_value;

