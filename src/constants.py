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

# ── ALL fields per deed type ───────────────────────────────────────────────────
# KEY RULE: Every key here must match the {{PLACEHOLDER}} name in the skeleton
# exactly. No separation between critical/optional — Claude asks for all.
CRITICAL_FIELDS = {

    # ══════════════════════════════════════════════════════════════════════════
    # PLOT DEED
    # ══════════════════════════════════════════════════════════════════════════
    "plot": {

        # ── Header ────────────────────────────────────────────────────────────
        "DATE_DAY":           "பத்திர தேதி — நாள்",
        "DATE_MONTH":         "பத்திர தேதி — மாதம்",
        "DATE_YEAR":          "பத்திர தேதி — ஆண்டு",
        # DATE_WORDS removed — generated automatically from DATE_DAY/MONTH/YEAR

        # ── Purchaser ─────────────────────────────────────────────────────────
        "PURCHASER_NAME":     "வாங்குபவர் பெயர்",
        "PURCHASER_FATHER":   "வாங்குபவர் தந்தை பெயர்",
        "PURCHASER_AGE":      "வாங்குபவர் வயது",
        "PURCHASER_ADDRESS":  "வாங்குபவர் முழு விலாசம்",
        "PURCHASER_ID":       "வாங்குபவர் ஆதார் மற்றும் PAN எண் (உதா: ஆதார்: 1234 5678 9012, PAN: ABCDE1234F)",
        "PURCHASER_PHONE":    "வாங்குபவர் கைபேசி எண்",

        # ── Vendor ────────────────────────────────────────────────────────────
        "VENDOR_NAME":        "விற்பவர் பெயர்",
        "VENDOR_FATHER":      "விற்பவர் தந்தை பெயர்",
        "VENDOR_AGE":         "விற்பவர் வயது",
        "VENDOR_ADDRESS":     "விற்பவர் முழு விலாசம்",
        "VENDOR_ID":          "விற்பவர் ஆதார் மற்றும் PAN எண் (உதா: ஆதார்: 1234 5678 9012, PAN: ABCDE1234F)",
        "VENDOR_PHONE":       "விற்பவர் கைபேசி எண்",

        # ── Prior ownership ───────────────────────────────────────────────────
        "PRIOR_DOC_NO":       "முன்னைய ஆவண எண்",
        "PRIOR_YEAR":         "முன்னைய ஆவண ஆண்டு",
        "PRIOR_REG_OFFICE":   "முன்னைய பதிவு அலுவலகம்",
        "PRIOR_PURCHASE_DATE":"முன்னைய கிரயம் தேதி",

        # ── Consideration ─────────────────────────────────────────────────────
        "TOTAL_AMOUNT":       "மொத்த விற்பனை தொகை (ரூ. எண்ணில்)",
        "AMOUNT_WORDS":       "மொத்த தொகை எழுத்தில்",
        "RECEIVED_AMOUNT":    "பெறப்பட்ட தொகை (ரூ. எண்ணில்)",
        "RECEIVED_WORDS":     "பெறப்பட்ட தொகை எழுத்தில்",
        "PAYMENT_MODE":       "செலுத்திய விதம் (ரொக்கம் / NEFT / RTGS / காசோலை)",

        # ── Handed document ───────────────────────────────────────────────────
        "HANDED_DOC_NO":      "ஒப்படைக்கப்பட்ட ஆவண எண்",

        # ── Property ──────────────────────────────────────────────────────────
        "DOOR_NO":            "கதவு எண்",
        "WARD_NO":            "வார்டு எண்",
        "PLOT_NO":            "Plot எண்",
        "STREET":             "தெரு பெயர்",
        "PROP_AREA":          "பகுதி / ஊர் பெயர்",
        "TALUK":              "தாலுக்கா",
        "PROP_DISTRICT":      "மாவட்டம்",
        "EXTENT_SQFT":        "மொத்த பரப்பு (சதுர அடி / Sq.ft)",

        # ── Boundaries ────────────────────────────────────────────────────────
        "BOUNDARY_EAST":      "கிழக்கு எல்லை",
        "BOUNDARY_WEST":      "மேற்கு எல்லை",
        "BOUNDARY_NORTH":     "வடக்கு எல்லை",
        "BOUNDARY_SOUTH":     "தெற்கு எல்லை",

        # ── Witnesses ─────────────────────────────────────────────────────────
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
        # DATE_WORDS removed — generated automatically from DATE_DAY/MONTH/YEAR
        "REG_OFFICE":         "பதிவு அலுவலகம்",
        "DISTRICT":           "ஜில்லா",
        "TALUK":              "தாலுக்கா",
        "STAMP_VALUE":        "இ-ஸ்டாம்ப் மதிப்பு (ரூ.)",

        # ── Vendor ────────────────────────────────────────────────────────────
        "VENDOR_PREFIX":      "விற்பவர் முன்னொட்டு (திரு / திருமதி / செல்வி)",
        "VENDOR_NAME":        "விற்பவர் பெயர்",
        "VENDOR_RELATION":    "விற்பவர் உறவு (மகன் / மகள் / மனைவி)",
        "VENDOR_FATHER":      "விற்பவர் தந்தை / கணவர் பெயர்",
        "VENDOR_AGE":         "விற்பவர் வயது",
        "VENDOR_CASTE":       "விற்பவர் சாதி / சமூகம்",
        "VENDOR_OCCUPATION":  "விற்பவர் தொழில்",
        "VENDOR_ADDRESS":     "விற்பவர் முழு விலாசம்",
        "VENDOR_VILLAGE":     "விற்பவர் கிராமம்",
        "VENDOR_VATTAM":      "விற்பவர் வட்டம்",
        "VENDOR_DISTRICT":    "விற்பவர் மாவட்டம்",
        "VENDOR_AADHAAR":     "விற்பவர் ஆதார் எண் (12 இலக்கம்)",
        "VENDOR_PAN":         "விற்பவர் PAN எண்",
        "VENDOR_PHONE":       "விற்பவர் கைபேசி எண்",

        # ── Purchaser ─────────────────────────────────────────────────────────
        "PURCHASER_PREFIX":   "வாங்குபவர் முன்னொட்டு",
        "PURCHASER_NAME":     "வாங்குபவர் பெயர்",
        "PURCHASER_RELATION": "வாங்குபவர் உறவு",
        "PURCHASER_FATHER":   "வாங்குபவர் தந்தை / கணவர் பெயர்",
        "PURCHASER_AGE":      "வாங்குபவர் வயது",
        "PURCHASER_CASTE":    "வாங்குபவர் சாதி / சமூகம்",
        "PURCHASER_OCCUPATION":"வாங்குபவர் தொழில்",
        "PURCHASER_ADDRESS":  "வாங்குபவர் முழு விலாசம்",
        "PURCHASER_VILLAGE":  "வாங்குபவர் கிராமம்",
        "PURCHASER_VATTAM":   "வாங்குபவர் வட்டம்",
        "PURCHASER_DISTRICT": "வாங்குபவர் மாவட்டம்",
        "PURCHASER_AADHAAR":  "வாங்குபவர் ஆதார் எண் (12 இலக்கம்)",
        "PURCHASER_PAN":      "வாங்குபவர் PAN எண்",
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
        "CHITTA_NO":          "சிட்டா எண்",
        "LAND_TYPE":          "நில வகை (Government / Private / Ryotwari)",
        "NANJAI_OR_PUNJAI":   "நஞ்சை அல்லது புஞ்சை",
        "WATER_SOURCE":       "நீர் ஆதாரம் (கால்வாய் / கிணறு / ஆழ்துளை / மழை)",
        "A_REGISTER_NO":      "A-Register எண்",
        "EXTENT_ACRE":        "ஏக்கர் அளவு",
        "EXTENT_CENT":        "சென்ட் அளவு",
        "BUILDINGS":          "கட்டிடங்கள் விவரம் (இருந்தால்)",
        "TREES":              "மரங்கள் விவரம் (இருந்தால்)",
        "WATER_STRUCTURES":   "நீர் கட்டமைப்பு விவரம் (இருந்தால்)",

        # ── Boundaries ────────────────────────────────────────────────────────
        "BOUNDARY_EAST":      "கிழக்கு எல்லை",
        "BOUNDARY_WEST":      "மேற்கு எல்லை",
        "BOUNDARY_NORTH":     "வடக்கு எல்லை",
        "BOUNDARY_SOUTH":     "தெற்கு எல்லை",

        # ── Consideration ─────────────────────────────────────────────────────
        "TOTAL_AMOUNT":       "மொத்த விற்பனை தொகை (ரூ. எண்ணில்)",
        "AMOUNT_WORDS":       "மொத்த தொகை எழுத்தில்",
        "ADVANCE_DATE":       "முன்பணம் தேதி",
        "ADVANCE_AMOUNT":     "முன்பணம் தொகை",
        "BALANCE_AMOUNT":     "இருப்பு தொகை",
        "BALANCE_DATE":       "இருப்பு தொகை செலுத்திய தேதி",
        "PAYMENT_MODE":       "செலுத்திய விதம்",
        "TRANSACTION_NO":     "பரிவர்த்தனை எண் (NEFT/RTGS ref)",
        "TRANSACTION_DATE":   "பரிவர்த்தனை தேதி",
        "BANK_NAME":          "வங்கி பெயர்",

        # ── Prior deed ────────────────────────────────────────────────────────
        "PRIOR_DEED_DATE":    "முன்னைய கிரயம் தேதி",
        "PRIOR_REG_OFFICE":   "முன்னைய பதிவு அலுவலகம்",
        "PRIOR_DOC_NO":       "முன்னைய ஆவண எண்",
        "PRIOR_YEAR":         "முன்னைய ஆவண ஆண்டு",

        # ── Chain of title ────────────────────────────────────────────────────
        "OWNER_1":            "1வது உரிமையாளர் பெயர்",
        "DOC_NO_1":           "1வது ஆவண எண்",
        "OWNER_2":            "2வது உரிமையாளர் பெயர்",
        "DOC_NO_2":           "2வது ஆவண எண்",
        "OWNER_3":            "3வது உரிமையாளர் பெயர்",
        "DOC_NO_3":           "3வது ஆவண எண்",

        # ── Agriculture special ───────────────────────────────────────────────
        "NANJAI_PUNJAI_DETAIL":"நஞ்சை / புஞ்சை விரிவான விவரம்",
        "STANDING_CROPS":     "தற்போதுள்ள பயிர்கள் விவரம்",
        "TREES_DETAIL":       "மரங்கள் விரிவான விவரம்",
        "FARM_STRUCTURE":     "வேளாண் கட்டமைப்பு விவரம் (நீர்த்தொட்டி, ஆழ்துளை, அரண் போன்றவை)",

        # ── Documents handed over ─────────────────────────────────────────────
        "MOTHER_DEED":        "அன்னை பத்திரம் விவரம்",
        "PATTA_COPY":         "பட்டா நகல் விவரம்",
        "CHITTA_ADANGAL":     "சிட்டா / அடங்கல் விவரம்",
        "EC_COPY":            "வில்லங்கச் சான்றிதழ் நகல்",
        "FMB_SKETCH":         "FMB வரைபட விவரம்",
        "TAX_RECEIPTS":       "வரி ரசீது விவரம்",
        "ID_COPIES":          "அடையாள ஆவண நகல்கள்",
        "OTHER_DOCS":         "இதர ஆவணங்கள்",

        # ── Witnesses ─────────────────────────────────────────────────────────
        "WITNESS1_NAME":      "சாட்சி 1 பெயர்",
        "WITNESS1_ADDRESS":   "சாட்சி 1 விலாசம்",
        "WITNESS1_AADHAAR":   "சாட்சி 1 ஆதார் எண்",
        "WITNESS2_NAME":      "சாட்சி 2 பெயர்",
        "WITNESS2_ADDRESS":   "சாட்சி 2 விலாசம்",
        "WITNESS2_AADHAAR":   "சாட்சி 2 ஆதார் எண்",
    }
}
