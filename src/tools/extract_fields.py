"""
tools/extract_fields.py
=======================
Tool 3 — extract_fields

Parses a raw Tamil/English user prompt and extracts all deed field values
using regex patterns. Missing fields are set to None.

Supports an optional existing_fields dict so that values collected
across multiple conversation turns are merged without loss.

Annotation:
  readOnlyHint   = True   (pure text parsing — no I/O)
  idempotentHint = True   (same prompt + existing_fields → same result)
"""

import re
import json
from mcp.types import Tool, TextContent
from constants import CRITICAL_FIELDS

# ── Tool definition ────────────────────────────────────────────────────────────
TOOL_DEFINITION = Tool(
    name="extract_fields",
    description=(
        "[STEP 3 of 9] பயனரின் raw text-இல் இருந்து எல்லா fields-ஐயும் parse செய். "
        "NEVER manually parse fields yourself — இந்த tool மட்டும் பயன்படுத்து. "
        "முதல் call: existing_fields={} (empty). "
        "Loop iteration: existing_fields = கடைசியாக collect ஆன fields dict. "
        "MERGE RULE: existing non-null values மாற்றாதே. "
        "புதிய non-null values மட்டும் null fields-ஐ overwrite செய்யும். "
        "fields dict-ஐ எப்போதும் reset செய்யாதே. "
        "Return-இல் missing_fields list-ஐ validate_fields-க்கு pass செய்."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "Type of deed detected by detect_deed_type."
            },
            "prompt": {
                "type": "string",
                "description": "Raw user text to extract field values from."
            },
            "existing_fields": {
                "type": "object",
                "description": (
                    "Optional. Previously collected fields dict. "
                    "New non-null values from prompt are merged on top — "
                    "existing non-null values are NOT overwritten."
                ),
                "default": {}
            }
        },
        "required": ["deed_type", "prompt"]
    },
    annotations={
        "title":          "Field Extractor",
        "readOnlyHint":   True,
        "idempotentHint": True,
    }
)

