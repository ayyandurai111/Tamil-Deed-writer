"""
constants.py
============
Shared constants: file paths, field definitions, PAN threshold.

RULE: Every {{PLACEHOLDER}} in every skeleton template MUST have a matching
key here. Field key == placeholder name (no MOBILE vs PHONE confusion).

LAW SOURCES:
  1. Registration Act 1908 — S.17, S.21, S.23, S.28, S.32A
  2. Transfer of Property Act 1882 — S.54
  3. Income Tax Act 1961 — Rule 114B (PAN >₹10L), S.194-IA (TDS >₹50L)
  4. TNREGINET — Aadhaar mandatory for biometric at SRO
  5. TN Land Reforms Act 1961 — extent & land nature for ceiling compliance
  6. Stamp Act 1899 / TN Stamp Act
"""

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

_output_env = os.environ.get("OUTPUT_DIR", "")
OUTPUT_DIR  = Path(_output_env) if _output_env else Path("/tmp/tamil-deed-output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://tamil-deed-writer.onrender.com")

# ── PAN / TDS thresholds ───────────────────────────────────────────────────────
PAN_THRESHOLD = 1_000_000    # ₹10 lakh  — Rule 114B
TDS_THRESHOLD = 5_000_000    # ₹50 lakh  — S.194-IA

# Shared month number → Tamil name map (used by extract_fields + resolve_date)
TAMIL_MONTHS = {
    1:  "ஜனவரி",   2:  "பிப்ரவரி", 3:  "மார்ச்",
    4:  "ஏப்ரல்",  5:  "மே",        6:  "ஜூன்",
    7:  "ஜூலை",    8:  "ஆகஸ்ட்",   9:  "செப்டம்பர்",
    10: "அக்டோபர்", 11: "நவம்பர்",  12: "டிசம்பர்",
}

# ── OPTIONAL FIELDS ────────────────────────────────────────────────────────────
# Fields the user may NOT provide. fill_skeleton cleanup will set these to None
# when blank, so generate_docx skips the phrase entirely — no "___" in output.
OPTIONAL_FIELDS = {
    "agriculture": frozenset({
        # Stamp
        "STAMP_VALUE",
        # Party optional details
        "VENDOR_CASTE",       "VENDOR_OCCUPATION",
        "VENDOR_VILLAGE",     "VENDOR_VATTAM",     "VENDOR_DISTRICT",
        "PURCHASER_CASTE",    "PURCHASER_OCCUPATION",
        "PURCHASER_VILLAGE",  "PURCHASER_VATTAM",  "PURCHASER_DISTRICT",
        # Property optional
        "CHITTA_NO",          "A_REGISTER_NO",
        "BUILDINGS",          "TREES",             "WATER_STRUCTURES",
        # Agriculture special
        # NANJAI_PUNJAI_DETAIL removed — template now uses {{NANJAI_OR_PUNJAI}} consistently
        "STANDING_CROPS",     "TREES_DETAIL",      "FARM_STRUCTURE",
        # Consideration optional
        "ADVANCE_DATE",       "ADVANCE_AMOUNT",
        "BALANCE_DATE",       "TRANSACTION_NO",    "TRANSACTION_DATE",
        # Chain of title — 3rd owner optional
        "OWNER_3",            "DOC_NO_3",
        # Documents handed over — all optional
        "MOTHER_DEED",        "PATTA_COPY",        "CHITTA_ADANGAL",
        "EC_COPY",            "FMB_SKETCH",        "TAX_RECEIPTS",
        "ID_COPIES",          "OTHER_DOCS",
        # Witness Aadhaar optional
        "WITNESS1_AADHAAR",   "WITNESS2_AADHAAR",
    }),
    "plot": frozenset({
        "STAMP_VALUE",
        "VENDOR_CASTE",       "VENDOR_OCCUPATION",
        "PURCHASER_CASTE",    "PURCHASER_OCCUPATION",
        "ADVANCE_DATE",       "ADVANCE_AMOUNT",
        "BALANCE_DATE",       "TRANSACTION_NO",    "TRANSACTION_DATE",
        "WITNESS1_AADHAAR",   "WITNESS2_AADHAAR",
    }),
}

