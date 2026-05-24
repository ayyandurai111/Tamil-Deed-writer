"""
tools/review_draft.py
=====================
Tool 6 — review_draft  (CALL 7 of 12)

Reviews the CLEAN SKELETON (from fill_skeleton) before DOCX generation.
Input: clean_skeleton (also accepts filled_skeleton as alias) + deed_type.

4-layer review:

  L1 — Placeholder Check   : any {{TAG}} remaining in skeleton values
  L2 — Legal Checks        : Aadhaar, PAN, date validity, boundaries
  L3 — Consistency Checks  : district match, amount-words, age sanity
  L4 — Structure Check     : required sections present, witnesses complete

Returns:
  {
    "ready_for_docx" : bool,
    "critical_count" : int,
    "warning_count"  : int,
    "layers": {
      "L1_placeholders": { "passed", "errors" },
      "L2_legal":        { "passed", "errors" },
      "L3_consistency":  { "passed", "warnings" },
      "L4_structure":    { "passed", "errors" }
    },
    "summary": str
  }
"""

import re
import json
from datetime import date
from mcp.types import Tool, TextContent

# ── Tool definition ────────────────────────────────────────────────────────────
TOOL_DEFINITION = Tool(
    name="review_draft",
    description=(
        "[CALL 7 of 12] ONE TASK: இந்த tool call மட்டும் (L1+L2 programmatic check). "
        "fill_skeleton clean_skeleton result-ஐ pass செய். tool call முடிந்தவுடன் response முடிந்தது. "

        "── TOOL செய்வது (L1 + L2 + L3 + L4) ─── "
        "இந்த tool L1+L2 மட்டும் programmatic-ஆக check செய்யும். L3+L4 = அடுத்த calls-ல். "

        "── L1+L2 RESULT மட்டும் return ஆகும் ─── "
        "ready_for_docx result-ஐ வைத்துக்கொள் — CALL 10 final decision-க்கு தேவை. "
        "L3+L4 results + ready_for_docx சேர்த்து CALL 10-ல் மட்டும் decide செய். "
        ""
        ""
        ""
        ""
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "clean_skeleton": {
                "type": "object",
                "description": "The cleaned skeleton JSON from fill_skeleton (Phase 2 output)."
            },
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "Type of deed."
            }
        },
        "required": ["clean_skeleton", "deed_type"]
    },
    annotations={
        "title":          "Skeleton Reviewer",
        "readOnlyHint":   True,
        "idempotentHint": True,
    }
)


# ══════════════════════════════════════════════════════════════════════════════
#  LAYER 1 — PLACEHOLDER CHECK
#  Scans entire skeleton JSON string for any remaining {{TAG}}
# ══════════════════════════════════════════════════════════════════════════════

def _layer1_placeholders(skeleton: dict) -> dict:
    skeleton_str = json.dumps(skeleton, ensure_ascii=False)
    found  = re.findall(r"\{\{([A-Z_0-9]+)\}\}", skeleton_str)
    unique = sorted(set(found))

    errors = [
        {
            "field":    tag,
            "issue":    f"{{{{{tag}}}}} — skeleton-ல் இன்னும் நிரப்பப்படவில்லை",
            "severity": "critical"
        }
        for tag in unique
    ]
    return {"passed": len(errors) == 0, "errors": errors}


# ══════════════════════════════════════════════════════════════════════════════
#  LAYER 2 — LEGAL CHECKS
# ══════════════════════════════════════════════════════════════════════════════

def _check_aadhaar(val, label: str):
    if not val or str(val).startswith("{{"):
        return None
    # Skip blank placeholder values like "___________" from unfilled templates
    if re.match(r'^[_\s]+$', str(val).strip()):
        return None
    digits = re.sub(r"[^0-9]", "", str(val))
    if len(digits) != 12:
        return {
            "field":    label,
            "issue":    f"{label}: ஆதார் {len(digits)} இலக்கம் — 12 கட்டாயம்",
            "severity": "critical"
        }
    return None


def _check_pan(val, label: str):
    if not val or str(val) in ("___", "—") or str(val).startswith("{{"):
        return None
    if not re.search(r"[A-Z]{5}[0-9]{4}[A-Z]", str(val).upper()):
        return {
            "field":    label,
            "issue":    f"{label}: PAN format தவறு — ABCDE1234F format வேண்டும்",
            "severity": "critical"
        }
    return None


