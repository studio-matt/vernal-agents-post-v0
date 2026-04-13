-- Optional: run if `campaigns.image_settings_json` does not exist yet (MySQL/MariaDB).
-- Safe to run once; ignore error if column already exists.
ALTER TABLE campaigns ADD COLUMN image_settings_json TEXT NULL;
