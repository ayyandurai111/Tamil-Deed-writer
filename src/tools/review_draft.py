"""
tools/review_draft.py
=====================
Tool 7 — review_draft

3-layer review of the Tamil deed draft before DOCX generation.

  Layer 1 — Missing Placeholders  : finds any {{TAG}} still in draft
  Layer 2 — Legal Checks          : Aadhaar digits, PAN format, date, boundaries
  Layer 3 — Consistency           : district match, age sanity, amount vs words

No external API calls. Claude (the orchestrating AI) reads the summary
and can provide additional feedback to the user directly.

Returns:
  {
    "has_errors":     bool,
    "ready_for_docx": bool,     ← True only when no critical errors
    "layers": {
      "placeholders": { "passed", "errors" },
      "legal":        { "passed", "errors" },
      "consistency":  { "passed", "warnings" }
    },
    "critical_count": int,
    "warning_count":  int,
    "summary":        str   (Tamil summary for Claude to show user)
  }

Annotation:
  readOnlyHint   = True
  idempotentHint = True
"""

import re
import json
from datetime import date
from mcp.types import Tool, TextContent

# ── Tool definition ────────────────────────────────────────────────────────────
TOOL_DEFINITION = Tool(
    name="review_draft",
    description=(
        "[STEP 7 of 9] Draft-ஐ 2 layers-இல் சரிபார். "

        "L1 Placeholders: {{TAG}} unfilled இருக்கிறதா. "
        "L2 Legal: Aadhaar 12 digits, PAN format, Date valid, 4 boundaries உள்ளனவா. "

        "Tool return ஆன பிறகு — YOU (Claude) Layer 3 செய்: "
        "draft_text-ஐ படித்து கீழ்கண்டவற்றை சரிபார்: "
        "(a) விற்பவர் prefix (திரு/திருமதி) gender-உடன் பொருந்துகிறதா? "
        "(b) 4 எல்லைகளும் வெவ்வேறு விவரம் உள்ளனவா (நான்கும் ஒரே விஷயமா)? "
        "(c) AMOUNT_WORDS எண்ணுடன் பொருந்துகிறதா? "
        "(d) Party பெயர்கள் draft முழுவதும் consistent-ஆக உள்ளனவா? "
        "(e) ஏதேனும் Tamil grammar பிழை தெரிகிறதா? "
        "Claude issues காண்பித்தால் பயனரிடம் confirm கேள். "

        "ready_for_docx=True + no L3 issues → generate_docx செல். "
        "ready_for_docx=True + L3 issues → பயனரிடம் காட்டி confirm கேள், பிறகு generate_docx. "
        "ready_for_docx=False → ❌ Critical errors காட்டு, திருத்தம் கேள். "
        "fill_skeleton → generate_draft → review_draft LOOP. "
        "❌ ready_for_docx=False-ஆக இருந்தால் generate_docx call செய்யாதே."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "draft_text": {
                "type": "string",
                "description": "The plain-text draft returned by generate_draft."
            },
            "filled_skeleton": {
                "type": "object",
                "description": "The filled skeleton JSON — used for structured field checks."
            },
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "Type of deed."
            }
        },
        "required": ["draft_text", "filled_skeleton", "deed_type"]
    },
    annotations={
        "title":          "Draft Reviewer",
        "readOnlyHint":   True,
        "idempotentHint": True,
    }
)


# ══════════════════════════════════════════════════════════════════════════════
#  LAYER 1 — MISSING PLACEHOLDERS
# ══════════════════════════════════════════════════════════════════════════════

def _layer1_placeholders(draft_text: str) -> dict:
    """Find any {{PLACEHOLDER}} tags still present in the draft."""
    found  = re.findall(r"\{\{([A-Z_]+)\}\}", draft_text)
    unique = sorted(set(found))

    errors = [
        {
            "field":    tag,
            "issue":    f"{{{{{tag}}}}} — இன்னும் நிரப்பப்படவில்லை",
            "severity": "critical"
        }
        for tag in unique
    ]

    return {
        "passed": len(errors) == 0,
        "errors": errors
    }


# ══════════════════════════════════════════════════════════════════════════════
#  LAYER 2 — LEGAL CHECKS
# ══════════════════════════════════════════════════════════════════════════════