def _check_date(day, month, year) -> dict | None:
    from constants import TAMIL_MONTHS
    _TAMIL_TO_NUM = {v: k for k, v in TAMIL_MONTHS.items()}
    month_num = int(month) if str(month).isdigit() else _TAMIL_TO_NUM.get(str(month).strip())
    try:
        if not month_num:
            raise ValueError(f"Unknown month: {month}")
        d = date(int(year), month_num, int(day))
        if d > date.today():
            return {
                "field":    "DATE",
                "issue":    f"பத்திர தேதி {d} எதிர்காலத்தில் உள்ளது",
                "severity": "warning"
            }
    except (ValueError, TypeError):
        return {
            "field":    "DATE",
            "issue":    f"தேதி தவறானது: {day}/{month}/{year}",
            "severity": "critical"
        }
    return None


def _layer2_legal(skeleton: dict, deed_type: str) -> dict:
    errors = []
    v   = skeleton.get("vendor",        {}) or {}
    p   = skeleton.get("purchaser",     {}) or {}
    hdr = skeleton.get("header",        {}) or {}
    con = skeleton.get("consideration", {}) or {}

    # Aadhaar
    for err in [
        _check_aadhaar(v.get("aadhaar"), "விற்பவர் ஆதார்"),
        _check_aadhaar(p.get("aadhaar"), "வாங்குபவர் ஆதார்"),
    ]:
        if err:
            errors.append(err)

    # PAN — only if values are present (PAN requirement already enforced by validate_fields)
    for err in [
        _check_pan(v.get("pan"), "விற்பவர் PAN"),
        _check_pan(p.get("pan"), "வாங்குபவர் PAN"),
    ]:
        if err:
            errors.append(err)

    # Amount > 0
    amt_str = str(con.get("total_amount", "") or "").replace(",", "").strip()
    if amt_str and amt_str.isdigit() and int(amt_str) <= 0:
        errors.append({
            "field":    "TOTAL_AMOUNT",
            "issue":    "மொத்த விலை பூஜ்யம் அல்லது தவறான தொகை",
            "severity": "critical"
        })

    # Date
    err = _check_date(
        hdr.get("date_day", ""),
        hdr.get("date_month", ""),
        hdr.get("date_year", "")
    )
    if err:
        errors.append(err)

    # 4 boundaries mandatory for agriculture
    if deed_type == "agriculture":
        prop = skeleton.get("property", {}) or {}
        for key, label in [
            ("boundary_east",  "கிழக்கு எல்லை"),
            ("boundary_west",  "மேற்கு எல்லை"),
            ("boundary_north", "வடக்கு எல்லை"),
            ("boundary_south", "தெற்கு எல்லை"),
        ]:
            if not prop.get(key):
                errors.append({
                    "field":    key.upper(),
                    "issue":    f"{label} இல்லை — Registration Act S.21 கட்டாயம்",
                    "severity": "critical"
                })

    return {"passed": all(e["severity"] != "critical" for e in errors), "errors": errors}


# ══════════════════════════════════════════════════════════════════════════════
#  LAYER 3 — CONSISTENCY CHECKS
# ══════════════════════════════════════════════════════════════════════════════

def _layer3_consistency(skeleton: dict, deed_type: str) -> dict:
    warnings = []
    hdr  = skeleton.get("header",        {}) or {}
    v    = skeleton.get("vendor",        {}) or {}
    p    = skeleton.get("purchaser",     {}) or {}
    prop = skeleton.get("property",      {}) or {}
    con  = skeleton.get("consideration", {}) or {}

    # District: header vs property
    hdr_d  = str(hdr.get("district",  "") or "").strip().lower()
    prop_d = str(prop.get("district", "") or "").strip().lower()
    if hdr_d and prop_d and hdr_d != prop_d:
        warnings.append({
            "field": "DISTRICT",
            "issue": f"மாவட்டம் பொருந்தவில்லை — Header: '{hdr.get('district')}', Property: '{prop.get('district')}'",
            "severity": "warning"
        })

    # Amount vs words
    amt_str   = str(con.get("total_amount",  "") or "").replace(",", "").strip()
    words_str = str(con.get("amount_in_words", con.get("amount_words", "")) or "").strip()
    if amt_str.isdigit() and words_str:
        amt = int(amt_str)
        if amt >= 10_000_000 and "கோடி" not in words_str:
            warnings.append({
                "field": "AMOUNT_WORDS",
                "issue": f"₹{amt:,} — 'கோடி' எழுத்தில் இல்லை",
                "severity": "warning"
            })
        elif amt >= 100_000 and "லட்சம்" not in words_str and "கோடி" not in words_str:
            warnings.append({
                "field": "AMOUNT_WORDS",
                "issue": f"₹{amt:,} — 'லட்சம்' எழுத்தில் இல்லை",
                "severity": "warning"
            })

    # Age sanity
    for label, party in [("விற்பவர்", v), ("வாங்குபவர்", p)]:
        age_str = str(party.get("age", "") or "").strip()
        if age_str.isdigit():
            age = int(age_str)
            if age < 18:
                warnings.append({
                    "field":    f"{label}_AGE",
                    "issue":    f"{label} வயது {age} — 18 கீழ், சட்டப்படி செல்லாது",
                    "severity": "critical"
                })
            elif age > 100:
                warnings.append({
                    "field":    f"{label}_AGE",
                    "issue":    f"{label} வயது {age} — சரிபார்க்கவும்",
                    "severity": "warning"
                })

    return {"passed": all(w["severity"] != "critical" for w in warnings), "warnings": warnings}


