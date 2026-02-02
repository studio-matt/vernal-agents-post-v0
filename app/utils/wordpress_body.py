"""
WordPress body sanitizer: programmatic failsafe so WP body never contains title/excerpt/permalink.
POST_TITLE → WP title field only. POST_EXCERPT → WP excerpt only. PERMALINK → WP slug only.
CONTENT → WP body only. Never save raw model response as WP body.
"""
import re
import logging

logger = logging.getLogger(__name__)


def sanitize_wordpress_body(text: str) -> str:
    """
    Strip title, excerpt, and permalink patterns from text so only body remains.
    Use this whenever setting or sending the WordPress post body (content field).
    Do not rely on the model to avoid outputting these; always sanitize at save/post time.
    """
    if not text or not isinstance(text, str):
        return text or ""

    out = text.strip()
    if not out:
        return ""

    # Remove block patterns (title/excerpt/permalink so only body remains)
    patterns = [
        # Title variants (single line)
        r"^POST_TITLE\s*:?\s*[^\n]*(?:\n|$)",
        r"^Post[_\s]+Title\s*:?\s*[^\n]*(?:\n|$)",
        r"^Title\s*:?\s*[^\n]*(?:\n|$)",
        # Excerpt variants (multiline until next label)
        r"^POST_EXCERPT\s*:?\s*.+?(?=\n\s*(?:POST_|Permalink|Article|Title|Excerpt)|$)",
        r"^Post[_\s]+Excerpt\s*:?\s*.+?(?=\n\s*(?:Post[_\s]+|Permalink|Article|Title|Excerpt)|$)",
        r"^Excerpt\s*:?\s*.+?(?=\n\s*(?:Permalink|Article|Title|Excerpt)|$)",
        # Permalink/slug variants (single line)
        r"^PERMALINK\s*:?\s*[^\n]*(?:\n|$)",
        r"^Permalink\s*:?\s*[^\n]*(?:\n|$)",
        r"^Slug\s*:?\s*[^\n]*(?:\n|$)",
        # Article body label only (remove label, keep rest)
        r"^Article[_\s]+Body\s*:?\s*",
    ]
    for p in patterns:
        out = re.sub(p, "", out, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)

    # Second pass: drop any remaining line that looks like a WordPress field label (failsafe)
    label_starts = (
        "post_title", "post title", "title:", "permalink", "slug:",
        "post_excerpt", "post excerpt", "excerpt:",
    )
    lines = out.split("\n")
    kept = []
    for line in lines:
        low = line.strip().lower()
        if any(low.startswith(s) for s in label_starts):
            continue
        kept.append(line)
    out = "\n".join(kept)

    # Remove JSON-like blocks that contain post_title / post_excerpt / permalink (single-line or short)
    out = re.sub(
        r'\s*\{\s*["\']?post_title["\']?\s*:\s*[^}]+["\']?post_excerpt["\']?\s*:\s*[^}]+["\']?permalink["\']?\s*:\s*[^}]+\}\s*',
        "",
        out,
        flags=re.IGNORECASE,
    )
    # Remove markdown-style headers for these fields
    out = re.sub(r"^#\s*Post\s+Title\s*$", "", out, flags=re.IGNORECASE | re.MULTILINE)
    out = re.sub(r"^#\s*Post\s+Excerpt\s*$", "", out, flags=re.IGNORECASE | re.MULTILINE)
    out = re.sub(r"^#\s*Permalink\s*$", "", out, flags=re.IGNORECASE | re.MULTILINE)
    out = re.sub(r"\*\*Permalink(?:\/Slug)?\*\*\s*[^\n]+", "", out, flags=re.IGNORECASE)
    out = re.sub(r"\*\*Excerpt\*\*\s*[^\n]+", "", out, flags=re.IGNORECASE)

    # Collapse excess newlines
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out
