"""
tools/generate_docx.py
======================
Tool 6 — generate_docx

Builds the final Tamil Sale Deed .docx from a filled skeleton dict.
Uses python-docx with Latha font for Tamil rendering.

Annotation:
  readOnlyHint    = False   (writes a .docx file to disk)
  destructiveHint = False   (creates new file; never overwrites existing data)
  idempotentHint  = False   (each call produces a timestamped new file)
"""

import json
from datetime import datetime
from pathlib import Path
from mcp.types import Tool, TextContent

# python-docx imports
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from constants import OUTPUT_DIR

# ── Tool definition ────────────────────────────────────────────────────────────
TOOL_DEFINITION = Tool(
    name="generate_docx",
    description=(
        "[STEP 8 of 9] PRECONDITION: review_draft ready_for_docx=True கட்டாயம். "
        "False-ஆக இருந்தால் இந்த tool-ஐ call செய்யாதே — hard rule. "
        "filled_skeleton = Step 5 result (review pass ஆனது). "
        "filename_prefix = 'vendor_purchaser' format உதாரணம்: 'ramasamy_murugan'. "
        "success=True: பயனருக்கு சொல்: ✅ பத்திரம் தயாரானது! 📄 [filename] 📁 output/. "
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
        "title":          "DOCX Generator",
        "readOnlyHint":   False,   # writes a file
        "destructiveHint": False,  # does not overwrite or delete anything
        "idempotentHint": False,   # each call makes a new timestamped file
    }
)


# ══════════════════════════════════════════════════════════════════════════════
#  DOCX FORMATTING HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _set_tamil_font(run, size_pt: int = 12, bold: bool = False):
    run.font.name = "Latha"
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    r    = run._r
    rPr  = r.get_or_add_rPr()
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"),    "Latha")
    rFonts.set(qn("w:hAnsi"),   "Latha")
    rFonts.set(qn("w:cs"),      "Latha")
    rFonts.set(qn("w:eastAsia"),"Latha")
    rPr.insert(0, rFonts)