# ══════════════════════════════════════════════════════════════════════════════
#  LAYER 4 — STRUCTURE CHECK
#  Verifies required skeleton sections are present and non-empty
# ══════════════════════════════════════════════════════════════════════════════

def _layer4_structure(skeleton: dict, deed_type: str) -> dict:
    errors = []

    def _present(val) -> bool:
        if val is None:
            return False
        if isinstance(val, str):
            return val.strip() != ""
        if isinstance(val, dict):
            return bool(val)
        if isinstance(val, list):
            return len(val) > 0
        return True

    # Required top-level sections
    required_sections = [
        ("title",          "title"),
        ("section_4_text", "Section 4 — விற்பவர் உரிமை அறிவிப்பு"),
        ("section_8_text", "Section 8 — ஆட்சி ஒப்படைப்பு"),
        ("closing_text",   "Closing text"),
        ("disclaimer",     "Disclaimer"),
    ]
    for key, label in required_sections:
        if not _present(skeleton.get(key)):
            errors.append({
                "field":    key.upper(),
                "issue":    f"{label} skeleton-ல் இல்லை",
                "severity": "critical"
            })

    # Witnesses — both must have name
    witnesses = skeleton.get("witnesses", []) or []
    for i, w in enumerate(witnesses[:2], start=1):
        if not _present((w or {}).get("name")):
            errors.append({
                "field":    f"WITNESS{i}_NAME",
                "issue":    f"சாட்சி {i} பெயர் இல்லை",
                "severity": "critical"
            })

    # Chain of title — at least 1 entry for agriculture
    if deed_type == "agriculture":
        chain = skeleton.get("chain_of_title", []) or []
        if not chain:
            errors.append({
                "field":    "CHAIN_OF_TITLE",
                "issue":    "முந்தைய உரிமைத் தொடர் இல்லை — குறைந்தது 1 உரிமையாளர் தேவை",
                "severity": "critical"
            })

    return {"passed": len(errors) == 0, "errors": errors}


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle(arguments: dict) -> list[TextContent]:
    # Accept both "clean_skeleton" (new API) and "filled_skeleton" (old API / backward compat)
    skeleton  = arguments.get("clean_skeleton") or arguments.get("filled_skeleton", {})
    deed_type = arguments.get("deed_type", "agriculture")

    l1 = _layer1_placeholders(skeleton)
    l2 = _layer2_legal(skeleton, deed_type)
    l3 = _layer3_consistency(skeleton, deed_type)
    l4 = _layer4_structure(skeleton, deed_type)

    critical_errors = (
        [e for e in l1["errors"]   if e["severity"] == "critical"] +
        [e for e in l2["errors"]   if e["severity"] == "critical"] +
        [w for w in l3["warnings"] if w["severity"] == "critical"] +
        [e for e in l4["errors"]   if e["severity"] == "critical"]
    )
    warnings = (
        [e for e in l2["errors"]   if e["severity"] == "warning"] +
        [w for w in l3["warnings"] if w["severity"] == "warning"]
    )

    critical_count = len(critical_errors)
    warning_count  = len(warnings)
    ready_for_docx = critical_count == 0

    if ready_for_docx and warning_count == 0:
        summary = "✅ எல்லா layers pass — generate_docx செல்."
    elif ready_for_docx and warning_count > 0:
        summary = f"⚠️ {warning_count} எச்சரிக்கைகள் — பயனரிடம் காட்டி confirm கேள், பிறகு generate_docx."
    else:
        summary = f"❌ {critical_count} critical தவறுகள் — திருத்தியபின் மட்டுமே தொடரவும்."

    return [TextContent(
        type="text",
        text=json.dumps({
            "ready_for_docx": ready_for_docx,
            "critical_count": critical_count,
            "warning_count":  warning_count,
            "summary":        summary,
            "layers": {
                "L1_placeholders": l1,
                "L2_legal":        l2,
                "L3_consistency":  l3,
                "L4_structure":    l4,
            }
        }, ensure_ascii=False, indent=2)
    )]
