# Author Personality Baseline & Adjustment System - Confirmation

## ✅ CONFIRMED: How the System Works

### 1. Baseline Calculation from LIWC Scores

**Location**: `components/AuthorMimicry.tsx` lines 2340-2346

**How it works:**
- After analyzing writing samples, LIWC scores are calculated for each category
- Each LIWC category's z-score is converted to a percentile (0-100 scale)
- Formula: `percentile = 50 + (z-score × 10)`
  - z-score of 0 = 50th percentile (baseline)
  - z-score of +2 = 70th percentile
  - z-score of -2 = 30th percentile
- These percentiles become the **baseline** for each LIWC category
- Baseline is stored in `baseline_adjustments_json` in the database

**Example:**
```javascript
// LIWC score: { category: "Analytic", z: 1.5 }
// Baseline: 50 + (1.5 × 10) = 65th percentile
// Stored as: { "liwc_analytic": 65 }
```

---

### 2. Adjuster Sliders (User Modifications)

**Location**: `components/AuthorMimicry.tsx` lines 4079-4091

**How it works:**
- Each LIWC category has a slider in the Results section
- Slider shows:
  - **Baseline** (grey bar): Original percentile from LIWC analysis
  - **Adjusted** (blue bar): User-modified value (if different)
  - **Delta**: Difference between adjusted and baseline
- When user moves slider, it updates `baselineAdjustments` state
- Adjusted values are saved to `baseline_adjustments_json` in database
- **These adjustments are GLOBAL** - they apply to all content generation

**Example:**
```
Baseline (from LIWC): 65%
User adjusts slider to: 75%
Delta: +10%
This adjustment applies to ALL platforms
```

---

### 3. Platform-Specific Adjustments

**Location**: `machine_agent.py` lines 80-85

**How it works:**
- Platform-specific **formatting and style guidelines** are applied during content generation
- These are **separate** from baseline adjustments
- Each platform has different:
  - Character limits (Twitter: 280, LinkedIn: 3000, etc.)
  - Tone guidelines (LinkedIn: professional, Twitter: concise, etc.)
  - Formatting rules (hashtags, emojis, structure)

**Example:**
```
Same baseline adjustments (e.g., Analytic: 75%)
+ LinkedIn guidelines → Professional, polished, 2-3 hashtags
+ Twitter guidelines → Concise, witty, trending
```

---

## ⚠️ CLARIFICATION: What's NOT Per-Platform

### Baseline Adjustments are GLOBAL

**Current Implementation:**
- Baseline adjustments (slider values) are **NOT** platform-specific
- When you adjust "Analytic" to 75%, it applies to:
  - LinkedIn posts
  - Twitter posts
  - Instagram posts
  - All platforms equally

**What IS Platform-Specific:**
- Formatting (character limits, hashtags, emojis)
- Tone guidelines (professional vs casual)
- Structure (paragraphs, bullet points)
- But NOT the baseline LIWC percentile values

---

## 🔍 How Content Generation Works

### Step 1: Baseline Calculation
1. Writing samples analyzed → LIWC scores calculated
2. LIWC z-scores → converted to percentiles (baseline)
3. Baseline stored in database

### Step 2: User Adjustments (Optional)
1. User views LIWC chart in Results section
2. User adjusts sliders for specific categories
3. Adjustments saved to `baseline_adjustments_json`
4. **These adjustments are GLOBAL** (apply to all platforms)

### Step 3: Content Generation
1. System loads author personality with baseline + adjustments
2. For each platform:
   - Uses **same baseline adjustments** (global)
   - Applies **platform-specific formatting** (LinkedIn vs Twitter)
   - Generates content matching both

---

## 📊 Visual Example

```
┌─────────────────────────────────────────┐
│  Author Personality Baseline            │
│  ─────────────────────────────────────  │
│  Analytic: 65% (from LIWC)              │
│  Clout: 72% (from LIWC)                 │
│  Authentic: 58% (from LIWC)            │
└─────────────────────────────────────────┘
              │
              │ User adjusts sliders
              ▼
┌─────────────────────────────────────────┐
│  Adjusted Baseline (Global)             │
│  ─────────────────────────────────────  │
│  Analytic: 75% (+10% adjustment)        │
│  Clout: 72% (no change)                 │
│  Authentic: 65% (+7% adjustment)        │
└─────────────────────────────────────────┘
              │
              ├─────────────────┬─────────────────┐
              ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   LinkedIn   │  │    Twitter   │  │  Instagram   │
    │              │  │              │  │              │
    │ Same baseline│  │ Same baseline│  │ Same baseline│
    │ adjustments  │  │ adjustments  │  │ adjustments  │
    │              │  │              │  │              │
    │ + Professional│  │ + Concise    │  │ + Visual     │
    │   formatting  │  │   formatting │  │   formatting │
    └──────────────┘  └──────────────┘  └──────────────┘
```

---

## ✅ Summary: Your Understanding vs Reality

### What You Said:
> "author personality calculates content on a baseline of some sort and each platform article is adjusted based on the LIWS chart. There is an adjuster there that will change the values of the author personality by that amount."

### What's Actually True:
✅ **YES** - Content is calculated from a baseline (LIWC percentiles)  
✅ **YES** - There is an adjuster (sliders) that changes baseline values  
⚠️ **PARTIALLY** - Platform articles are adjusted, but:
   - Baseline adjustments are **GLOBAL** (same for all platforms)
   - Platform-specific adjustments are **formatting/style only**, not baseline values

### What's NOT True:
❌ Each platform does NOT have separate baseline adjustments  
❌ The adjuster does NOT change values per-platform  
❌ Platform articles are NOT adjusted based on different LIWC values

---

## 🎯 If You Want Per-Platform Baseline Adjustments

**Current State:** Baseline adjustments are global

**If you want per-platform adjustments:**
1. Would need to modify database schema to store per-platform adjustments
2. Would need UI changes to show platform-specific sliders
3. Would need backend changes to apply platform-specific adjustments during generation

**Current Workaround:**
- Use global baseline adjustments
- Rely on platform-specific formatting/guidelines for differences
- Or create separate author personalities for different platforms

---

## 📝 Code References

- **Baseline Calculation**: `AuthorMimicry.tsx:2340-2346`
- **Adjuster Sliders**: `AuthorMimicry.tsx:4079-4091`
- **Platform Guidelines**: `machine_agent.py:80-85`
- **Baseline Storage**: `AuthorMimicry.tsx:2668` (`baseline_adjustments_json`)

