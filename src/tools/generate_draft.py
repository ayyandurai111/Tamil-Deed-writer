"""
tools/generate_draft.py
=======================
Tool 9 — generate_draft

Converts a filled_skeleton dict into a human-readable Tamil plain-text draft.
This draft is passed to review_draft for AI + rule-based checking before DOCX.

Annotation:
  readOnlyHint   = True   (no file writes — returns text only)
  idempotentHint = True   (same skeleton → same draft)
"""

import json
import re
from datetime import datetime
from mcp.types import Tool, TextContent

# ── Tool definition ────────────────────────────────────────────────────────────
TOOL_DEFINITION = Tool(
    name="generate_draft",
    description=(
        "[STEP 6 of 9] filled_skeleton-ஐ human-readable Tamil plain-text-ஆக மாற்று. "
        "filled_skeleton = Step 5 result. "
        "DOCX இல்லை — plain text மட்டும். review_draft-க்கு இது input. "
        "Return: draft_text, draft_id, sections, unfilled_count. "
        "பயனருக்கு சொல்: Draft தயாரானது ✅ — இப்போது 4 அடுக்கு சரிபார்ப்பு செய்கிறேன்: "
        "1️⃣ Placeholders  2️⃣ Legal  3️⃣ Consistency  4️⃣ Tamil Grammar. "
        "draft_text + filled_skeleton + deed_type → review_draft-க்கு pass செய்."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "filled_skeleton": {
                "type": "object",
                "description": "The filled skeleton JSON returned by fill_skeleton."
            }
        },
        "required": ["filled_skeleton"]
    },
    annotations={
        "title":          "Draft Generator",
        "readOnlyHint":   True,
        "idempotentHint": True,
    }
)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _v(val: str, fallback: str = "___") -> str:
    """Return value or fallback if None / empty / still a placeholder."""
    if not val or re.search(r"\{\{.+?\}\}", str(val)):
        return fallback
    return str(val).strip()


def _section(title: str, lines: list[str]) -> str:
    """Format a named section block."""
    body = "\n".join(f"  {line}" for line in lines if line.strip())
    return f"\n{'─'*55}\n{title}\n{'─'*55}\n{body}\n"


