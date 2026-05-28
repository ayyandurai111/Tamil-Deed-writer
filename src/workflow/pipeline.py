"""
workflow/pipeline.py
====================
Complete server-side deed generation pipeline.

No LLM API calls. No AI reasoning. Pure Python.
Every step that was previously an MCP tool call is now a private function here.
The AI calls ONE tool (run_deed_workflow) and reads ONE field (next_action).

Pipeline steps (internal, invisible to AI):
  detect   → detect_deed_type + load_skeleton
  collect  → extract_fields + resolve_date + validate_fields
             loops until all fields present + PAN rule satisfied
  review   → fill_skeleton + L1+L2+L3+L4 checks
  confirm  → user acknowledged warnings → generate_docx
  done     → list_output_files → return download_url
"""

from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from constants import (
    CRITICAL_FIELDS, OPTIONAL_FIELDS, TAMIL_MONTHS,
    PAN_THRESHOLD, TDS_THRESHOLD, OUTPUT_DIR, BASE_URL,
)
import file_store


# ══════════════════════════════════════════════════════════════════════════════
#  RESPONSE BUILDER — only three shapes ever returned to the AI
# ══════════════════════════════════════════════════════════════════════════════

def _ask(message: str, debug_step: str = "") -> dict:
    """AI must show message to user and call tool again."""
    return {
        "next_action":   "ask_user",
        "ask_message":   message,
        "download_url":  None,
        "debug_step":    debug_step,
    }


def _complete(message: str, download_url: str) -> dict:
    """Workflow finished. AI shows message + download_url. Must NOT call tool again."""
    return {
        "next_action":   "complete",
        "ask_message":   message,
        "download_url":  download_url,
        "debug_step":    "done",
    }


def _error(message: str, debug_step: str = "") -> dict:
    """Recoverable error. AI shows message and calls tool again with step=reply."""
    return {
        "next_action":   "error",
        "ask_message":   message,
        "download_url":  None,
        "debug_step":    debug_step,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — DETECT DEED TYPE  (pure keyword rules, no LLM)
# ══════════════════════════════════════════════════════════════════════════════

_AGRI_KEYWORDS = {
    # Tamil
    "விவசாய", "நஞ்சை", "புஞ்சை", "ஏக்கர்", "சென்ட்", "பட்டா", "புல எண்",
    "சர்வே", "கால்வாய்", "நீர்ப்பாசன", "வயல்", "தோட்டம்", "FMB", "அடங்கல்",
    # English
    "agriculture", "agricultural", "farm", "acre", "cent", "paddy",
    "crop", "irrigation", "survey", "patta", "nanjai", "punjai",
}

_PLOT_KEYWORDS = {
    # Tamil
    "மனை", "வீட்டுமனை", "site", "கதவு எண்", "வார்டு", "தெரு",
    "layout", "வீடு",
    # English
    "plot", "sqft", "sq ft", "square feet", "door no", "ward",
    "residential", "urban", "house site",
}


def _detect_deed_type(text: str) -> str:
    lower = text.lower()
    agri_score = sum(1 for kw in _AGRI_KEYWORDS if kw.lower() in lower)
    plot_score = sum(1 for kw in _PLOT_KEYWORDS if kw.lower() in lower)
    return "agriculture" if agri_score >= plot_score and agri_score > 0 else "plot"


def _load_skeleton(deed_type: str) -> dict:
    from tools.load_skeleton import _load_skeleton_json  # type: ignore
    return _load_skeleton_json(deed_type)


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 2 — FIELD EXTRACTION  (regex + heuristics, no LLM)
# ══════════════════════════════════════════════════════════════════════════════

def _normalize_fields(fields: dict) -> dict:
    out = {}
    for k, v in fields.items():
        key = str(k).strip().upper()
        if v in (None, "null", "None", "undefined", ""):
            out[key] = None
        else:
            out[key] = str(v).strip() if not isinstance(v, (dict, list)) else v
    return out


def _fixup_fields(fields: dict) -> dict:
    """Post-normalize corrections: month names, amount_words trailing suffix."""
    _EN_TO_NUM = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7,
        "jul": 7, "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
    }
    mv = str(fields.get("DATE_MONTH") or "").strip()
    if mv:
        if mv.isdigit():
            fields["DATE_MONTH"] = TAMIL_MONTHS.get(int(mv), mv)
        elif mv.lower() in _EN_TO_NUM:
            fields["DATE_MONTH"] = TAMIL_MONTHS.get(_EN_TO_NUM[mv.lower()], mv)

    for key in ("AMOUNT_WORDS", "RECEIVED_WORDS", "ADVANCE_WORDS", "BALANCE_WORDS"):
        val = fields.get(key)
        if val and str(val).strip().endswith("மட்டும்"):
            fields[key] = str(val).strip()[: -len("மட்டும்")].strip()
    return fields


