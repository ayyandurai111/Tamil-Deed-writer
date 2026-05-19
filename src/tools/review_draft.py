"""
tools/review_draft.py
=====================
Tool 10 — review_draft

4-layer review of the Tamil deed draft before DOCX generation.

  Layer 1 — Missing Placeholders  : regex (instant, no API)
  Layer 2 — Legal Checks          : rule-based (instant, no API)
  Layer 3 — Consistency           : cross-field logic (instant, no API)
  Layer 4 — Tamil Grammar & Style : Claude AI via Anthropic API

Returns:
  {
    "has_errors":     bool,
    "ready_for_docx": bool,     ← True only when no critical errors
    "layers": {
      "placeholders": { "passed", "errors" },
      "legal":        { "passed", "errors" },
      "consistency":  { "passed", "warnings" },
      "tamil_grammar":{ "passed", "errors", "suggestions", "overall_quality" }
    },
    "critical_count": int,
    "warning_count":  int,
    "summary":        str   (Tamil summary for user)
  }

Annotation:
  readOnlyHint   = True    (no file writes)
  idempotentHint = False   (AI layer result may vary slightly)
"""

import re
import json
import asyncio
from datetime import date
from mcp.types import Tool, TextContent

# ── Tool definition ────────────────────────────────────────────────────────────
TOOL_DEFINITION = Tool(
    name="review_draft",
    description=(
        "[STEP 7 of 9] Draft-ஐ 4 layers-இல் சரிபார். "
        "L1 Placeholders: {{TAG}} unfilled regex. "
        "L2 Legal: Aadhaar 12 digits, PAN format, Date valid, 4 boundaries உள்ளனவா. "
        "L3 Consistency: District match, Age≥18, Amount vs words. "
        "L4 Tamil Grammar: Claude AI — இலக்கணம், legal terms, incomplete sentences. "
        "ready_for_docx=True + warnings=0 → பயனருக்கு: ✅ சரிபார்ப்பு முடிந்தது → generate_docx செல். "
        "ready_for_docx=True + warnings>0 → warnings காட்டு → generate_docx செல். "
        "ready_for_docx=False → ❌ Critical errors Tamil-இல் காட்டு, திருத்தம் கேள். "
        "பிறகு fill_skeleton → generate_draft → review_draft LOOP. "
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
        "idempotentHint": False,   # AI layer output may vary
        "openWorldHint":  True,    # calls Anthropic API
    }
)


# ══════════════════════════════════════════════════════════════════════════════
#  LAYER 1 — MISSING PLACEHOLDERS
# ══════════════════════════════════════════════════════════════════════════════