# ── Regex patterns ─────────────────────────────────────────────────────────────
_PATTERNS = {
    # Parties
    "VENDOR_NAME":        [r"விற்பவர்[:\s]*([^\,\.\n]+)",    r"seller[:\s]*([^\,\.\n]+)",  r"vendor[:\s]*([^\,\.\n]+)"],
    "VENDOR_FATHER":      [r"விற்பவர்.*?தந்தை[:\s]*([^\,\.\n]+)", r"vendor.*?s/o[:\s]*([^\,\.\n]+)", r"vendor.*?father[:\s]*([^\,\.\n]+)"],
    "VENDOR_AGE":         [r"விற்பவர்.*?(\d+)\s*வயது",       r"vendor.*?age[:\s]*(\d+)",   r"seller.*?(\d+)\s*years"],
    "VENDOR_ADDRESS":     [r"விற்பவர்.*?முகவரி[:\s]*([^\n]+)", r"விற்பவர்.*?விலாசம்[:\s]*([^\n]+)"],
    "VENDOR_AADHAAR":     [r"விற்பவர்.*?ஆதார்[:\s]*([\d\- ]{12,14})", r"vendor.*?aadhaar[:\s]*([\d\- ]{12,14})"],
    "VENDOR_PAN":         [r"விற்பவர்.*?PAN[:\s]*([A-Z]{5}\d{4}[A-Z])", r"vendor.*?pan[:\s]*([A-Za-z]{5}\d{4}[A-Za-z])"],
    "PURCHASER_NAME":     [r"வாங்குபவர்[:\s]*([^\,\.\n]+)",  r"buyer[:\s]*([^\,\.\n]+)",   r"purchaser[:\s]*([^\,\.\n]+)"],
    "PURCHASER_FATHER":   [r"வாங்குபவர்.*?தந்தை[:\s]*([^\,\.\n]+)", r"buyer.*?s/o[:\s]*([^\,\.\n]+)"],
    "PURCHASER_AGE":      [r"வாங்குபவர்.*?(\d+)\s*வயது",    r"buyer.*?age[:\s]*(\d+)"],
    "PURCHASER_ADDRESS":  [r"வாங்குபவர்.*?முகவரி[:\s]*([^\n]+)", r"வாங்குபவர்.*?விலாசம்[:\s]*([^\n]+)"],
    "PURCHASER_AADHAAR":  [r"வாங்குபவர்.*?ஆதார்[:\s]*([\d\- ]{12,14})", r"buyer.*?aadhaar[:\s]*([\d\- ]{12,14})"],
    "PURCHASER_PAN":      [r"வாங்குபவர்.*?PAN[:\s]*([A-Z]{5}\d{4}[A-Z])", r"buyer.*?pan[:\s]*([A-Za-z]{5}\d{4}[A-Za-z])"],
    # Property
    "PROP_DISTRICT":      [r"மாவட்டம்[:\s]*([^\s,\.]+)",    r"district[:\s]*([^\s,\.]+)"],
    "PROP_TALUK":         [r"தாலுக்கா?[:\s]*([^\s,\.]+)",   r"taluk[:\s]*([^\s,\.]+)"],
    "PROP_VILLAGE":       [r"கிராமம்[:\s]*([^\s,\.]+)",     r"village[:\s]*([^\s,\.]+)"],
    "SURVEY_NO":          [r"survey\s*no[:\s]*([\d/]+)",     r"புல எண்[:\s]*([\d/]+)",     r"சர்வே எண்[:\s]*([\d/]+)"],
    "PATTA_NO":           [r"பட்டா எண்[:\s]*([\d]+)",       r"patta[:\s]*([\d]+)"],
    "NANJAI_OR_PUNJAI":   [r"(நஞ்சை|புஞ்சை|nanjai|punjai)", r"(நஞ்சை நிலம்|புஞ்சை நிலம்)"],
    "EXTENT_ACRE":        [r"([\d.]+)\s*ஏக்கர்",            r"([\d.]+)\s*acres?"],
    "EXTENT_SQFT":        [r"([\d,]+)\s*sq\.?\s*ft",         r"([\d,]+)\s*square\s*feet",  r"([\d,]+)\s*சதுர அடி"],
    "BOUNDARY_EAST":      [r"கிழக்கு[:\s—-]+([^\n,]+)",     r"east[:\s—-]+([^\n,]+)"],
    "BOUNDARY_WEST":      [r"மேற்கு[:\s—-]+([^\n,]+)",      r"west[:\s—-]+([^\n,]+)"],
    "BOUNDARY_NORTH":     [r"வடக்கு[:\s—-]+([^\n,]+)",      r"north[:\s—-]+([^\n,]+)"],
    "BOUNDARY_SOUTH":     [r"தெற்கு[:\s—-]+([^\n,]+)",      r"south[:\s—-]+([^\n,]+)"],
    # Consideration
    "TOTAL_AMOUNT":       [r"மொத்த விலை[:\s]*ரூ\.?\s*([\d,]+)", r"total.*?rs\.?\s*([\d,]+)", r"விலை[:\s]*ரூ\.?\s*([\d,]+)", r"₹\s*([\d,]+)"],
    "PAYMENT_MODE":       [r"(NEFT|RTGS|cheque|cash|ரொக்கம்|காசோலை)", r"payment.*?(NEFT|RTGS|cheque|cash)"],
    # Registration
    "REG_OFFICE":         [r"பதிவு அலுவலகம்[:\s]*([^\n,\.]+)", r"reg.*?office[:\s]*([^\n,\.]+)"],
    # Prior deed
    "PRIOR_DOC_NO":       [r"முன்னோர் ஆவணம்[:\s]*([\d/]+)", r"prior.*?doc.*?([\d/]+)", r"முன்னைய ஆவண எண்[:\s]*([\d/]+)"],
    # Witnesses
    "WITNESS1_NAME":      [r"சாட்சி\s*1[:\s]*([^\n,]+)",   r"witness\s*1[:\s]*([^\n,]+)"],
    "WITNESS1_ADDRESS":   [r"சாட்சி\s*1.*?விலாசம்[:\s]*([^\n]+)"],
    "WITNESS2_NAME":      [r"சாட்சி\s*2[:\s]*([^\n,]+)",   r"witness\s*2[:\s]*([^\n,]+)"],
    "WITNESS2_ADDRESS":   [r"சாட்சி\s*2.*?விலாசம்[:\s]*([^\n]+)"],
    # Plot-specific
    "PROP_AREA":          [r"பகுதி[:\s]*([^\n,\.]+)", r"area[:\s]*([^\n,\.]+(?:நகர்|nagar|street|தெரு))"],
    "DOOR_NO":            [r"கதவு எண்[:\s]*([\w/]+)",       r"door\s*no[:\s]*([\w/]+)"],
    "WARD_NO":            [r"வார்டு[:\s]*([\d]+)",           r"ward\s*no[:\s]*([\d]+)"],
    "PLOT_NO":            [r"plot\s*no[:\s]*([\d]+)",         r"மனை எண்[:\s]*([\d]+)"],
}