def _check_aadhaar(val: str, label: str) -> dict | None:
    if not val or val == "___":
        return None   # already caught by layer 1
    digits = re.sub(r"[^0-9]", "", str(val))
    if len(digits) != 12:
        return {
            "field":    label,
            "issue":    f"{label}: ஆதார் எண் {len(digits)} இலக்கம் உள்ளது — 12 இலக்கம் கட்டாயம்",
            "severity": "critical"
        }
    return None


def _check_pan(val: str, label: str) -> dict | None:
    if not val or val in ("___", "பொருந்தாது", "—") or str(val).startswith("{{"):
        return None
    if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", str(val).strip().upper()):
        return {
            "field":    label,
            "issue":    f"{label}: PAN format தவறு — 5 எழுத்து + 4 எண் + 1 எழுத்து (ABCDE1234F)",
            "severity": "critical"
        }
    return None


def _check_amount(val: str) -> dict | None:
    if not val or val == "___":
        return None
    digits = re.sub(r"[^0-9]", "", str(val))
    if not digits or int(digits) <= 0:
        return {
            "field":    "TOTAL_AMOUNT",
            "issue":    "மொத்த விலை பூஜ்யம் அல்லது தவறான தொகை",
            "severity": "critical"
        }
    return None


def _check_date(day: str, month: str, year: str) -> dict | None:
    try:
        d     = date(int(year), int(month), int(day))
        today = date.today()
        if d > today:
            return {
                "field":    "DATE",
                "issue":    f"பத்திர தேதி {d} இன்றைய தேதியை விட எதிர்காலத்தில் உள்ளது",
                "severity": "warning"
            }
    except (ValueError, TypeError):
        return {
            "field":    "DATE",
            "issue":    f"தேதி தவறானது: {day}/{month}/{year}",
            "severity": "critical"
        }
    return None


def _layer2_legal(filled: dict, deed_type: str) -> dict:
    errors = []

    v   = filled.get("vendor", {})
    p   = filled.get("purchaser", {})
    hdr = filled.get("header", {})
    con = filled.get("consideration", {})

    # Aadhaar
    if deed_type == "agriculture":
        for err in [
            _check_aadhaar(v.get("aadhaar"), "விற்பவர் ஆதார்"),
            _check_aadhaar(p.get("aadhaar"), "வாங்குபவர் ஆதார்"),
        ]:
            if err:
                errors.append(err)
    else:
        # Plot deed: Aadhaar embedded in id_card field
        for party_label, party in [("விற்பவர்", v), ("வாங்குபவர்", p)]:
            id_val = str(party.get("id_card", "") or "")
            digits = re.sub(r"[^0-9]", "", id_val)
            # Look for 12 consecutive digits in the combined ID string
            found_12 = re.search(r"\d{12}", id_val.replace(" ", ""))
            if not found_12 and len(digits) < 12:
                errors.append({
                    "field":    f"{party_label}_ID",
                    "issue":    f"{party_label} அடையாள அட்டையில் 12 இலக்க ஆதார் எண் இல்லை",
                    "severity": "critical"
                })

    # PAN
    for err in [
        _check_pan(v.get("pan"), "விற்பவர் PAN"),
        _check_pan(p.get("pan"), "வாங்குபவர் PAN"),
    ]:
        if err:
            errors.append(err)

    # Amount
    err = _check_amount(con.get("total_amount"))
    if err:
        errors.append(err)

    # Date
    err = _check_date(
        hdr.get("date_day", ""),
        hdr.get("date_month", ""),
        hdr.get("date_year", "")
    )
    if err:
        errors.append(err)

    # Boundaries — all 4 mandatory for agriculture
    if deed_type == "agriculture":
        prop = filled.get("property", {})
        for boundary, label in [
            ("boundary_east",  "கிழக்கு எல்லை"),
            ("boundary_west",  "மேற்கு எல்லை"),
            ("boundary_north", "வடக்கு எல்லை"),
            ("boundary_south", "தெற்கு எல்லை"),
        ]:
            val = prop.get(boundary, "")
            if not val or val == "___" or re.search(r"\{\{", str(val)):
                errors.append({
                    "field":    boundary.upper(),
                    "issue":    f"{label} — நிரப்பப்படவில்லை (Registration Act S.21 — கட்டாயம்)",
                    "severity": "critical"
                })

    return {
        "passed": all(e["severity"] != "critical" for e in errors),
        "errors": errors
    }


# ══════════════════════════════════════════════════════════════════════════════
#  LAYER 3 — CONSISTENCY CHECKS
# ══════════════════════════════════════════════════════════════════════════════