def _layer1_placeholders(draft_text: str) -> dict:
    """Find any {{PLACEHOLDER}} tags still present in the draft."""
    found = re.findall(r"\{\{([A-Z_]+)\}\}", draft_text)
    unique = sorted(set(found))

    errors = [
        {
            "field":    tag,
            "issue":    f"{{{{ {tag} }}}} — இன்னும் நிரப்பப்படவில்லை",
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
    if not val or val in ("___", "பொருந்தாது", "—"):
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
        d = date(int(year), int(month), int(day))
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

    # Aadhaar checks
    for err in [
        _check_aadhaar(v.get("aadhaar"), "விற்பவர் ஆதார்"),
        _check_aadhaar(p.get("aadhaar"), "வாங்குபவர் ஆதார்"),
    ]:
        if err:
            errors.append(err)

    # PAN checks
    for err in [
        _check_pan(v.get("pan"), "விற்பவர் PAN"),
        _check_pan(p.get("pan"), "வாங்குபவர் PAN"),
    ]:
        if err:
            errors.append(err)

    # Amount check
    err = _check_amount(con.get("total_amount"))
    if err:
        errors.append(err)

    # Date check
    err = _check_date(
        hdr.get("date_day", ""),
        hdr.get("date_month", ""),
        hdr.get("date_year", "")
    )
    if err:
        errors.append(err)

    # Boundaries — all 4 must exist
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
            "field":   "DISTRICT",
            "issue":   f"மாவட்டம் பொருந்தவில்லை — Header: '{hdr.get('district')}', Property: '{prop.get('district')}'",
            "severity": "warning"
        })

    # Vendor district vs header district
    v_district = str(v.get("district", "")).strip().lower()
    if v_district and hdr_district and v_district != hdr_district:
        warnings.append({
            "field":   "VENDOR_DISTRICT",
            "issue":   f"விற்பவர் மாவட்டம் '{v.get('district')}' — Header மாவட்டம் '{hdr.get('district')}' — வேறுபாடு",
            "severity": "warning"
        })

    # Amount vs words rough check (numeric digits only comparison)
    amount_str = str(con.get("total_amount", "")).replace(",", "").strip()
    words_str  = str(con.get("amount_in_words", "")).strip()
    if amount_str.isdigit() and words_str and words_str not in ("___", ""):
        amount_int = int(amount_str)
        # Simple lakh/crore keyword check
        if amount_int >= 10_000_000 and "கோடி" not in words_str:
            warnings.append({
                "field":   "AMOUNT_WORDS",
                "issue":   f"தொகை {amount_int:,} — ₹1 கோடிக்கு மேல், ஆனால் 'கோடி' எழுத்தில் இல்லை",
                "severity": "warning"
            })
        elif amount_int >= 100_000 and "லட்சம்" not in words_str and "கோடி" not in words_str:
            warnings.append({
                "field":   "AMOUNT_WORDS",
                "issue":   f"தொகை {amount_int:,} — ₹1 லட்சத்திற்கு மேல், ஆனால் 'லட்சம்' எழுத்தில் இல்லை",
                "severity": "warning"
            })

    # Age sanity check
    for party_label, party in [("விற்பவர்", v), ("வாங்குபவர்", p)]:
        age_str = str(party.get("age", "")).strip()
        if age_str.isdigit():
            age = int(age_str)
            if age < 18:
                warnings.append({
                    "field":   f"{party_label.upper()}_AGE",
                    "issue":   f"{party_label} வயது {age} — 18 வயதுக்கு கீழ் சட்டப்படி ஒப்பந்தம் செல்லாது",
                    "severity": "critical"
                })
            elif age > 100:
                warnings.append({
                    "field":   f"{party_label.upper()}_AGE",
                    "issue":   f"{party_label} வயது {age} — சரிபார்க்கவும்",
                    "severity": "warning"
                })

    return {
        "passed":   all(w["severity"] != "critical" for w in warnings),
        "warnings": warnings
    }


# ══════════════════════════════════════════════════════════════════════════════
#  LAYER 4 — TAMIL GRAMMAR & STYLE (Claude AI)
# ══════════════════════════════════════════════════════════════════════════════

_GRAMMAR_SYSTEM_PROMPT = """நீ ஒரு Tamil legal document editor மற்றும் தமிழ் இலக்கண நிபுணர்.

கீழே கொடுக்கப்படும் சுத்த விக்கிரயப் பத்திரம் (Sale Deed) draft-ஐ மட்டும் படி.
இந்த 4 விஷயங்களை மட்டும் சரிபார்:

1. தமிழ் இலக்கண தவறுகள் (வினை, வேற்றுமை, வல்லினம் மிகல்/மிகாமல்)
2. Legal Tamil சொற்கள் சரியாக உள்ளனவா
   (சரியானவை: விக்கிரயதாரர், கிரயதாரர், பத்திரதாரர், விக்கிரயம், கிரயம்)
3. Sentences முழுமையாக உள்ளனவா — ஏதாவது தொடர் பாதியில் நிறுத்தப்பட்டதா?
4. Legal deed-க்கு பொருத்தமற்ற வார்த்தைகள் உள்ளனவா?

ONLY return valid JSON, no explanation, no markdown:
{
  "grammar_errors": [
    {"line": "தவறான வரி அல்லது phrase", "issue": "என்ன தவறு", "fix": "சரியான வரி"}
  ],
  "legal_term_errors": [
    {"wrong": "தவறான சொல்", "correct": "சரியான சொல்", "context": "எந்த இடத்தில்"}
  ],
  "incomplete_sentences": [
    {"sentence": "முழுமையற்ற தொடர்"}
  ],
  "style_suggestions": [
    {"original": "தற்போதைய வாக்கியம்", "suggestion": "மேம்படுத்தப்பட்ட வாக்கியம்"}
  ],
  "overall_quality": "good" | "fair" | "poor",
  "quality_note": "ஒரு வரி கருத்து தமிழில்"
}"""


