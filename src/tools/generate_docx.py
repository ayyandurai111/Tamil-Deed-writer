"""
tools/generate_docx.py
======================
Tool 8 — generate_docx

Professional Tamil Sale Deed layout:
- Single uniform font: Latha 12pt throughout
- Title only: 14pt Bold Center
- "சொத்து விவரம்" label: 12pt Bold
- No section headings, no dividers, no bold sub-headers in body
- Date + Purchaser + Vendor in ONE opening paragraph
- All clauses as justified paragraphs
- Property as one comma-separated paragraph
- Line-by-line only for witnesses and signatures
"""

import json
from datetime import datetime
from pathlib import Path
from mcp.types import Tool, TextContent

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from constants import OUTPUT_DIR

# ── Tool definition ────────────────────────────────────────────────────────────
TOOL_DEFINITION = Tool(
    name="generate_docx",
    description=(
        "[CALL 11 of 12] ONE TASK: இந்த tool call மட்டும். PRECONDITION: CALL 10 final decision ready_for_docx=True கட்டாயம். "
        "False-ஆக இருந்தால் / CALL 7+8+9+10 முடியாமல் call செய்யாதே — hard rule. "
        "filled_skeleton = Step 5 result (review pass ஆனது). "
        "filename_prefix = 'vendor_purchaser' format உதாரணம்: 'ramasamy_murugan'. "
        "tool call முடிந்தவுடன் response முடிந்தது. success=True → NEXT CALL (தனி response): list_output_files (CALL 12). "
        "PAN/TDS notes இருந்தால் காட்டு. disclaimer காட்டு. "
        "success=False: ❌ தோல்வி: [error] மீண்டும் முயற்சிக்கவும்."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "filled_skeleton": {
                "type": "object",
                "description": "The filled skeleton JSON returned by fill_skeleton."
            },
            "filename_prefix": {
                "type": "string",
                "description": "Optional prefix for the output filename (e.g. 'raman_karthik').",
                "default": "deed"
            }
        },
        "required": ["filled_skeleton"]
    },
    annotations={
        "title":           "DOCX Generator",
        "readOnlyHint":    False,
        "destructiveHint": False,
        "idempotentHint":  False,
    }
)


# ══════════════════════════════════════════════════════════════════════════════
#  CORE FONT HELPER — ONE font, ONE size everywhere
# ══════════════════════════════════════════════════════════════════════════════

BODY_FONT  = "Latha"
BODY_SIZE  = 12   # pt — used for ALL text
TITLE_SIZE = 14   # pt — title only


def _apply_font(run, size_pt: int = BODY_SIZE, bold: bool = False):
    """Apply Latha font to a run. Single point of font control."""
    run.font.name = "Latha"
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    rPr = run._r.get_or_add_rPr()
    rFonts = OxmlElement("w:rFonts")
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), BODY_FONT)
    rPr.insert(0, rFonts)


def _blank(val, fallback: str = "___________") -> str:
    """Return value or blank placeholder if missing/unfilled."""
    if not val or str(val).startswith("{{"):
        return fallback
    return str(val)


# ══════════════════════════════════════════════════════════════════════════════
#  PARAGRAPH BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def _title_para(doc, text: str):
    """Document title — 14pt Bold Center."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(6)
    run = p.add_run(text)
    _apply_font(run, size_pt=TITLE_SIZE, bold=True)
    return p


def _body_para(doc, text: str, bold: bool = False,
               align=WD_ALIGN_PARAGRAPH.JUSTIFY,
               space_before: int = 6, space_after: int = 6,
               first_line_indent: bool = True):
    """
    Standard body paragraph — 12pt Latha Justified.
    This is used for ALL prose content.
    """
    if not text or str(text).startswith("{{"):
        return None
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after  = Pt(space_after)
    if first_line_indent:
        p.paragraph_format.first_line_indent = Cm(0.75)
    run = p.add_run(text)
    _apply_font(run, size_pt=BODY_SIZE, bold=bold)
    return p


def _sig_para(doc, text: str):
    """Signature / witness line — 12pt Left, no indent."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run(text)
    _apply_font(run, size_pt=BODY_SIZE, bold=False)
    return p


