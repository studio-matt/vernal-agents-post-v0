#!/usr/bin/env python3
"""
Migration script to populate system settings with hardcoded agent definitions.
This extracts agent data from agents.py and saves it to the system_settings table.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import SystemSettings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Hardcoded agent definitions from agents.py
AGENT_DEFINITIONS = {
    # Research Agents
    "script_research": {
        "role": "Script Research Agent",
        "goal": "Research and analyze content for script generation",
        "backstory": "You are an expert content researcher who analyzes information and creates detailed research reports.",
    },
    # QC Agents
    "qc": {
        "role": "Quality Control Agent",
        "goal": "Review and ensure quality of generated content",
        "backstory": "You are a meticulous quality control specialist who ensures all content meets high standards.",
    },
    "instagram_qc": {
        "role": "Instagram QC Agent",
        "goal": "Review and ensure quality of Instagram content",
        "backstory": "You are a quality control specialist focused on Instagram content standards.",
    },
    "facebook_qc": {
        "role": "Facebook QC Agent",
        "goal": "Review and ensure quality of Facebook content",
        "backstory": "You are a quality control specialist focused on Facebook content standards.",
    },
    "youtube_qc": {
        "role": "YouTube QC Agent",
        "goal": "Review and ensure quality of YouTube content",
        "backstory": "You are a quality control specialist focused on YouTube content standards.",
    },
    "twitter_qc": {
        "role": "Twitter QC Agent",
        "goal": "Review and ensure quality of Twitter content",
        "backstory": "You are a quality control specialist focused on Twitter content standards.",
    },
    "linkedin_qc": {
        "role": "LinkedIn QC Agent",
        "goal": "Review and ensure quality of LinkedIn content",
        "backstory": "You are a quality control specialist focused on LinkedIn content standards.",
    },
    "wordpress_qc": {
        "role": "WordPress QC Agent",
        "goal": "Review and ensure quality of WordPress content",
        "backstory": "You are a quality control specialist focused on WordPress content standards.",
    },
    "tiktok_qc": {
        "role": "TikTok QC Agent",
        "goal": "Review and ensure quality of TikTok content",
        "backstory": "You are a quality control specialist focused on TikTok content standards.",
    },
    # Writing Agents
    "instagram": {
        "role": "Instagram Content Agent",
        "goal": "Create visual Instagram content",
        "backstory": "You are an Instagram specialist who creates visually appealing and engaging posts.",
    },
    "facebook": {
        "role": "Facebook Content Agent",
        "goal": "Create engaging Facebook content",
        "backstory": "You are a Facebook content specialist who creates viral and engaging posts.",
    },
    "youtube": {
        "role": "YouTube Content Agent",
        "goal": "Create YouTube video content",
        "backstory": "You are a YouTube specialist who creates engaging video scripts and descriptions.",
    },
    "twitter": {
        "role": "Twitter Content Agent",
        "goal": "Create concise Twitter content",
        "backstory": "You are a Twitter specialist who creates impactful tweets within character limits.",
    },
    "linkedin": {
        "role": "LinkedIn Content Agent",
        "goal": "Create professional LinkedIn content",
        "backstory": "You are a LinkedIn content specialist who creates engaging professional posts.",
    },
    "wordpress": {
        "role": "WordPress Content Agent",
        "goal": "Create WordPress blog content",
        "backstory": "You are a WordPress specialist who creates SEO-optimized blog posts.",
    },
    "tiktok": {
        "role": "TikTok Content Agent",
        "goal": "Create viral TikTok content",
        "backstory": "You are a TikTok specialist who creates short-form viral content.",
    },
    "script_rewriter": {
        "role": "Script Rewriter Agent",
        "goal": "Rewrite and improve existing scripts",
        "backstory": "You are a script rewriting specialist who improves and optimizes existing content.",
    },
    "regenrate_content": {
        "role": "Content Regeneration Agent",
        "goal": "Regenerate and refresh existing content",
        "backstory": "You are a content regeneration specialist who refreshes and updates existing content.",
    },
    "regenrate_subcontent": {
        "role": "Subcontent Regeneration Agent",
        "goal": "Regenerate subcontent and variations",
        "backstory": "You are a subcontent specialist who creates variations and subcontent from main content.",
    },
}

def migrate_agents():
    """Migrate hardcoded agent definitions to system settings."""
    db = SessionLocal()
    try:
        # Determine which tab each agent belongs to
        research_agents = ["script_research"]
        writing_agents = ["instagram", "facebook", "youtube", "twitter", "linkedin", "wordpress", "tiktok", "script_rewriter", "regenrate_content", "regenrate_subcontent"]
        qc_agents = ["qc", "instagram_qc", "facebook_qc", "youtube_qc", "twitter_qc", "linkedin_qc", "wordpress_qc", "tiktok_qc"]
        
        migrated_count = 0
        
        for agent_name, agent_data in AGENT_DEFINITIONS.items():
            # Determine tab
            if agent_name in research_agents:
                tab = "research"
            elif agent_name in writing_agents:
                tab = "writing"
            elif agent_name in qc_agents:
                tab = "qc"
            else:
                logger.warning(f"Unknown agent type for {agent_name}, skipping")
                continue
            
            # Save each field
            fields = ["role", "goal", "backstory"]
            for field in fields:
                setting_key = f"{tab}_agent_{agent_name}_{field}"
                setting_value = agent_data.get(field, "")
                
                # Check if setting already exists
                existing = db.query(SystemSettings).filter(
                    SystemSettings.setting_key == setting_key
                ).first()
                
                if existing:
                    # Update if different
                    if existing.setting_value != setting_value:
                        existing.setting_value = setting_value
                        logger.info(f"Updated {setting_key}")
                        migrated_count += 1
                    else:
                        logger.debug(f"Setting {setting_key} already exists with same value")
                else:
                    # Create new setting
                    new_setting = SystemSettings(
                        setting_key=setting_key,
                        setting_value=setting_value,
                        description=f"{agent_name.replace('_', ' ').title()} {field}"
                    )
                    db.add(new_setting)
                    logger.info(f"Created {setting_key}")
                    migrated_count += 1
        
        db.commit()
        logger.info(f"✅ Migration complete! Migrated {migrated_count} settings.")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_agents()