# ── Agriculture draft builder ──────────────────────────────────────────────────
def _build_agriculture(data: dict) -> dict:
    hdr  = data.get("header", {})
    v    = data.get("vendor", {})
    p    = data.get("purchaser", {})
    prop = data.get("property", {})
    con  = data.get("consideration", {})
    wit  = data.get("witnesses", [{}, {}])
    ag   = data.get("agriculture_special", {})
    docs = data.get("documents_handed", {})

    sections = {}

    # ── Title ──────────────────────────────────────────────────────────────────
    sections["title"] = (
        f"{data.get('title', 'சுத்த விக்கிரயப் பத்திரம்')}\n"
        f"{data.get('subtitle', 'ABSOLUTE SALE DEED — AGRICULTURE LAND')}\n"
        f"{data.get('act_ref', '')}"
    )

    # ── Header ─────────────────────────────────────────────────────────────────
    sections["header"] = _section("பத்திர தலைப்பு விவரம்", [
        f"தேதி           : {_v(hdr.get('date_day'))}ம் / {_v(hdr.get('date_month'))} மாதம் / {_v(hdr.get('date_year'))} ஆண்டு",
        f"பதிவு அலுவலகம் : {_v(hdr.get('registration_office'))}",
        f"ஜில்லா         : {_v(hdr.get('district'))}",
        f"தாலுக்கா       : {_v(hdr.get('taluk'))}",
    ])

    # ── Parties ────────────────────────────────────────────────────────────────
    sections["parties"] = _section("பகுதி 1 — தரப்பினர் விவரம்", [
        "[ விற்பனையாளர் — VENDOR ]",
        f"பெயர்          : {_v(v.get('prefix'))} {_v(v.get('name'))}",
        f"தந்தை / கணவர் : {_v(v.get('father_name'))}",
        f"வயது           : {_v(v.get('age'))}",
        f"விலாசம்        : {_v(v.get('address'))}, {_v(v.get('village'))}, {_v(v.get('district'))}",
        f"ஆதார் எண்      : {_v(v.get('aadhaar'))}",
        f"PAN எண்        : {_v(v.get('pan'), 'பொருந்தாது')}",
        "",
        "[ கொள்முதலாளர் — PURCHASER ]",
        f"பெயர்          : {_v(p.get('prefix'))} {_v(p.get('name'))}",
        f"தந்தை / கணவர் : {_v(p.get('father_name'))}",
        f"வயது           : {_v(p.get('age'))}",
        f"விலாசம்        : {_v(p.get('address'))}, {_v(p.get('village'))}, {_v(p.get('district'))}",
        f"ஆதார் எண்      : {_v(p.get('aadhaar'))}",
        f"PAN எண்        : {_v(p.get('pan'), 'பொருந்தாது')}",
    ])

    # ── Property ───────────────────────────────────────────────────────────────
    sections["property"] = _section("பகுதி 2 — சொத்து விவரம்", [
        f"மாவட்டம்      : {_v(prop.get('district'))}",
        f"தாலுக்கா      : {_v(prop.get('taluk'))}",
        f"கிராமம்       : {_v(prop.get('village'))}",
        f"சர்வே எண்     : {_v(prop.get('survey_no'))} / {_v(prop.get('subdivision'))}",
        f"பட்டா எண்     : {_v(prop.get('patta_no'))}",
        f"நில வகை       : {_v(prop.get('land_nature'))} ({_v(prop.get('land_type'))})",
        f"பரப்பளவு      : {_v(prop.get('extent_acre'))} ஏக்கர் {_v(prop.get('extent_cent', '0'))} சென்ட்",
        "",
        "[ நான்கு எல்லைகள் ]",
        f"கிழக்கு (E)   : {_v(prop.get('boundary_east'))}",
        f"மேற்கு  (W)   : {_v(prop.get('boundary_west'))}",
        f"வடக்கு  (N)   : {_v(prop.get('boundary_north'))}",
        f"தெற்கு  (S)   : {_v(prop.get('boundary_south'))}",
    ])

    # ── Consideration ──────────────────────────────────────────────────────────
    sections["consideration"] = _section("பகுதி 3 — விற்பனை தொகை விவரம்", [
        f"மொத்த விலை    : ரூ. {_v(con.get('total_amount'))}",
        f"தொகை எழுத்தில்: {_v(con.get('amount_in_words'))}",
        f"செலுத்தும் விதம்: {_v(con.get('payment_mode'))}",
        f"வங்கி          : {_v(con.get('bank_name', '—'))}",
        f"பரிவர்த்தனை எண்: {_v(con.get('transaction_no', '—'))}",
    ])

    # ── Legal clauses (static text — include as-is from skeleton) ─────────────
    legal = data.get("legal_clauses", {})
    sections["legal"] = _section("பகுதி 6 — சட்டரீதியான அறிவிப்புகள்", [
        legal.get("land_reforms", ""),
        "",
        legal.get("encumbrance", ""),
        "",
        legal.get("tax", ""),
    ])

    # ── Agriculture special ────────────────────────────────────────────────────
    sections["agriculture_special"] = _section("பகுதி 7 — விவசாய நிலம் சிறப்புச் சரத்துகள்", [
        ag.get("land_nature_clause", ""),
        "",
        ag.get("irrigation_clause", ""),
        "",
        ag.get("fmb_clause", ""),
        "",
        ag.get("adangal_clause", ""),
    ])

    # ── Witnesses ──────────────────────────────────────────────────────────────
    w1 = wit[0] if len(wit) > 0 else {}
    w2 = wit[1] if len(wit) > 1 else {}
    sections["witnesses"] = _section("பகுதி 10 — சாட்சிகள்", [
        f"சாட்சி 1      : {_v(w1.get('name'))} — {_v(w1.get('address'))}",
        f"சாட்சி 2      : {_v(w2.get('name'))} — {_v(w2.get('address'))}",
        "",
        "விற்பனையாளர் கையொப்பம்  : _______________________",
        "கொள்முதலாளர் கையொப்பம் : _______________________",
    ])

    # ── Assemble full draft ────────────────────────────────────────────────────
    full_draft = (
        sections["title"] + "\n" +
        sections["header"] +
        sections["parties"] +
        sections["property"] +
        sections["consideration"] +
        sections["legal"] +
        sections["agriculture_special"] +
        sections["witnesses"] +
        f"\n⚠  {data.get('disclaimer', '')}\n"
    )

    return full_draft, sections