def _heading_para(doc, text: str, level: int = 1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after  = Pt(4)
    run = p.add_run(text)
    _set_tamil_font(run, size_pt=13 if level == 1 else 12, bold=True)
    return p


def _body_para(doc, text: str, indent: bool = False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(4)
    if indent:
        p.paragraph_format.left_indent = Cm(1)
    run = p.add_run(text)
    _set_tamil_font(run, size_pt=12)
    return p


def _field_row(doc, label: str, value: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Cm(1)
    lbl = p.add_run(f"{label} : ")
    _set_tamil_font(lbl, size_pt=12, bold=True)
    val = p.add_run(value if value and not value.startswith("{{") else "_______________")
    _set_tamil_font(val, size_pt=12)
    return p


def _blank(val, fallback: str = "_______________") -> str:
    if not val or str(val).startswith("{{"):
        return fallback
    return str(val)


# ══════════════════════════════════════════════════════════════════════════════
#  AGRICULTURE DOCX BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def _build_agriculture_docx(data: dict, output_path: Path):
    doc = Document()
    for section in doc.sections:
        section.top_margin    = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin   = Cm(3)
        section.right_margin  = Cm(2)

    hdr  = data.get("header", {})
    v    = data.get("vendor", {})
    p    = data.get("purchaser", {})
    prop = data.get("property", {})
    con  = data.get("consideration", {})
    wit  = data.get("witnesses", [{}, {}])

    # Title
    t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_tamil_font(t.add_run(data.get("title", "சுத்த விக்கிரயப் பத்திரம்")), 16, bold=True)
    s = doc.add_paragraph(); s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_tamil_font(s.add_run(data.get("subtitle", "ABSOLUTE SALE DEED — AGRICULTURE LAND")), 13, bold=True)
    a = doc.add_paragraph(); a.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_tamil_font(a.add_run(data.get("act_ref", "")), 11)
    doc.add_paragraph()

    # Header
    _field_row(doc, "ஆவண தேதி",
               f"{_blank(hdr.get('date_day'))}ம் / {_blank(hdr.get('date_month'))} மாதம் / {_blank(hdr.get('date_year'))} ஆம் ஆண்டு")
    _field_row(doc, "பதிவு அலுவலகம்", _blank(hdr.get("registration_office")))
    _field_row(doc, "ஜில்லா",  _blank(hdr.get("district")))
    _field_row(doc, "தாலுக்கா", _blank(hdr.get("taluk")))

    # Section 1 — Parties
    _heading_para(doc, "பகுதி 1 — தரப்பினர் விவரம்")
    _heading_para(doc, "விற்பனையாளர் (VENDOR / SELLER) :", level=2)
    for label, key in [("பெயர்", "name"), ("தந்தை / கணவர் பெயர்", "father_name"),
                        ("வயது", "age"), ("விலாசம்", "address"),
                        ("மாவட்டம்", "district"), ("ஆதார் எண்", "aadhaar"),
                        ("பான் எண்", "pan"), ("கைபேசி", "phone")]:
        _field_row(doc, label, _blank(v.get(key)))

    _heading_para(doc, "கொள்முதலாளர் (PURCHASER / BUYER) :", level=2)
    for label, key in [("பெயர்", "name"), ("தந்தை / கணவர் பெயர்", "father_name"),
                        ("வயது", "age"), ("விலாசம்", "address"),
                        ("மாவட்டம்", "district"), ("ஆதார் எண்", "aadhaar"),
                        ("பான் எண்", "pan"), ("கைபேசி", "phone")]:
        _field_row(doc, label, _blank(p.get(key)))

    # Section 2 — Property
    _heading_para(doc, "பகுதி 2 — சொத்து விவரம்")
    _field_row(doc, "மாவட்டம்",   _blank(prop.get("district")))
    _field_row(doc, "தாலுக்கா",   _blank(prop.get("taluk")))
    _field_row(doc, "கிராமம்",    _blank(prop.get("village")))
    _field_row(doc, "சர்வே எண்",  _blank(prop.get("survey_no")))
    _field_row(doc, "பட்டா எண்",  _blank(prop.get("patta_no")))
    _field_row(doc, "நில வகை",    _blank(prop.get("land_nature")))
    _field_row(doc, "மொத்த பரப்பளவு",
               f"{_blank(prop.get('extent_acre'))} ஏக்கர் {_blank(prop.get('extent_cent', ''))} சென்ட்")

    _heading_para(doc, "நான்கு எல்லைகள் (Four Boundaries)", level=2)
    for direction, key in [("கிழக்கு (East)", "boundary_east"), ("மேற்கு (West)", "boundary_west"),
                            ("வடக்கு (North)", "boundary_north"), ("தெற்கு (South)", "boundary_south")]:
        _field_row(doc, direction, _blank(prop.get(key)))

    # Section 3 — Consideration
    _heading_para(doc, "பகுதி 3 — விற்பனை மொத்த தொகை விவரம்")
    _field_row(doc, "மொத்த விலை",      _blank(con.get("total_amount")))
    _field_row(doc, "தொகை எழுத்தில்",  _blank(con.get("amount_words")))
    _field_row(doc, "செலுத்திய விதம்", _blank(con.get("payment_mode")))

    # Witnesses & Signatures
    doc.add_paragraph()
    _heading_para(doc, "சாட்சிகள் மற்றும் கையொப்பங்கள்")
    w1 = wit[0] if len(wit) > 0 else {}
    w2 = wit[1] if len(wit) > 1 else {}

    for idx, w in enumerate([w1, w2], start=1):
        _heading_para(doc, f"சாட்சி {idx} (Witness {idx})", level=2)
        _field_row(doc, "பெயர்",      _blank(w.get("name")))
        _field_row(doc, "விலாசம்",    _blank(w.get("address")))
        _field_row(doc, "கையொப்பம்",  "")

    doc.add_paragraph()
    _heading_para(doc, "விற்பனையாளர் (VENDOR)", level=2)
    _field_row(doc, "பெயர்",    _blank(v.get("name")))
    _field_row(doc, "கையொப்பம் / கட்டை விரல் ரேகை", "")

    _heading_para(doc, "கொள்முதலாளர் (PURCHASER)", level=2)
    _field_row(doc, "பெயர்",    _blank(p.get("name")))
    _field_row(doc, "கையொப்பம் / கட்டை விரல் ரேகை", "")

    doc.add_paragraph()
    disc = doc.add_paragraph(); disc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_tamil_font(disc.add_run(f"⚠  {data.get('disclaimer', '')}"), 10)

    doc.save(str(output_path))


# ══════════════════════════════════════════════════════════════════════════════
#  PLOT DOCX BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def _build_plot_docx(data: dict, output_path: Path):
    doc = Document()
    for section in doc.sections:
        section.top_margin    = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin   = Cm(3)
        section.right_margin  = Cm(2)

    hdr  = data.get("header", {})
    v    = data.get("vendor", {})
    p    = data.get("purchaser", {})
    con  = data.get("consideration", {})
    prop = data.get("property", {})
    wit  = data.get("witnesses", [{}, {}])

    # Title
    t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_tamil_font(t.add_run(data.get("title", "சுத்த விக்கிரையப் பத்திரம்")), 16, bold=True)
    s = doc.add_paragraph(); s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_tamil_font(s.add_run(data.get("subtitle", "ABSOLUTE SALE DEED — PLOT / VACANT LAND")), 13, bold=True)
    doc.add_paragraph()

    _field_row(doc, "தேதி",
               f"{_blank(hdr.get('date_day'))}ம் {_blank(hdr.get('date_month'))} மாதம் {_blank(hdr.get('date_year'))}ம் தேதி")

    _heading_para(doc, "கொள்முதலாளர் (PURCHASER / BUYER) :")
    for label, key in [("பெயர்", "name"), ("தந்தை பெயர்", "father_name"),
                        ("வயது", "age"), ("விலாசம்", "address"),
                        ("அடையாள அட்டை", "id_card"), ("கைபேசி எண்", "phone")]:
        _field_row(doc, label, _blank(p.get(key)))

    _heading_para(doc, "விற்பனையாளர் (VENDOR / SELLER) :")
    for label, key in [("பெயர்", "name"), ("தந்தை பெயர்", "father_name"),
                        ("வயது", "age"), ("விலாசம்", "address"),
                        ("அடையாள அட்டை", "id_card"), ("கைபேசி எண்", "phone")]:
        _field_row(doc, label, _blank(v.get(key)))

    for clause_key in ["ownership_clause", "sale_clause", "possession_clause",
                        "encumbrance_clause", "tax_clause", "patta_clause",
                        "document_clause", "relinquish_clause", "closing_text"]:
        doc.add_paragraph()
        _body_para(doc, data.get(clause_key, ""))

    # Property schedule
    doc.add_paragraph()
    _heading_para(doc, data.get("property_label", "சொத்து விவரம்"))
    for label, key in [("கதவு எண் (Door No)", "door_no"), ("வார்டு எண் (Ward No)", "ward_no"),
                        ("Plot எண்", "plot_no"), ("தெரு", "street"),
                        ("பகுதி", "area"), ("தாலுக்கா", "taluk"),
                        ("மாவட்டம்", "district"), ("மொத்த பரப்பு (Sq.ft)", "extent_sqft")]:
        _field_row(doc, label, _blank(prop.get(key)))

    _heading_para(doc, "நான்கு எல்லைகள் (Four Boundaries)", level=2)
    for direction, key in [("கிழக்கு (East)", "boundary_east"), ("மேற்கு (West)", "boundary_west"),
                            ("வடக்கு (North)", "boundary_north"), ("தெற்கு (South)", "boundary_south")]:
        _field_row(doc, direction, _blank(prop.get(key)))

    # Witnesses & Signatures
    doc.add_paragraph()
    _heading_para(doc, "சாட்சிகள் மற்றும் கையொப்பங்கள்")
    w1 = wit[0] if len(wit) > 0 else {}
    w2 = wit[1] if len(wit) > 1 else {}

    for idx, w in enumerate([w1, w2], start=1):
        _heading_para(doc, f"சாட்சி {idx} (Witness {idx})", level=2)
        _field_row(doc, "பெயர்",      _blank(w.get("name")))
        _field_row(doc, "விலாசம்",    _blank(w.get("address")))
        _field_row(doc, "கையொப்பம்",  "")

    doc.add_paragraph()
    _heading_para(doc, "விற்பனையாளர் (VENDOR)", level=2)
    _field_row(doc, "பெயர்",    _blank(v.get("name")))
    _field_row(doc, "கையொப்பம் / கட்டை விரல் ரேகை", "")

    _heading_para(doc, "கொள்முதலாளர் (PURCHASER)", level=2)
    _field_row(doc, "பெயர்",    _blank(p.get("name")))
    _field_row(doc, "கையொப்பம் / கட்டை விரல் ரேகை", "")

    doc.save(str(output_path))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle(arguments: dict) -> list[TextContent]:
    filled_skeleton = arguments.get("filled_skeleton", {})
    prefix          = arguments.get("filename_prefix", "deed")
    deed_type       = filled_skeleton.get("type", "plot")

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prefix = "".join(c if c.isalnum() or c == "_" else "_" for c in prefix)
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
                "message":  f"✅ பத்திரம் தயாரிக்கப்பட்டது: {filename}"
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
