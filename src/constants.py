"""
constants.py
============
Shared constants: file paths, legal field definitions, PAN threshold.

LAW SOURCES:
  1. Registration Act 1908 — S.17 (compulsory registration), S.21 (property
     description), S.32A (biometric identity of parties)
  2. Transfer of Property Act 1882 — S.54 (sale consideration must be stated)
  3. Income Tax Act 1961 — Rule 114B (PAN if > ₹10L), S.194-IA (TDS if > ₹50L)
  4. TNREGINET — Aadhaar mandatory for biometric verification at SRO
  5. TN Land Reforms Act 1961 — extent & land nature for ceiling compliance
  6. Stamp Act 1899 / TN Stamp Act — stamp value & consideration required
"""

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent.parent          # tamil-deed-mcp/
TEMPLATES_DIR = BASE_DIR / "templates"

# OUTPUT_DIR: use env var on Render (ephemeral /tmp), fall back to local output/
_output_env = os.environ.get("OUTPUT_DIR", "")
OUTPUT_DIR  = Path(_output_env) if _output_env else BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── PAN / TDS thresholds (Income Tax Act) ─────────────────────────────────────
PAN_THRESHOLD = 1_000_000    # ₹10 lakh  — Rule 114B
TDS_THRESHOLD = 5_000_000    # ₹50 lakh  — S.194-IA