# ── Normalisation helpers ──────────────────────────────────────────────────────
def _normalise_aadhaar(val: str) -> str:
    """Strip dashes/spaces, return 12-digit string or original if invalid."""
    digits = re.sub(r"[^0-9]", "", val)
    return digits if len(digits) == 12 else val

def _normalise_amount(val: str) -> str:
    """Remove commas and spaces from amount strings."""
    return re.sub(r"[,\s]", "", val)


# ── Core extraction function (also used by test suite directly) ────────────────
def extract_from_prompt(deed_type: str, prompt: str) -> dict:
    """
    Parse prompt and return a flat dict {field_key: value | None}.
    All CRITICAL_FIELDS keys for the deed_type are guaranteed to be present.
    """
    fields: dict = {}

    for field_key, patterns in _PATTERNS.items():
        for pattern in patterns:
            m = re.search(pattern, prompt, re.IGNORECASE)
            if m:
                value = m.group(1).strip() if m.lastindex else m.group(0).strip()

                if "AADHAAR" in field_key:
                    value = _normalise_aadhaar(value)
                elif field_key == "TOTAL_AMOUNT":
                    value = _normalise_amount(value)
                elif field_key == "NANJAI_OR_PUNJAI":
                    value = m.group(0).strip()

                fields[field_key] = value
                break

    # Date — DD/MM/YYYY or DD.MM.YYYY
    date_m = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", prompt)
    if date_m:
        fields.setdefault("DATE_DAY",   date_m.group(1))
        fields.setdefault("DATE_MONTH", date_m.group(2))
        fields.setdefault("DATE_YEAR",  date_m.group(3))

    # Ensure all critical keys are present (None if not found)
    for key in CRITICAL_FIELDS.get(deed_type, {}):
        fields.setdefault(key, None)

    return fields


# ── Handler ────────────────────────────────────────────────────────────────────
async def handle(arguments: dict) -> list[TextContent]:
    deed_type       = arguments.get("deed_type", "plot")
    prompt          = arguments.get("prompt", "")
    existing_fields = arguments.get("existing_fields") or {}

    new_fields = extract_from_prompt(deed_type, prompt)

    # Merge: keep existing non-null values; overwrite only nulls with new data
    merged = dict(existing_fields)
    for key, val in new_fields.items():
        if val is not None:
            merged[key] = val
        elif key not in merged:
            merged[key] = None

    found   = [k for k, v in merged.items() if v is not None]
    missing = [k for k, v in merged.items() if v is None]

    return [TextContent(
        type="text",
        text=json.dumps({
            "fields":         merged,
            "found_count":    len(found),
            "missing_count":  len(missing),
            "found_fields":   found,
            "missing_fields": missing,
            "message": (
                f"✅ {len(found)} fields found, {len(missing)} still missing. "
                "Pass these fields to validate_fields next."
            )
        }, ensure_ascii=False, indent=2)
    )]