def _extract_fields_from_text(text: str, existing: dict, deed_type: str) -> dict:
    """
    Rule-based field extraction from raw user text.
    Updates only null slots in existing dict.
    Covers common patterns — AI-provided structured dict is preferred when available.
    """
    merged = dict(existing)

    # Ensure all critical keys exist
    for key in CRITICAL_FIELDS.get(deed_type, {}):
        merged.setdefault(key, None)

    t = text.strip()

    # Aadhaar — 12 consecutive digits (possibly space-separated in groups)
    aadhaars = re.findall(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", t)
    clean_aadhaars = [re.sub(r"[\s-]", "", a) for a in aadhaars if len(re.sub(r"[\s-]", "", a)) == 12]
    if len(clean_aadhaars) >= 1 and not merged.get("VENDOR_AADHAAR"):
        merged["VENDOR_AADHAAR"] = clean_aadhaars[0]
    if len(clean_aadhaars) >= 2 and not merged.get("PURCHASER_AADHAAR"):
        merged["PURCHASER_AADHAAR"] = clean_aadhaars[1]

    # PAN — ABCDE1234F pattern
    pans = re.findall(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", t.upper())
    if len(pans) >= 1 and not merged.get("VENDOR_PAN"):
        merged["VENDOR_PAN"] = pans[0]
    if len(pans) >= 2 and not merged.get("PURCHASER_PAN"):
        merged["PURCHASER_PAN"] = pans[1]

    # Phone — 10 digit mobile numbers
    phones = re.findall(r"\b[6-9]\d{9}\b", t)
    if len(phones) >= 1 and not merged.get("VENDOR_PHONE"):
        merged["VENDOR_PHONE"] = phones[0]
    if len(phones) >= 2 and not merged.get("PURCHASER_PHONE"):
        merged["PURCHASER_PHONE"] = phones[1]

    # Amount — digits with optional commas/lakhs notation
    amounts = re.findall(r"₹\s*([\d,]+)|Rs\.?\s*([\d,]+)|([\d,]{5,})\s*(?:rupees?|ரூபாய்|/-)", t, re.I)
    flat = ["".join(g).replace(",", "") for g in amounts if any(g)]
    if flat and not merged.get("TOTAL_AMOUNT"):
        merged["TOTAL_AMOUNT"] = flat[0]

    # Survey number
    sv = re.search(r"(?:survey\s*no\.?|புல\s*எண்\.?|சர்வே)\s*:?\s*([\d/A-Za-z]+)", t, re.I)
    if sv and not merged.get("SURVEY_NO"):
        merged["SURVEY_NO"] = sv.group(1).strip()

    # Patta
    pt = re.search(r"(?:patta\s*no\.?|பட்டா)\s*:?\s*([\d/]+)", t, re.I)
    if pt and not merged.get("PATTA_NO"):
        merged["PATTA_NO"] = pt.group(1).strip()

    # Extent acre/cent
    acre = re.search(r"([\d.]+)\s*(?:acres?|ஏக்கர்)", t, re.I)
    if acre and not merged.get("EXTENT_ACRE"):
        merged["EXTENT_ACRE"] = acre.group(1)
    cent = re.search(r"([\d.]+)\s*(?:cents?|சென்ட்)", t, re.I)
    if cent and not merged.get("EXTENT_CENT"):
        merged["EXTENT_CENT"] = cent.group(1)

    # Sqft for plot
    sqft = re.search(r"([\d.]+)\s*(?:sq\.?\s*ft|sqft|square\s*feet|சதுர\s*அடி)", t, re.I)
    if sqft and not merged.get("SQFT"):
        merged["SQFT"] = sqft.group(1)

    merged = _fixup_fields(merged)
    return merged


def _merge_structured_fields(provided: dict, existing: dict, deed_type: str) -> dict:
    """
    When the user (or a wrapper) sends a structured fields dict alongside
    user_message, merge it — do not overwrite already-filled slots.
    """
    merged = dict(existing)
    for k, v in _normalize_fields(provided).items():
        if v is not None and (k not in merged or merged[k] is None):
            merged[k] = v
    for key in CRITICAL_FIELDS.get(deed_type, {}):
        merged.setdefault(key, None)
    return _fixup_fields(merged)


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — DATE RESOLUTION
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_date(text: str) -> dict:
    """Parse date from raw text. Falls back to today."""
    from tools.resolve_date import parse_date  # type: ignore
    return parse_date(text)


def _apply_date(fields: dict, date_result: dict) -> dict:
    for k in ("DATE_DAY", "DATE_MONTH", "DATE_YEAR", "DATE_FULL", "DATE_MONTH_TAMIL"):
        if k in date_result:
            fields.setdefault(k, None)
            if not fields[k]:
                fields[k] = date_result[k]
    return fields


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 4 — FIELD VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def _validate_fields(fields: dict, deed_type: str) -> dict:
    """
    Returns:
      can_generate : bool
      pan_block    : bool   — amount > 10L but PAN missing
      tds_required : bool   — amount > 50L (advisory)
      missing      : dict   — {field_key: tamil_label}
      pan_tds_note : str
    """
    critical = CRITICAL_FIELDS.get(deed_type, {})
    missing = {k: v for k, v in critical.items() if not fields.get(k)}

    # PAN rule: amount > 10L → PAN mandatory
    amt_str = str(fields.get("TOTAL_AMOUNT") or "").replace(",", "").strip()
    amount = int(amt_str) if amt_str.isdigit() else 0

    pan_block = False
    tds_required = False
    pan_tds_note = ""

    if amount >= PAN_THRESHOLD:
        has_vpan = bool(fields.get("VENDOR_PAN"))
        has_ppan = bool(fields.get("PURCHASER_PAN"))
        if not (has_vpan and has_ppan):
            pan_block = True
            missing["VENDOR_PAN"]    = "விற்பவர் PAN எண் (Rule 114B)"
            missing["PURCHASER_PAN"] = "வாங்குபவர் PAN எண் (Rule 114B)"

    if amount >= TDS_THRESHOLD:
        tds_required = True
        pan_tds_note = (
            f"TDS Advisory: Sale amount Rs.{amount:,} exceeds Rs.50 lakh. "
            "Purchaser must deduct 1% TDS (Sec 194-IA) and file Form 26QB before registration."
        )

    can_generate = not missing and not pan_block

    return {
        "can_generate": can_generate,
        "pan_block":    pan_block,
        "tds_required": tds_required,
        "missing":      missing,
        "pan_tds_note": pan_tds_note,
    }


def _format_missing(missing: dict) -> str:
    lines = "\n".join(f"  - {v}" for v in list(missing.values())[:10])
    return f"The following details are needed to generate the deed:\n{lines}\n\nPlease provide them."


def _format_pan_ask(tds_required: bool) -> str:
    msg = (
        "The sale amount exceeds Rs.10 lakh. PAN is mandatory (Income Tax Rule 114B).\n"
        "Please provide:\n"
        "  - Vendor PAN number\n"
        "  - Purchaser PAN number"
    )
    if tds_required:
        msg += (
            "\n\nNote: Amount also exceeds Rs.50 lakh. Purchaser must deduct 1% TDS "
            "(Sec 194-IA) and file Form 26QB before registration."
        )
    return msg


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 5 — FILL SKELETON + REVIEW (L1-L4)
# ══════════════════════════════════════════════════════════════════════════════

def _fill_skeleton(skeleton: dict, fields: dict, deed_type: str) -> dict:
    from tools.fill_skeleton import fill_and_clean  # type: ignore
    return fill_and_clean(skeleton, fields, deed_type)


def _run_review(clean_skeleton: dict, deed_type: str) -> dict:
    """Run L1+L2+L3+L4 checks. Returns the full review result dict."""
    from tools.review_draft import (  # type: ignore
        _layer1_placeholders,
        _layer2_legal,
        _layer3_consistency,
        _layer4_structure,
    )
    l1 = _layer1_placeholders(clean_skeleton)
    l2 = _layer2_legal(clean_skeleton, deed_type)
    l3 = _layer3_consistency(clean_skeleton, deed_type)
    l4 = _layer4_structure(clean_skeleton, deed_type)

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

    return {
        "ready_for_docx":  len(critical_errors) == 0,
        "critical_errors": critical_errors,
        "warnings":        warnings,
        "critical_count":  len(critical_errors),
        "warning_count":   len(warnings),
    }


def _format_errors(errors: list) -> str:
    lines = "\n".join(f"  - {e['issue']}" for e in errors[:8])
    return f"The following issues were found in the deed draft:\n{lines}\n\nPlease provide corrections."


def _format_warnings(warnings: list) -> str:
    lines = "\n".join(f"  - {w['issue']}" for w in warnings[:6])
    return (
        f"The deed draft has minor warnings:\n{lines}\n\n"
        "Do you want to proceed with generation? Reply 'yes' to continue or 'no' to make corrections."
    )


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 6 — GENERATE DOCX
# ══════════════════════════════════════════════════════════════════════════════

def _generate_docx(clean_skeleton: dict, session_id: str) -> str:
    """Generate .docx, store in file_store, return download_url."""
    from tools.generate_docx import _build_agriculture_docx, _build_plot_docx  # type: ignore
    from datetime import datetime

    deed_type = clean_skeleton.get("type", "plot")
    prefix    = session_id[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"deed_{prefix}_{timestamp}.docx"
    output_path = OUTPUT_DIR / filename

    if deed_type == "agriculture":
        _build_agriculture_docx(clean_skeleton, output_path)
    else:
        _build_plot_docx(clean_skeleton, output_path)

    file_store.put(filename, output_path.read_bytes())

    return f"{BASE_URL}/download/{filename}"


def _format_complete(download_url: str, tds_note: str) -> str:
    msg = f"Your Tamil sale deed has been generated successfully.\n\nDownload: {download_url}"
    if tds_note:
        msg += f"\n\nImportant: {tds_note}"
    msg += (
        "\n\nDisclaimer: This document is a draft template only. "
        "Consult a registered lawyer or sub-registrar before registration."
    )
    return msg


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def run(
    session: dict,
    user_message: str,
    step: str,
    fields_update: dict | None = None,
) -> tuple[dict, dict]:
    """
    Execute one pipeline turn.

    Args:
        session       : loaded session dict (mutated in place)
        user_message  : raw user text (passed as-is from AI)
        step          : "start" | "reply"
        fields_update : optional structured field dict from AI/user

    Returns:
        (response_dict, updated_session)
        response_dict always has: next_action, ask_message, download_url, debug_step
    """

    # ── Apply any structured field updates from this turn ────────────────────
    if fields_update:
        session["fields"] = _merge_structured_fields(
            fields_update, session["fields"], session.get("deed_type") or "plot"
        )

    current_step = session.get("step", "detect")

    # ════════════════════════════════════════════════════════════════════════
    # PIPELINE STEP: detect
    # ════════════════════════════════════════════════════════════════════════
    if current_step == "detect" or step == "start":
        deed_type = _detect_deed_type(user_message)
        skeleton  = _load_skeleton(deed_type)

        session["deed_type"] = deed_type
        session["skeleton"]  = skeleton
        session["fields"]    = {}
        session["step"]      = "collect"

        # Extract fields from initial message immediately
        session["fields"] = _extract_fields_from_text(
            user_message, session["fields"], deed_type
        )
        date_result = _resolve_date(user_message)
        session["fields"] = _apply_date(session["fields"], date_result)
        if fields_update:
            session["fields"] = _merge_structured_fields(
                fields_update, session["fields"], deed_type
            )

        # Fall through to collect immediately
        current_step = "collect"

    # ════════════════════════════════════════════════════════════════════════
    # PIPELINE STEP: collect
    # ════════════════════════════════════════════════════════════════════════
    if current_step == "collect":
        deed_type = session["deed_type"]

        # Extract from this turn's message
        session["fields"] = _extract_fields_from_text(
            user_message, session["fields"], deed_type
        )
        date_result = _resolve_date(user_message)
        session["fields"] = _apply_date(session["fields"], date_result)

        val = _validate_fields(session["fields"], deed_type)

        if val["pan_block"]:
            session["step"] = "collect"
            return _ask(_format_pan_ask(val["tds_required"]), "collect:pan_block"), session

        if not val["can_generate"]:
            session["step"] = "collect"
            return _ask(_format_missing(val["missing"]), "collect:missing"), session

        # All fields OK → run review
        session["step"] = "review"
        current_step    = "review"
        session["_tds_note"] = val["pan_tds_note"]

    # ════════════════════════════════════════════════════════════════════════
    # PIPELINE STEP: review
    # ════════════════════════════════════════════════════════════════════════
    if current_step == "review":
        deed_type = session["deed_type"]
        clean     = _fill_skeleton(session["skeleton"], session["fields"], deed_type)
        review    = _run_review(clean, deed_type)

        session["clean_skeleton"] = clean
        session["review"]         = review

        if review["critical_count"] > 0:
            session["step"] = "collect"
            return _ask(_format_errors(review["critical_errors"]), "review:critical_errors"), session

        if review["warning_count"] > 0:
            session["step"] = "confirm"
            return _ask(_format_warnings(review["warnings"]), "review:warnings"), session

        # No errors, no warnings → generate
        session["step"] = "generate"
        current_step    = "generate"

    # ════════════════════════════════════════════════════════════════════════
    # PIPELINE STEP: confirm  (user replied yes/no to warnings)
    # ════════════════════════════════════════════════════════════════════════
    if current_step == "confirm":
        reply = user_message.strip().lower()
        if any(w in reply for w in ("yes", "ஆம்", "ok", "okay", "proceed", "continue", "ஆமாம்", "சரி")):
            session["step"] = "generate"
            current_step    = "generate"
        else:
            session["step"] = "collect"
            return _ask(
                "Please provide the corrections and send your updated details.",
                "confirm:rejected"
            ), session

    # ════════════════════════════════════════════════════════════════════════
    # PIPELINE STEP: generate
    # ════════════════════════════════════════════════════════════════════════
    if current_step == "generate":
        session_id   = session.get("_session_id", "unknown")
        download_url = _generate_docx(session["clean_skeleton"], session_id)
        tds_note     = session.get("_tds_note", "")

        session["step"] = "done"
        return _complete(_format_complete(download_url, tds_note), download_url), session

    # ════════════════════════════════════════════════════════════════════════
    # PIPELINE STEP: done  (workflow already complete)
    # ════════════════════════════════════════════════════════════════════════
    return _error(
        "This session has already completed. Start a new conversation to generate another deed.",
        "done:already_complete"
    ), session