# ── Critical fields per deed type ─────────────────────────────────────────────
# CRITICAL = deed REJECTED or LEGALLY VOID without these fields
CRITICAL_FIELDS = {

    "agriculture": {
        # ── Parties (Registration Act S.17, S.32A; TNREGINET biometric) ──────
        "VENDOR_NAME":      "விற்பவர் பெயர் (Registration Act S.17 — கட்டாயம்)",
        "VENDOR_FATHER":    "விற்பவர் தந்தை/கணவர் பெயர் (Registration Act S.21)",
        "VENDOR_AGE":       "விற்பவர் வயது (Registration Act S.17)",
        "VENDOR_ADDRESS":   "விற்பவர் முழு விலாசம் (Registration Act S.21)",
        "VENDOR_AADHAAR":   "விற்பவர் ஆதார் எண் (TNREGINET — biometric கட்டாயம்)",

        "PURCHASER_NAME":   "வாங்குபவர் பெயர் (Registration Act S.17 — கட்டாயம்)",
        "PURCHASER_FATHER": "வாங்குபவர் தந்தை/கணவர் பெயர் (Registration Act S.21)",
        "PURCHASER_AGE":    "வாங்குபவர் வயது (Registration Act S.17)",
        "PURCHASER_ADDRESS":"வாங்குபவர் முழு விலாசம் (Registration Act S.21)",
        "PURCHASER_AADHAAR":"வாங்குபவர் ஆதார் எண் (TNREGINET — biometric கட்டாயம்)",

        # ── Property (Registration Act S.21 — must identify property) ────────
        "PROP_DISTRICT":    "சொத்து மாவட்டம் (Registration Act S.21)",
        "PROP_TALUK":       "சொத்து தாலுக்கா (Registration Act S.21)",
        "PROP_VILLAGE":     "சொத்து கிராமம் (Registration Act S.21)",
        "SURVEY_NO":        "சர்வே / புல எண் (Registration Act S.21 — கட்டாயம்)",
        "PATTA_NO":         "பட்டா எண் (TN Revenue Records — சொத்து உரிமை ஆதாரம்)",
        "NANJAI_OR_PUNJAI": "நஞ்சை / புஞ்சை (TN Land Reforms Act 1961 — ceiling கணக்கீடு)",
        "EXTENT_ACRE":      "ஏக்கர் அளவு (TN Land Reforms Act S.5)",
        "BOUNDARY_EAST":    "கிழக்கு எல்லை (Registration Act S.21)",
        "BOUNDARY_WEST":    "மேற்கு எல்லை (Registration Act S.21)",
        "BOUNDARY_NORTH":   "வடக்கு எல்லை (Registration Act S.21)",
        "BOUNDARY_SOUTH":   "தெற்கு எல்லை (Registration Act S.21)",

        # ── Consideration (Transfer of Property Act S.54; Stamp Act) ─────────
        "TOTAL_AMOUNT":     "மொத்த விற்பனை தொகை (Transfer of Property Act S.54 — கட்டாயம்)",
        "AMOUNT_WORDS":     "தொகை எழுத்தில் (Stamp Act — stamp duty கணக்கீடு)",
        "PAYMENT_MODE":     "செலுத்திய விதம் (IT Act S.269SS — ரொக்கம் ₹20k+ தடை)",

        # ── Registration details ───────────────────────────────────────────────
        "DATE_DAY":         "பத்திர தேதி — நாள் (Registration Act S.23)",
        "DATE_MONTH":       "பத்திர தேதி — மாதம் (Registration Act S.23)",
        "DATE_YEAR":        "பத்திர தேதி — ஆண்டு (Registration Act S.23)",
        "REG_OFFICE":       "பதிவு அலுவலகம் (Registration Act S.28 — jurisdiction)",
        "DISTRICT":         "ஜில்லா (Registration Act S.28)",

        # ── Prior deed (Transfer of Property Act — title chain) ───────────────
        "PRIOR_DOC_NO":     "முன்னைய ஆவண எண் (Transfer of Property Act — title chain)",
        "PRIOR_REG_OFFICE": "முன்னைய பதிவக அலுவலகம் (chain of title — கட்டாயம்)",

        # ── Witnesses (Registration Act S.17 — 2 witnesses mandatory) ─────────
        "WITNESS1_NAME":    "சாட்சி 1 பெயர் (Registration Act S.17 — 2 சாட்சிகள் கட்டாயம்)",
        "WITNESS1_ADDRESS": "சாட்சி 1 விலாசம் (Registration Act S.17)",
        "WITNESS2_NAME":    "சாட்சி 2 பெயர் (Registration Act S.17 — 2 சாட்சிகள் கட்டாயம்)",
        "WITNESS2_ADDRESS": "சாட்சி 2 விலாசம் (Registration Act S.17)",
    },

    "plot": {
        # ── Parties ───────────────────────────────────────────────────────────
        "VENDOR_NAME":      "விற்பவர் பெயர் (Registration Act S.17 — கட்டாயம்)",
        "VENDOR_FATHER":    "விற்பவர் தந்தை/கணவர் பெயர் (Registration Act S.21)",
        "VENDOR_AGE":       "விற்பவர் வயது (Registration Act S.17)",
        "VENDOR_ADDRESS":   "விற்பவர் முழு விலாசம் (Registration Act S.21)",
        "VENDOR_ID":        "விற்பவர் ஆதார்/PAN எண் (TNREGINET — biometric கட்டாயம்)",

        "PURCHASER_NAME":   "வாங்குபவர் பெயர் (Registration Act S.17 — கட்டாயம்)",
        "PURCHASER_FATHER": "வாங்குபவர் தந்தை/கணவர் பெயர் (Registration Act S.21)",
        "PURCHASER_AGE":    "வாங்குபவர் வயது (Registration Act S.17)",
        "PURCHASER_ADDRESS":"வாங்குபவர் முழு விலாசம் (Registration Act S.21)",
        "PURCHASER_ID":     "வாங்குபவர் ஆதார்/PAN எண் (TNREGINET — biometric கட்டாயம்)",

        # ── Property ──────────────────────────────────────────────────────────
        "PROP_DISTRICT":    "சொத்து மாவட்டம் (Registration Act S.21)",
        "PROP_AREA":        "சொத்து பகுதி / ஊர் (Registration Act S.21)",
        "EXTENT_SQFT":      "மொத்த பரப்பு Sq.ft (Registration Act S.21 — அளவு கட்டாயம்)",
        "BOUNDARY_EAST":    "கிழக்கு எல்லை (Registration Act S.21 — கட்டாயம்)",
        "BOUNDARY_WEST":    "மேற்கு எல்லை (Registration Act S.21 — கட்டாயம்)",
        "BOUNDARY_NORTH":   "வடக்கு எல்லை (Registration Act S.21 — கட்டாயம்)",
        "BOUNDARY_SOUTH":   "தெற்கு எல்லை (Registration Act S.21 — கட்டாயம்)",

        # ── Consideration ─────────────────────────────────────────────────────
        "TOTAL_AMOUNT":     "மொத்த விற்பனை தொகை (Transfer of Property Act S.54 — கட்டாயம்)",
        "AMOUNT_WORDS":     "தொகை எழுத்தில் (Stamp Act — stamp duty கணக்கீடு)",
        "RECEIVED_AMOUNT":  "பெறப்பட்ட தொகை (Transfer of Property Act S.54)",
        "RECEIVED_WORDS":   "பெறப்பட்ட தொகை எழுத்தில் (Stamp Act)",
        "PAYMENT_MODE":     "செலுத்திய விதம் (IT Act S.269SS — ரொக்கம் ₹20k+ தடை)",

        # ── Registration ──────────────────────────────────────────────────────
        "DATE_DAY":         "பத்திர தேதி — நாள் (Registration Act S.23)",
        "DATE_MONTH":       "பத்திர தேதி — மாதம் (Registration Act S.23)",
        "DATE_YEAR":        "பத்திர தேதி — ஆண்டு (Registration Act S.23)",

        # ── Prior deed ────────────────────────────────────────────────────────
        "PRIOR_DOC_NO":     "முன்னைய ஆவண எண் (Transfer of Property Act — title chain)",
        "PRIOR_REG_OFFICE": "முன்னைய பதிவக அலுவலகம் (chain of title — கட்டாயம்)",

        # ── Witnesses ─────────────────────────────────────────────────────────
        "WITNESS1_NAME":    "சாட்சி 1 பெயர் (Registration Act S.17 — 2 சாட்சிகள் கட்டாயம்)",
        "WITNESS1_ADDRESS": "சாட்சி 1 விலாசம் (Registration Act S.17)",
        "WITNESS2_NAME":    "சாட்சி 2 பெயர் (Registration Act S.17 — 2 சாட்சிகள் கட்டாயம்)",
        "WITNESS2_ADDRESS": "சாட்சி 2 விலாசம் (Registration Act S.17)",
    }
}