def _layer3_consistency(filled: dict, deed_type: str) -> dict:
    warnings = []

    hdr  = filled.get("header", {})
    v    = filled.get("vendor", {})
    p    = filled.get("purchaser", {})
    prop = filled.get("property", {})
    con  = filled.get("consideration", {})

    # District consistency: header vs property
    hdr_district  = str(hdr.get("district", "")).strip().lower()
    prop_district = str(prop.get("district", "")).strip().lower()
    if hdr_district and prop_district and hdr_district != prop_district:
        warnings.append({
            "field":    "DISTRICT",
            "issue":    f"மாவட்டம் பொருந்தவில்லை — Header: '{hdr.get('district')}', Property: '{prop.get('district')}'",
            "severity": "warning"
        })

    # Amount vs words rough check
    amount_str = str(con.get("total_amount", "")).replace(",", "").strip()
    words_str  = str(con.get("amount_in_words", con.get("amount_words", ""))).strip()
    if amount_str.isdigit() and words_str and words_str not in ("___", ""):
        amount_int = int(amount_str)
        if amount_int >= 10_000_000 and "கோடி" not in words_str:
            warnings.append({
                "field":    "AMOUNT_WORDS",
                "issue":    f"தொகை {amount_int:,} — ₹1 கோடிக்கு மேல், ஆனால் 'கோடி' எழுத்தில் இல்லை",
                "severity": "warning"
            })
        elif amount_int >= 100_000 and "லட்சம்" not in words_str and "கோடி" not in words_str:
            warnings.append({
                "field":    "AMOUNT_WORDS",
                "issue":    f"தொகை {amount_int:,} — ₹1 லட்சத்திற்கு மேல், ஆனால் 'லட்சம்' எழுத்தில் இல்லை",
                "severity": "warning"
            })

    # Age sanity
    for party_label, party in [("விற்பவர்", v), ("வாங்குபவர்", p)]:
        age_str = str(party.get("age", "")).strip()
        if age_str.isdigit():
            age = int(age_str)
            if age < 18:
                warnings.append({
                    "field":    f"{party_label}_AGE",
                    "issue":    f"{party_label} வயது {age} — 18 வயதுக்கு கீழ் சட்டப்படி ஒப்பந்தம் செல்லாது",
                    "severity": "critical"
                })
            elif age > 100:
                warnings.append({
                    "field":    f"{party_label}_AGE",
                    "issue":    f"{party_label} வயது {age} — சரிபார்க்கவும்",
                    "severity": "warning"
                })

    return {
        "passed":   all(w["severity"] != "critical" for w in warnings),
        "warnings": warnings
    }


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle(arguments: dict) -> list[TextContent]:
    draft_text = arguments.get("draft_text", "")
    filled     = arguments.get("filled_skeleton", {})
    deed_type  = arguments.get("deed_type", "plot")

    l1 = _layer1_placeholders(draft_text)
    l2 = _layer2_legal(filled, deed_type)

    critical_errors = (
        [e for e in l1["errors"] if e["severity"] == "critical"] +
        [e for e in l2["errors"] if e["severity"] == "critical"]
    )
    warnings = (
        [e for e in l2["errors"] if e["severity"] == "warning"]
    )

    critical_count = len(critical_errors)
    warning_count  = len(warnings)
    ready_for_docx = critical_count == 0

    if ready_for_docx and warning_count == 0:
        summary = "✅ L1+L2 சரிபார்ப்பு நிறைவு — Claude L3 consistency சரிபார்க்கும்."
    elif ready_for_docx and warning_count > 0:
        summary = (
            f"⚠️  {warning_count} எச்சரிக்கைகள் — Claude L3 சரிபார்த்து பயனரிடம் காட்டும்."
        )
    else:
        summary = (
            f"❌ {critical_count} critical தவறுகள் — திருத்தியபின் மட்டுமே தொடரவும்."
        )

    return [TextContent(
        type="text",
        text=json.dumps({
            "has_errors":     critical_count > 0 or warning_count > 0,
            "ready_for_docx": ready_for_docx,
            "critical_count": critical_count,
            "warning_count":  warning_count,
            "summary":        summary,
            "layers": {
                "L1_placeholders": l1,
                "L2_legal":        l2,
                "L3_consistency":  "Claude performs this check after tool returns"
            }
        }, ensure_ascii=False, indent=2)
    )]