# ── Plot draft builder ─────────────────────────────────────────────────────────
def _build_plot(data: dict) -> dict:
    hdr  = data.get("header", {})
    v    = data.get("vendor", {})
    p    = data.get("purchaser", {})
    prop = data.get("property", {})
    con  = data.get("consideration", {})
    wit  = data.get("witnesses", [{}, {}])

    sections = {}

    sections["title"] = (
        f"{data.get('title', 'சுத்த விக்கிரையப் பத்திரம்')}\n"
        f"{data.get('subtitle', 'ABSOLUTE SALE DEED — PLOT / VACANT LAND')}"
    )

    sections["header"] = _section("பத்திர தலைப்பு விவரம்", [
        f"தேதி           : {_v(hdr.get('date_day'))}ம் / {_v(hdr.get('date_month'))} மாதம் / {_v(hdr.get('date_year'))} ஆண்டு",
    ])

    sections["parties"] = _section("தரப்பினர் விவரம்", [
        "[ விற்பனையாளர் — VENDOR ]",
        f"பெயர்          : {_v(v.get('name'))}",
        f"தந்தை         : {_v(v.get('father_name'))}",
        f"வயது           : {_v(v.get('age'))}",
        f"விலாசம்        : {_v(v.get('address'))}",
        f"அடையாள அட்டை : {_v(v.get('id_card'))}",
        "",
        "[ கொள்முதலாளர் — PURCHASER ]",
        f"பெயர்          : {_v(p.get('name'))}",
        f"தந்தை         : {_v(p.get('father_name'))}",
        f"வயது           : {_v(p.get('age'))}",
        f"விலாசம்        : {_v(p.get('address'))}",
        f"அடையாள அட்டை : {_v(p.get('id_card'))}",
    ])

    sections["property"] = _section("சொத்து விவரம்", [
        f"கதவு எண்      : {_v(prop.get('door_no'))}",
        f"வார்டு எண்    : {_v(prop.get('ward_no'))}",
        f"Plot எண்      : {_v(prop.get('plot_no'))}",
        f"தெரு          : {_v(prop.get('street'))}",
        f"பகுதி         : {_v(prop.get('area'))}",
        f"தாலுக்கா      : {_v(prop.get('taluk'))}",
        f"மாவட்டம்      : {_v(prop.get('district'))}",
        f"பரப்பளவு      : {_v(prop.get('extent_sqft'))} Sq.ft",
        "",
        "[ நான்கு எல்லைகள் ]",
        f"கிழக்கு (E)   : {_v(prop.get('boundary_east'))}",
        f"மேற்கு  (W)   : {_v(prop.get('boundary_west'))}",
        f"வடக்கு  (N)   : {_v(prop.get('boundary_north'))}",
        f"தெற்கு  (S)   : {_v(prop.get('boundary_south'))}",
    ])

    sections["consideration"] = _section("விற்பனை தொகை விவரம்", [
        f"மொத்த விலை    : ரூ. {_v(con.get('total_amount'))}",
        f"தொகை எழுத்தில்: {_v(con.get('amount_in_words'))}",
        f"செலுத்தும் விதம்: {_v(con.get('payment_mode'))}",
    ])

    w1 = wit[0] if len(wit) > 0 else {}
    w2 = wit[1] if len(wit) > 1 else {}
    sections["witnesses"] = _section("சாட்சிகள்", [
        f"சாட்சி 1      : {_v(w1.get('name'))} — {_v(w1.get('address'))}",
        f"சாட்சி 2      : {_v(w2.get('name'))} — {_v(w2.get('address'))}",
        "",
        "விற்பனையாளர் கையொப்பம்  : _______________________",
        "கொள்முதலாளர் கையொப்பம் : _______________________",
    ])

    full_draft = (
        sections["title"] + "\n" +
        sections["header"] +
        sections["parties"] +
        sections["property"] +
        sections["consideration"] +
        sections["witnesses"]
    )

    return full_draft, sections


# ── Handler ────────────────────────────────────────────────────────────────────
async def handle(arguments: dict) -> list[TextContent]:
    filled = arguments.get("filled_skeleton", {})
    deed_type = filled.get("type", "plot")

    if deed_type == "agriculture":
        full_draft, sections = _build_agriculture(filled)
    else:
        full_draft, sections = _build_plot(filled)

    # Count remaining unfilled placeholders in the draft
    unfilled = re.findall(r"\{\{[A-Z_]+\}\}", full_draft)

    draft_id = f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    return [TextContent(
        type="text",
        text=json.dumps({
            "draft_id":          draft_id,
            "deed_type":         deed_type,
            "draft_text":        full_draft,
            "sections":          sections,
            "unfilled_count":    len(unfilled),
            "unfilled_tags":     list(set(unfilled)),
            "message": (
                f"✅ Draft ready ({draft_id}). "
                f"{len(unfilled)} unfilled placeholders found. "
                "Pass draft_text and filled_skeleton to review_draft next."
            )
        }, ensure_ascii=False, indent=2)
    )]