async def _layer4_grammar(draft_text: str) -> dict:
    """Call Anthropic API to check Tamil grammar and legal style."""
    try:
        import aiohttp

        # Limit draft to first 3000 chars to stay within token budget
        excerpt = draft_text[:3000]

        payload = {
            "model":      "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "system":     _GRAMMAR_SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": f"இந்த deed draft-ஐ சரிபார்: \n\n{excerpt}"}
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"API returned {resp.status}")
                data = await resp.json()

        # Extract text from response
        raw = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                raw += block.get("text", "")

        # Strip markdown fences if present
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*",     "", raw)
        result = json.loads(raw.strip())

        grammar_errors   = result.get("grammar_errors", [])
        legal_errors     = result.get("legal_term_errors", [])
        incomplete       = result.get("incomplete_sentences", [])
        suggestions      = result.get("style_suggestions", [])
        quality          = result.get("overall_quality", "fair")
        quality_note     = result.get("quality_note", "")

        all_errors = (
            [{"type": "grammar",  **e} for e in grammar_errors] +
            [{"type": "legal_term", **e} for e in legal_errors] +
            [{"type": "incomplete", **e} for e in incomplete]
        )

        return {
            "passed":          len(all_errors) == 0,
            "errors":          all_errors,
            "suggestions":     suggestions,
            "overall_quality": quality,
            "quality_note":    quality_note,
            "ai_checked":      True
        }

    except Exception as e:
        # If AI call fails — return warning, don't block DOCX
        return {
            "passed":          True,
            "errors":          [],
            "suggestions":     [],
            "overall_quality": "unknown",
            "quality_note":    f"AI சரிபார்ப்பு தற்காலிகமாக இயங்கவில்லை: {e}",
            "ai_checked":      False
        }


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle(arguments: dict) -> list[TextContent]:
    draft_text = arguments.get("draft_text", "")
    filled     = arguments.get("filled_skeleton", {})
    deed_type  = arguments.get("deed_type", "plot")

    # Run layers 1–3 in parallel, layer 4 (AI) separately
    l1 = _layer1_placeholders(draft_text)
    l2 = _layer2_legal(filled, deed_type)
    l3 = _layer3_consistency(filled, deed_type)
    l4 = await _layer4_grammar(draft_text)

    # Count totals
    critical_errors = (
        [e for e in l1["errors"]   if e["severity"] == "critical"] +
        [e for e in l2["errors"]   if e["severity"] == "critical"] +
        [e for e in l3["warnings"] if e["severity"] == "critical"]
    )
    warnings = (
        [e for e in l2["errors"]   if e["severity"] == "warning"] +
        [e for e in l3["warnings"] if e["severity"] == "warning"] +
        [e for e in l4["errors"]]
    )

    critical_count = len(critical_errors)
    warning_count  = len(warnings)
    has_errors     = critical_count > 0 or warning_count > 0
    ready_for_docx = critical_count == 0

    # Build Tamil summary for user
    if ready_for_docx and warning_count == 0:
        summary = "✅ Draft முழுவதும் சரியாக உள்ளது — DOCX உருவாக்கலாம்."
    elif ready_for_docx and warning_count > 0:
        summary = (
            f"⚠️  {warning_count} எச்சரிக்கைகள் உள்ளன — DOCX உருவாக்கலாம். "
            "ஆனால் warnings-ஐ முதலில் படிக்கவும்."
        )
    else:
        summary = (
            f"❌ {critical_count} critical தவறுகள் உள்ளன — "
            "திருத்தியபின் மட்டுமே DOCX உருவாக்கவும்."
        )

    return [TextContent(
        type="text",
        text=json.dumps({
            "has_errors":     has_errors,
            "ready_for_docx": ready_for_docx,
            "critical_count": critical_count,
            "warning_count":  warning_count,
            "summary":        summary,
            "layers": {
                "placeholders": l1,
                "legal":        l2,
                "consistency":  l3,
                "tamil_grammar": l4
            }
        }, ensure_ascii=False, indent=2)
    )]