def _spacer(doc):
    """Empty paragraph for visual spacing."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(0)
    run = p.add_run("")
    _apply_font(run)
    return p


# ══════════════════════════════════════════════════════════════════════════════
#  PARTY TEXT BUILDER
#  Returns a single Tamil prose string — NOT separate lines
# ══════════════════════════════════════════════════════════════════════════════

def _party_text(d: dict, deed_type: str = "plot") -> str:
    """
    Build the full party description as a single flowing text string.
    e.g. "45, அண்ணாநகர் 2வது தெரு, சென்னை 40 விலாசத்தில் வசிக்கும்
          திரு பாலன் அவர்களின் குமார் சுமார் 35 வயதுள்ள
          திரு.சுரேஷ் (அடையாள அட்டை XXXX-XXXX-1234) (கைபேசி எண்.9876543210)"
    """
    name       = _blank(d.get("name"))
    age        = _blank(d.get("age"))
    father     = _blank(d.get("father_name"))
    relation   = _blank(d.get("relation", "மகன்"))
    address    = _blank(d.get("address"))
    village    = _blank(d.get("village", ""), "")
    vattam     = _blank(d.get("vattam", ""), "")
    district   = _blank(d.get("district", ""), "")
    aadhaar    = _blank(d.get("aadhaar", d.get("id_card", "")))
    phone      = _blank(d.get("phone"))
    # BUG 1 FIX: strip trailing dot — Claude may extract "திரு." (with dot),
    # causing "திரு..பெயர்" when we add our own dot below.
    prefix     = _blank(d.get("prefix", "திரு"), "திரு").rstrip(".")

    # Build address part
    # Only append village/vattam/district if NOT already present in address string
    # (prevents duplication like "நிலக்கோட்டை, நிலக்கோட்டை, திண்டுக்கல்")
    addr_parts = [address]
    if village and not village.startswith("_") and village not in address:
        addr_parts.append(village)
    if vattam and not vattam.startswith("_") and vattam not in address:
        addr_parts.append(vattam)
    if district and not district.startswith("_") and district not in address:
        addr_parts.append(district)
    addr_str = ", ".join(addr_parts)

    # Build identity part
    if deed_type == "agriculture":
        occupation = _blank(d.get("occupation", ""), "")
        caste      = _blank(d.get("caste", ""), "")
        # FIX: correct Tamil order — PERSON அவர்களின் தந்தை FATHER
        id_part = f"{prefix}.{name}"
        if father and not father.startswith("_"):
            id_part += f" அவர்களின் தந்தை {father}"
        id_part += f" சுமார் {age} வயதுள்ள"
        if caste and not caste.startswith("_"):
            id_part += f" {caste}"
        if occupation and not occupation.startswith("_"):
            id_part += f" {occupation}"
    else:
        id_part = f"{prefix}.{father} அவர்களின் {relation} சுமார் {age} வயதுள்ள {prefix}.{name}"

    pan = _blank(d.get("pan", ""), "")

    text = f"{addr_str} விலாசத்தில் வசிக்கும் {id_part}"
    text += f" (அடையாள அட்டை {aadhaar})"
    if pan and not pan.startswith("_"):
        text += f" (PAN: {pan})"
    text += f" (கைபேசி எண்.{phone})"
    return text


# ══════════════════════════════════════════════════════════════════════════════
#  AGRICULTURE DEED BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def _build_agriculture_docx(data: dict, output_path: Path):
    doc = Document()

    # Page margins — standard legal
    for sec in doc.sections:
        sec.top_margin    = Cm(2.5)
        sec.bottom_margin = Cm(2.5)
        sec.left_margin   = Cm(3.5)
        sec.right_margin  = Cm(2.5)

    hdr   = data.get("header",        {})
    v     = data.get("vendor",        {})
    pur   = data.get("purchaser",     {})
    prop  = data.get("property",      {})
    con   = data.get("consideration", {})
    wit   = data.get("witnesses",     [{}, {}])

    # ── 1. STAMP NOTE (small, center) ────────────────────────────────────────
    stamp = data.get("stamp_note", "")
    if stamp and not stamp.startswith("{{"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(4)
        run = p.add_run(stamp)
        _apply_font(run, size_pt=BODY_SIZE)

    # ── 2. TITLE ──────────────────────────────────────────────────────────────
    _title_para(doc, data.get("title", "சுத்த விக்கிரயப் பத்திரம்"))
    _title_para(doc, data.get("subtitle", "ABSOLUTE SALE DEED — AGRICULTURE LAND"))

    act_ref = data.get("act_ref", "")
    if act_ref and not act_ref.startswith("{{"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(10)
        run = p.add_run(act_ref)
        _apply_font(run, size_pt=BODY_SIZE)

    # ── 3. OPENING PARAGRAPH — Date + Purchaser + Vendor (ONE paragraph) ─────
    date_day   = _blank(hdr.get("date_day"))
    date_month = _blank(hdr.get("date_month"))
    date_year  = _blank(hdr.get("date_year"))
    reg_office = _blank(hdr.get("registration_office"), "")
    taluk      = _blank(hdr.get("taluk"), "")
    district   = _blank(hdr.get("district"), "")

    date_str = f"{date_day}ம் தேதி {date_month} மாதம் {date_year}ம் ஆண்டு"
    if reg_office and not reg_office.startswith("_"):
        date_str += f", {reg_office} சார்பதிவக அலுவலகம்"
    if taluk and not taluk.startswith("_"):
        date_str += f", {taluk} தாலுக்கா"
    if district and not district.startswith("_"):
        date_str += f", {district} மாவட்டம்"

    # FIX BUG 1: vendor (விற்பவர்) FIRST, purchaser (வாங்குபவர்) SECOND — correct Tamil deed order
    v_text   = _party_text(v,   deed_type="agriculture")
    pur_text = _party_text(pur, deed_type="agriculture")

    opening = (
        f"{date_str},\n\n"
        f"{v_text} ஆகிய நான்,\n\n"
        f"{pur_text} அவர்களுக்கு அடியிற்கண்ட சாட்சிகள் முன்னிலையில் "
        f"மனப்பூர்வமாய் சம்மதித்து எழுதிக் கொடுத்த விவசாய நில "
        f"சுத்த விக்கிரயப் பத்திரம் என்னவென்றால்,"
    )
    _body_para(doc, opening, space_before=8, space_after=6, first_line_indent=False)

    # ── 4. VENDOR DECLARATION (section 4) ────────────────────────────────────
    _body_para(doc, data.get("section_4_text", ""))

    # ── 5. CONSIDERATION paragraph ────────────────────────────────────────────
    total   = _blank(con.get("total_amount"))
    words   = _blank(con.get("amount_in_words"))
    advance = _blank(con.get("advance_amount", ""), "")
    adv_dt  = _blank(con.get("advance_date", ""), "")
    balance = _blank(con.get("balance_amount", ""), "")
    bal_dt  = _blank(con.get("balance_date", ""), "")
    pay_mode= _blank(con.get("payment_mode", ""), "")
    txn_no  = _blank(con.get("transaction_no", ""), "")
    txn_dt  = _blank(con.get("transaction_date", ""), "")
    bank    = _blank(con.get("bank_name", ""), "")

    # Strip trailing "மட்டும்" from words to avoid "மட்டும் மட்டும்" duplication
    words_clean = words.rstrip().removesuffix("மட்டும்").rstrip()
    con_text = (
        f"இந்த விவசாய நிலத்தை விக்கிரயம் செய்வதற்கு நிர்ணயிக்கப்பட்ட "
        f"மொத்த விலை ரூபாய் {total} (எழுத்தால்: {words_clean} மட்டும்)."
    )
    if advance and not advance.startswith("_"):
        con_text += f" இதில் முன்பணமாக ரூபாய் {advance}"
        if adv_dt and not adv_dt.startswith("_"):
            con_text += f" ({adv_dt} தேதி)"
        con_text += " பெறப்பட்டது."
    if balance and not balance.startswith("_"):
        con_text += f" இருப்பு தொகை ரூபாய் {balance}"
        if bal_dt and not bal_dt.startswith("_"):
            con_text += f" ({bal_dt} தேதி)"
        con_text += " பெறப்பட்டது."
    if pay_mode and not pay_mode.startswith("_"):
        con_text += f" செலுத்திய முறை: {pay_mode}."
    if txn_no and not txn_no.startswith("_"):
        con_text += f" Transaction எண். {txn_no}"
        if txn_dt and not txn_dt.startswith("_"):
            con_text += f" தேதி {txn_dt}"
        if bank and not bank.startswith("_"):
            con_text += f", {bank} வங்கி"
        con_text += "."
    _body_para(doc, con_text)

    # ── 6. PROPERTY SCHEDULE ──────────────────────────────────────────────────
    # "சொத்து விவரம்" — Bold label, 12pt
    _body_para(doc, "சொத்து விவரம்", bold=True,
               align=WD_ALIGN_PARAGRAPH.LEFT,
               space_before=8, space_after=2, first_line_indent=False)

    prop_parts = []
    for label, key in [
        ("ஜில்லா",           "district"),
        ("தாலுக்கா",          "taluk"),
        ("கிராமம்",           "village"),
        ("வருவாய் கிராமம்",   "revenue_village"),
        ("வட்டம்",            "vattam"),
        ("சர்வே எண்",         "survey_no"),
        ("உட்பிரிவு",          "subdivision"),
        ("பட்டா எண்",          "patta_no"),
        ("சிட்டா எண்",         "chitta_no"),
        ("A-Register எண்",    "a_register_no"),
        ("நில வகை",           "land_type"),
        ("நஞ்சை/புஞ்சை",      "land_nature"),
        ("நீர் ஆதாரம்",        "water_source"),
    ]:
        val = _blank(prop.get(key, ""), "")
        if val and not val.startswith("_"):
            prop_parts.append(f"{label}: {val}")

    extent_acre = _blank(prop.get("extent_acre", ""), "")
    extent_cent = _blank(prop.get("extent_cent", "0"), "0")
    if extent_acre and not extent_acre.startswith("_"):
        prop_parts.append(f"மொத்த பரப்பளவு: {extent_acre} ஏக்கர் {extent_cent} சென்ட்")

    # boundaries
    for label, key in [
        ("கிழக்கு எல்லை", "boundary_east"),
        ("மேற்கு எல்லை",  "boundary_west"),
        ("வடக்கு எல்லை",  "boundary_north"),
        ("தெற்கு எல்லை",  "boundary_south"),
    ]:
        val = _blank(prop.get(key, ""), "")
        if val and not val.startswith("_"):
            prop_parts.append(f"{label}: {val}")

    for label, key in [
        ("கட்டடங்கள்",        "buildings"),
        ("மரங்கள்",            "trees"),
        ("நீர் கட்டமைப்பு",    "water_structures"),
    ]:
        val = _blank(prop.get(key, ""), "")
        if val and not val.startswith("_"):
            prop_parts.append(f"{label}: {val}")

    if prop_parts:
        _body_para(doc, ", ".join(prop_parts) + ".",
                   space_before=2, space_after=6, first_line_indent=False)

    # ── 7. CHAIN OF TITLE ─────────────────────────────────────────────────────
    chain = data.get("chain_of_title", [])
    if chain and isinstance(chain, list):
        chain_parts = []
        for entry in chain:
            if isinstance(entry, dict):
                label     = entry.get("label", "")
                owner_raw = entry.get("owner", "")
                # BUG 2 FIX: skip blank/empty/unfilled owners.
                # Prevents "3வது உரிமையாளர்: ___________" in output.
                if not owner_raw or str(owner_raw).strip() == "" \
                        or str(owner_raw).startswith("{{"):
                    continue
                owner  = str(owner_raw).strip()
                doc_no = _blank(entry.get("doc_no", ""), "")
                part   = f"{label}: {owner}"
                if doc_no and not doc_no.startswith("_"):
                    part += f" (ஆவண எண்: {doc_no})"
                chain_parts.append(part)
        if chain_parts:
            _body_para(doc, "முந்தைய உரிமைத் தொடர் — " + "; ".join(chain_parts) + ".")

    # ── 8. LEGAL CLAUSES ──────────────────────────────────────────────────────
    legal = data.get("legal_clauses", {})
    if isinstance(legal, dict):
        for clause in legal.values():
            _body_para(doc, clause)
    elif isinstance(legal, list):
        for clause in legal:
            _body_para(doc, str(clause))

    # ── 9. AGRICULTURE SPECIAL ────────────────────────────────────────────────
    agri = data.get("agriculture_special", {})
    prose_keys = ["land_nature_clause", "irrigation_clause", "fmb_clause", "adangal_clause"]
    if isinstance(agri, dict):
        for key in prose_keys:
            _body_para(doc, agri.get(key, ""))
        # standing crops / trees / farm structure — single sentence
        detail_parts = []
        for label, key in [
            ("நிலத்தில் உள்ள பயிர்கள்", "standing_crops"),
            ("மரங்கள் விவரம்",           "trees_detail"),
            ("பண்ணை கட்டமைப்பு",         "farm_structure"),
        ]:
            val = _blank(agri.get(key, ""), "")
            if val and not val.startswith("_"):
                detail_parts.append(f"{label}: {val}")
        if detail_parts:
            _body_para(doc, ", ".join(detail_parts) + ".")
    elif isinstance(agri, list):
        for item in agri:
            _body_para(doc, str(item))

    # ── 10. POSSESSION & TRANSFER ─────────────────────────────────────────────
    _body_para(doc, data.get("section_8_text", ""))

    # ── 11. DOCUMENTS HANDED ──────────────────────────────────────────────────
    docs = data.get("documents_handed", {})
    doc_labels = {
        "mother_deed":    "தாய் பத்திரம்",
        "patta_copy":     "பட்டா நகல்",
        "chitta_adangal": "சிட்டா / அடங்கல்",
        "ec_copy":        "வில்லங்கச் சான்று (EC)",
        "fmb_sketch":     "FMB Sketch",
        "tax_receipts":   "வரி ரசீது",
        "id_copies":      "அடையாள ஆவண நகல்கள்",
        "other_docs":     "இதர ஆவணங்கள்",
    }
    # Auto-derive mother_deed from chain_of_title doc numbers if not supplied
    if isinstance(docs, dict):
        mother = _blank(docs.get("mother_deed", ""), "")
        if not mother or mother.startswith("_"):
            chain_docs = []
            for entry in data.get("chain_of_title", []):
                if isinstance(entry, dict):
                    # Skip the current vendor entry — it's the deed being registered
                    if entry.get("label", "").startswith("தற்போதைய"):
                        continue
                    dn = _blank(entry.get("doc_no", ""), "")
                    if dn and not dn.startswith("_") and "/" in dn:
                        chain_docs.append(dn)
            if chain_docs:
                docs = dict(docs)
                docs["mother_deed"] = " மற்றும் ".join(chain_docs)
        # Default boolean doc fields to "ஆம்" if blank
        for bool_key in ("patta_copy", "chitta_adangal", "ec_copy",
                         "fmb_sketch", "tax_receipts", "id_copies"):
            val = _blank(docs.get(bool_key, ""), "")
            if not val or val.startswith("_"):
                docs = dict(docs)
                docs[bool_key] = "ஆம்"
    handed_parts = []
    if isinstance(docs, dict):
        for key, label in doc_labels.items():
            val = _blank(docs.get(key, ""), "")
            if val and not val.startswith("_"):
                handed_parts.append(f"{label}: {val}")
    if handed_parts:
        _body_para(doc, "ஒப்படைக்கப்பட்ட ஆவணங்கள் — " + ", ".join(handed_parts) + ".")
    else:
        _body_para(doc, "மேற்கண்ட சொத்திற்கான அனைத்து அசல் ஆவணங்களும் "
                        "கொள்முதலாளரிடம் ஒப்படைக்கப்பட்டன.")

    # ── 12. CLOSING TEXT ──────────────────────────────────────────────────────
    _body_para(doc, data.get("closing_text", ""), space_before=8, space_after=8)

    # ── 13. WITNESSES — line by line ──────────────────────────────────────────
    w1 = wit[0] if len(wit) > 0 else {}
    w2 = wit[1] if len(wit) > 1 else {}

    for idx, w in enumerate([w1, w2], start=1):
        label   = w.get("label", f"சாட்சி {idx}")
        name    = _blank(w.get("name"))
        address = _blank(w.get("address"))
        aadhaar = _blank(w.get("aadhaar", ""), "")
        line    = f"{label} : {name}, {address}"
        if aadhaar and not aadhaar.startswith("_"):
            line += f", ஆதார்: {aadhaar}"
        line += ",   கையொப்பம் : _______________"
        _sig_para(doc, line)

    _spacer(doc)

    # ── 14. VENDOR & PURCHASER SIGNATURES — two columns ───────────────────────
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after  = Pt(2)
    p.paragraph_format.first_line_indent = Cm(0)
    v_name   = _blank(v.get("name"))
    pur_name = _blank(pur.get("name"))
    run = p.add_run(f"விற்பனையாளர் : {v_name}")
    _apply_font(run, size_pt=BODY_SIZE)
    tab = p.add_run("\t\t\t\t\t")
    _apply_font(tab, size_pt=BODY_SIZE)
    run2 = p.add_run(f"கொள்முதலாளர் : {pur_name}")
    _apply_font(run2, size_pt=BODY_SIZE)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p2.paragraph_format.space_before = Pt(2)
    p2.paragraph_format.space_after  = Pt(2)
    p2.paragraph_format.first_line_indent = Cm(0)
    s1 = p2.add_run("கையொப்பம் / கட்டை விரல் ரேகை : _______________")
    _apply_font(s1, size_pt=BODY_SIZE)
    tab2 = p2.add_run("\t\t\t")
    _apply_font(tab2, size_pt=BODY_SIZE)
    s2 = p2.add_run("கையொப்பம் / கட்டை விரல் ரேகை : _______________")
    _apply_font(s2, size_pt=BODY_SIZE)

    # ── 15. REGISTRAR NOTE ────────────────────────────────────────────────────
    reg_note = data.get("registrar_note", "")
    if reg_note and not reg_note.startswith("{{"):
        _spacer(doc)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after  = Pt(2)
        p.paragraph_format.first_line_indent = Cm(0)
        run = p.add_run(reg_note)
        _apply_font(run, size_pt=BODY_SIZE)

    # ── 16. DISCLAIMER ────────────────────────────────────────────────────────
    disclaimer = data.get("disclaimer", "")
    if disclaimer and not disclaimer.startswith("{{"):
        _spacer(doc)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after  = Pt(4)
        p.paragraph_format.first_line_indent = Cm(0)
        run = p.add_run(f"⚠  {disclaimer}")
        _apply_font(run, size_pt=BODY_SIZE)

    doc.save(str(output_path))


# ══════════════════════════════════════════════════════════════════════════════
#  PLOT DEED BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def _build_plot_docx(data: dict, output_path: Path):
    doc = Document()

    for sec in doc.sections:
        sec.top_margin    = Cm(2.5)
        sec.bottom_margin = Cm(2.5)
        sec.left_margin   = Cm(3.5)
        sec.right_margin  = Cm(2.5)

    hdr   = data.get("header",        {})
    v     = data.get("vendor",        {})
    pur   = data.get("purchaser",     {})
    con   = data.get("consideration", {})
    prop  = data.get("property",      {})
    wit   = data.get("witnesses",     [{}, {}])

    # ── 1. TITLE ──────────────────────────────────────────────────────────────
    _title_para(doc, data.get("title", "சுத்த விக்கிரையப் பத்திரம்"))
    _title_para(doc, data.get("subtitle", "ABSOLUTE SALE DEED — PLOT / VACANT LAND"))
    _spacer(doc)

    # ── 2. OPENING PARAGRAPH — Date + Purchaser + Vendor (ONE paragraph) ─────
    date_day   = _blank(hdr.get("date_day"))
    date_month = _blank(hdr.get("date_month"))
    date_year  = _blank(hdr.get("date_year"))

    date_str = f"{date_day}ம் {date_month} மாதம் {date_year}ம் தேதி"
    date_str += ","

    pur_text = _party_text(pur, deed_type="plot")
    v_text   = _party_text(v,   deed_type="plot")

    opening = (
        f"{date_str}\n\n"
        f"{pur_text} அவர்களுக்கு,\n\n"
        f"{v_text} ஆகிய நான் அடியிற்கண்ட சாட்சிகள் முன்னிலையில் "
        f"மனப்பூர்வமாய் சம்மதித்து எழுதிக் கொள்ளும் காலிமனை "
        f"சுத்த விக்கிரையப் பத்திரம் என்னவென்றால்,"
    )
    _body_para(doc, opening, space_before=8, space_after=6, first_line_indent=False)

    # ── 3. ALL CLAUSES — each as its own justified paragraph ─────────────────
    for key in [
        "ownership_clause",
        "sale_clause",
        "possession_clause",
        "encumbrance_clause",
        "tax_clause",
        "patta_clause",
        "document_clause",
        "relinquish_clause",
    ]:
        _body_para(doc, data.get(key, ""))

    # ── 4. CLOSING TEXT ───────────────────────────────────────────────────────
    _body_para(doc, data.get("closing_text", ""), space_before=8, space_after=8)

    # ── 5. PROPERTY SCHEDULE ──────────────────────────────────────────────────
    # "சொத்து விவரம்" — Bold label, 12pt
    _body_para(doc, "சொத்து விவரம்", bold=True,
               align=WD_ALIGN_PARAGRAPH.LEFT,
               space_before=6, space_after=2, first_line_indent=False)

    prop_parts = []
    for label, key in [
        ("கதவு எண்", "door_no"),
        ("வார்டு எண்", "ward_no"),
        ("தொகுதி / Plot எண்", "plot_no"),
        ("தெரு", "street"),
        ("பகுதி", "area"),
        ("தாலுக்கா", "taluk"),
        ("மாவட்டம்", "district"),
    ]:
        val = _blank(prop.get(key, ""), "")
        if val and not val.startswith("_"):
            prop_parts.append(f"{label}: {val}")

    extent = _blank(prop.get("extent_sqft", ""), "")
    if extent and not extent.startswith("_"):
        prop_parts.append(f"மொத்த பரப்பு: {extent} Sq.ft")

    # boundaries
    boundary_text = "எல்லைகள்"
    boundary_parts = []
    for label, key in [
        ("கிழக்கு", "boundary_east"),
        ("மேற்கு",  "boundary_west"),
        ("வடக்கு",  "boundary_north"),
        ("தெற்கு",  "boundary_south"),
    ]:
        val = _blank(prop.get(key, ""), "")
        if val and not val.startswith("_"):
            boundary_parts.append(f"{label}: {val}")
    if boundary_parts:
        prop_parts.append(boundary_text + " — " + ", ".join(boundary_parts))

    if prop_parts:
        _body_para(doc, ", ".join(prop_parts) + ".",
                   space_before=2, space_after=6, first_line_indent=False)

    # ── 6. WITNESSES — line by line ───────────────────────────────────────────
    _spacer(doc)
    w1 = wit[0] if len(wit) > 0 else {}
    w2 = wit[1] if len(wit) > 1 else {}

    for idx, w in enumerate([w1, w2], start=1):
        label   = w.get("label", f"சாட்சி {idx}")
        name    = _blank(w.get("name"))
        address = _blank(w.get("address"))
        line    = f"{label} : {name}, {address},   கையொப்பம் : _______________"
        _sig_para(doc, line)

    _spacer(doc)

    # ── 7. VENDOR & PURCHASER SIGNATURES ─────────────────────────────────────
    v_name   = _blank(v.get("name"))
    pur_name = _blank(pur.get("name"))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after  = Pt(2)
    p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run(f"விற்பனையாளர் : {v_name}")
    _apply_font(run, size_pt=BODY_SIZE)
    tab = p.add_run("\t\t\t\t\t")
    _apply_font(tab, size_pt=BODY_SIZE)
    run2 = p.add_run(f"கொள்முதலாளர் : {pur_name}")
    _apply_font(run2, size_pt=BODY_SIZE)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p2.paragraph_format.space_before = Pt(2)
    p2.paragraph_format.space_after  = Pt(2)
    p2.paragraph_format.first_line_indent = Cm(0)
    s1 = p2.add_run("கையொப்பம் / கட்டை விரல் ரேகை : _______________")
    _apply_font(s1, size_pt=BODY_SIZE)
    tab2 = p2.add_run("\t\t\t")
    _apply_font(tab2, size_pt=BODY_SIZE)
    s2 = p2.add_run("கையொப்பம் / கட்டை விரல் ரேகை : _______________")
    _apply_font(s2, size_pt=BODY_SIZE)

    # ── 8. LEGAL NOTES ────────────────────────────────────────────────────────
    # (stored in skeleton under legal_notes if present)
    legal_notes = data.get("legal_notes", "")
    if legal_notes and not str(legal_notes).startswith("{{"):
        _spacer(doc)
        _body_para(doc, f"சட்ட குறிப்புகள் (Legal Notes) : {legal_notes}",
                   space_before=10, space_after=4, first_line_indent=False)

    doc.save(str(output_path))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle(arguments: dict) -> list[TextContent]:
    filled_skeleton = arguments.get("filled_skeleton", {})
    prefix          = arguments.get("filename_prefix", "deed")
    deed_type       = filled_skeleton.get("type", "plot")

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prefix = "".join(c if c.isalnum() and ord(c) < 128 else "_" for c in prefix)
    safe_prefix = safe_prefix.strip("_") or "deed"   # fall back if all chars were non-ASCII
    filename    = f"{safe_prefix}_{deed_type}_{timestamp}.docx"
    output_path = OUTPUT_DIR / filename

    try:
        if deed_type == "agriculture":
            _build_agriculture_docx(filled_skeleton, output_path)
        else:
            _build_plot_docx(filled_skeleton, output_path)

        return [TextContent(
            type="text",
            text=json.dumps({
                "success":  True,
                "file":     str(output_path),
                "filename": filename,
                "message":  f"✅ பத்திரம் தயாரிக்கப்பட்டது: {filename}\nகோப்பை பார்க்க list_output_files tool call செய்."
            }, ensure_ascii=False, indent=2)
        )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error":   str(e),
                "message": f"❌ DOCX generation failed: {e}"
            }, ensure_ascii=False)
        )]
