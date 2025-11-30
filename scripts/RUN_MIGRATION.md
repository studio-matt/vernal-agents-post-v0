# Run Author Profile Migration

## Quick Command

SSH to your backend server and run:

```bash
ssh ubuntu@18.235.104.132
cd /home/ubuntu/vernal-agents-post-v0
bash scripts/add_author_profile_columns.sh
```

## What It Does

This script adds three new columns to the `author_personalities` table:
- `profile_json` - Stores full AuthorProfile JSON
- `liwc_scores` - Quick access to LIWC category scores
- `trait_scores` - MBTI/OCEAN/HEXACO trait scores

## Verification

After running, verify the columns were added:

```bash
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "DESCRIBE author_personalities;" | grep -E "profile_json|liwc_scores|trait_scores"
```

You should see all three columns listed.

## Notes

- Script is idempotent - safe to run multiple times
- Requires `.env` file with database credentials
- No downtime required (adds nullable columns)