# ── CRITICAL FIELDS — must be present before docx generation ──────────────────
# KEY RULE: Every key here must match the {{PLACEHOLDER}} name in the skeleton
# exactly. These are the MINIMUM required fields per deed type.
CRITICAL_FIELDS = {

    # ══════════════════════════════════════════════════════════════════════════
    # PLOT DEED
    # ══════════════════════════════════════════════════════════════════════════
    "plot": {
        "DATE_DAY":           "பத்திர தேதி — நாள்",
        "DATE_MONTH":         "பத்திர தேதி — மாதம்",
        "DATE_YEAR":          "பத்திர தேதி — ஆண்டு",
        "PURCHASER_NAME":     "வாங்குபவர் பெயர்",
        "PURCHASER_FATHER":   "வாங்குபவர் தந்தை / கணவர் பெயர்",
        "PURCHASER_AGE":      "வாங்குபவர் வயது",
        "PURCHASER_ADDRESS":  "வாங்குபவர் முழு விலாசம்",
        "PURCHASER_AADHAAR":  "வாங்குபவர் ஆதார் எண் (12 இலக்கம்)",
        "PURCHASER_PHONE":    "வாங்குபவர் கைபேசி எண்",
        "VENDOR_NAME":        "விற்பவர் பெயர்",
        "VENDOR_FATHER":      "விற்பவர் தந்தை / கணவர் பெயர்",
        "VENDOR_AGE":         "விற்பவர் வயது",
        "VENDOR_ADDRESS":     "விற்பவர் முழு விலாசம்",
        "VENDOR_AADHAAR":     "விற்பவர் ஆதார் எண் (12 இலக்கம்)",
        "VENDOR_PHONE":       "விற்பவர் கைபேசி எண்",
        "TOTAL_AMOUNT":       "மொத்த விற்பனை தொகை (ரூ. எண்ணில்)",
        "AMOUNT_WORDS":       "மொத்த தொகை எழுத்தில்",
        "PAYMENT_MODE":       "செலுத்திய விதம்",
        "BALANCE_AMOUNT":     "இருப்பு தொகை",
        "BANK_NAME":          "வங்கி பெயர்",
        "WITNESS1_NAME":      "சாட்சி 1 பெயர்",
        "WITNESS1_ADDRESS":   "சாட்சி 1 விலாசம்",
        "WITNESS2_NAME":      "சாட்சி 2 பெயர்",
        "WITNESS2_ADDRESS":   "சாட்சி 2 விலாசம்",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # AGRICULTURE DEED
    # ══════════════════════════════════════════════════════════════════════════
    "agriculture": {
        # ── Header ────────────────────────────────────────────────────────────
        "DATE_DAY":           "பத்திர தேதி — நாள்",
        "DATE_MONTH":         "பத்திர தேதி — மாதம்",
        "DATE_YEAR":          "பத்திர தேதி — ஆண்டு",
        "REG_OFFICE":         "பதிவு அலுவலகம்",
        "DISTRICT":           "மாவட்டம்",
        "TALUK":              "தாலுக்கா",

        # ── Vendor ────────────────────────────────────────────────────────────
        "VENDOR_PREFIX":      "விற்பவர் முன்னொட்டு (திரு / திருமதி / செல்வி)",
        "VENDOR_NAME":        "விற்பவர் பெயர்",
        "VENDOR_RELATION":    "விற்பவர் உறவு (மகன் / மகள் / மனைவி)",
        "VENDOR_FATHER":      "விற்பவர் தந்தை / கணவர் பெயர்",
        "VENDOR_AGE":         "விற்பவர் வயது",
        "VENDOR_ADDRESS":     "விற்பவர் முழு விலாசம்",
        "VENDOR_AADHAAR":     "விற்பவர் ஆதார் எண் (12 இலக்கம்)",
        "VENDOR_PHONE":       "விற்பவர் கைபேசி எண்",

        # ── Purchaser ─────────────────────────────────────────────────────────
        "PURCHASER_PREFIX":   "வாங்குபவர் முன்னொட்டு",
        "PURCHASER_NAME":     "வாங்குபவர் பெயர்",
        "PURCHASER_RELATION": "வாங்குபவர் உறவு",
        "PURCHASER_FATHER":   "வாங்குபவர் தந்தை / கணவர் பெயர்",
        "PURCHASER_AGE":      "வாங்குபவர் வயது",
        "PURCHASER_ADDRESS":  "வாங்குபவர் முழு விலாசம்",
        "PURCHASER_AADHAAR":  "வாங்குபவர் ஆதார் எண் (12 இலக்கம்)",
        "PURCHASER_PHONE":    "வாங்குபவர் கைபேசி எண்",

        # ── Property ──────────────────────────────────────────────────────────
        "PROP_DISTRICT":      "சொத்து மாவட்டம்",
        "PROP_TALUK":         "சொத்து தாலுக்கா",
        "PROP_VILLAGE":       "சொத்து கிராமம்",
        "REVENUE_VILLAGE":    "வருவாய் கிராமம்",
        "PROP_VATTAM":        "சொத்து வட்டம்",
        "SURVEY_NO":          "சர்வே / புல எண்",
        "SUBDIVISION":        "உட்பிரிவு எண்",
        "PATTA_NO":           "பட்டா எண்",
        "LAND_TYPE":          "நில வகை",
        "NANJAI_OR_PUNJAI":   "நஞ்சை அல்லது புஞ்சை",
        "WATER_SOURCE":       "நீர் ஆதாரம்",
        "EXTENT_ACRE":        "ஏக்கர் அளவு",
        "EXTENT_CENT":        "சென்ட் அளவு",
        "BOUNDARY_EAST":      "கிழக்கு எல்லை",
        "BOUNDARY_WEST":      "மேற்கு எல்லை",
        "BOUNDARY_NORTH":     "வடக்கு எல்லை",
        "BOUNDARY_SOUTH":     "தெற்கு எல்லை",

        # ── Consideration ─────────────────────────────────────────────────────
        "TOTAL_AMOUNT":       "மொத்த விற்பனை தொகை (ரூ. எண்ணில்)",
        "AMOUNT_WORDS":       "மொத்த தொகை எழுத்தில்",
        "PAYMENT_MODE":       "செலுத்திய விதம்",
        "BALANCE_AMOUNT":     "இருப்பு தொகை",
        "BANK_NAME":          "வங்கி பெயர்",

        # ── Chain of title — at least 1st owner required ───────────────────
        "OWNER_1":            "1வது உரிமையாளர் பெயர்",
        "DOC_NO_1":           "1வது ஆவண எண்",
        "OWNER_2":            "2வது உரிமையாளர் பெயர்",
        "DOC_NO_2":           "2வது ஆவண எண்",

        # ── Witnesses ─────────────────────────────────────────────────────────
        "WITNESS1_NAME":      "சாட்சி 1 பெயர்",
        "WITNESS1_ADDRESS":   "சாட்சி 1 விலாசம்",
        "WITNESS2_NAME":      "சாட்சி 2 பெயர்",
        "WITNESS2_ADDRESS":   "சாட்சி 2 விலாசம்",
    },
}
